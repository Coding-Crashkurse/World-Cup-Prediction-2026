"""FastAPI backend (Spec §7): REST snapshots + WebSocket "broadcast" events.

The backend only *loads* the trained artifacts; it never trains. The WebSocket
streams the engine's ordered event list (the "Regie-Anweisungen" for the
broadcast UI), pacing single-run events so the front-end can choreograph reveals.
"""

from __future__ import annotations

import asyncio
import json
from contextlib import asynccontextmanager, suppress

import numpy as np
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .tournament import load_tournament, run_montecarlo, simulate_tournament
from .tournament.engine import TournamentResult
from .tournament.loader import SimConfig, Tournament

FLAG_BASE = "https://flagcdn.com"

# Per-event server-side pacing for the single-run "telecast" (seconds at 1x),
# divided by the client's `speed`. Tuned so a viewer can actually follow each
# result; the speed slider compresses it for the impatient.
_PACING = {
    "match_result": 0.95,
    "table_update": 0.25,
    "third_place_ranking": 2.5,
    "stage_change": 1.8,
    "bracket_seed": 0.08,
    "bracket_update": 0.8,
    "matchday": 1.4,
    "champion": 0.0,
}


def _mc_delay(runs_done: int) -> float:
    """Playback delay between Monte-Carlo frames — slow early so the big swings
    are watchable, then quick as the probabilities settle."""
    if runs_done <= 20:
        return 0.5
    if runs_done <= 100:
        return 0.28
    if runs_done <= 1000:
        return 0.13
    return 0.05


class _State:
    tournament: Tournament | None = None
    last_probabilities: dict | None = None


state = _State()


def get_tournament() -> Tournament:
    """Lazily load + cache the tournament; (re)load model from artifacts."""
    if state.tournament is None:
        state.tournament = load_tournament()
    return state.tournament


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Warm the cache if artifacts exist; otherwise endpoints report the error.
    with suppress(Exception):
        get_tournament()
    yield


app = FastAPI(title="Road to the Cup — WM 2026", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _team_payload(t: Tournament, code: str) -> dict:
    team = t.teams[code]
    return {
        "code": team.code,
        "name": team.name,
        "iso2": team.iso2,
        "confederation": team.confederation,
        "isHost": team.is_host,
        "elo": round(team.elo, 1),
        "flagUrl": f"{FLAG_BASE}/{team.iso2}.svg",
    }


def _result_payload(t: Tournament, result: TournamentResult) -> dict:
    return {
        "champion": result.champion,
        "runnerUp": result.runner_up,
        "thirdPlace": result.third_place,
        "fourthPlace": result.fourth_place,
        "qualifiedThirds": result.qualified_thirds,
        "groupTables": {g: tbl.to_event() for g, tbl in result.group_tables.items()},
        "koResults": [
            r.to_event() for r in sorted(result.ko_results.values(), key=lambda r: r.match_no or 0)
        ],
    }


@app.get("/teams")
def get_teams() -> dict:
    t = get_tournament()
    return {"teams": [_team_payload(t, c) for c in t.teams]}


@app.get("/groups")
def get_groups() -> dict:
    t = get_tournament()
    return {
        "groups": t.groups,
        "hosts": t.hosts,
        "bracket": {"r32": t.r32, "knockout": t.knockout},
    }


@app.get("/model")
def get_model_info() -> dict:
    t = get_tournament()
    m = t.require_model()
    return {
        "mu": m.mu,
        "gamma": m.gamma,
        "beta": m.beta,
        "rho": m.rho,
        "trainedThrough": m.trained_through,
        "nTrain": m.n_train,
        "halfLifeYears": m.half_life_years,
        "metrics": m.metrics,
    }


@app.get("/predict")
def predict(home: str, away: str, neutral: bool = True) -> dict:
    """The score-probability grid for one fixture (the maths, made visible)."""
    t = get_tournament()
    m = t.require_model()
    if home not in t.teams or away not in t.teams:
        raise HTTPException(status_code=404, detail="Unknown team code.")
    eh, ea = t.teams[home].elo, t.teams[away].elo
    lam, mu = m.rates(eh, ea, neutral)
    grid = m.score_matrix(lam, mu)  # 11x11 joint P(home=x, away=y)
    p_home, p_draw, p_away = m.outcome_probs(eh, ea, neutral)

    show = 8  # display goals 0..7; the tail beyond is negligible
    top_idx = np.argsort(grid.ravel())[::-1][:5]
    top = []
    for f in top_idx:
        x, y = divmod(int(f), grid.shape[1])
        top.append({"home": x, "away": y, "p": round(float(grid[x, y]), 4)})

    return {
        "home": home,
        "away": away,
        "neutral": neutral,
        "lambdaHome": round(float(lam), 3),
        "lambdaAway": round(float(mu), 3),
        "pHome": round(float(p_home), 4),
        "pDraw": round(float(p_draw), 4),
        "pAway": round(float(p_away), 4),
        "maxGoals": show - 1,
        "grid": [[round(float(grid[x, y]), 5) for y in range(show)] for x in range(show)],
        "top": top,
    }


@app.get("/elo-history")
def get_elo_history() -> dict:
    """Per-team Elo trajectory over time (for the ratings visualization)."""
    from .paths import ELO_HISTORY_FILE

    if not ELO_HISTORY_FILE.exists():
        return {"baseline": 1500.0, "series": {}}
    return json.loads(ELO_HISTORY_FILE.read_text(encoding="utf-8"))


@app.get("/probabilities")
def get_probabilities() -> dict:
    """Last aggregated Monte-Carlo result (cache); empty until one has run."""
    return state.last_probabilities or {"runsDone": 0, "runsTotal": 0, "teams": []}


class SimulateRequest(BaseModel):
    mode: str = "single"  # "single" | "montecarlo"
    n: int = 10000
    seed: int | None = None
    config: dict | None = None


@app.post("/simulate")
async def post_simulate(req: SimulateRequest) -> dict:
    """Run a simulation synchronously (off the event loop) and return a summary."""
    t = get_tournament()
    cfg = SimConfig(**req.config) if req.config else t.config
    t.config = cfg
    if req.mode == "single":
        result = await asyncio.to_thread(
            simulate_tournament, t, np.random.default_rng(req.seed), collect_events=False
        )
        return {"mode": "single", **_result_payload(t, result)}

    agg = await asyncio.to_thread(run_montecarlo, t, req.n, seed=req.seed)
    state.last_probabilities = agg.to_event()
    return {"mode": "montecarlo", **state.last_probabilities}


@app.websocket("/ws/simulate")
async def ws_simulate(websocket: WebSocket) -> None:
    await websocket.accept()
    try:
        params = await websocket.receive_json()
    except WebSocketDisconnect:
        return

    try:
        t = get_tournament()
        t.require_model()
    except Exception as exc:
        await websocket.send_json({"type": "error", "message": str(exc)})
        await websocket.close()
        return

    mode = params.get("mode", "single")
    seed = params.get("seed")
    speed = max(0.1, float(params.get("speed", 1.0)))
    if params.get("config"):
        t.config = SimConfig(**params["config"])

    try:
        if mode == "single":
            await _stream_single(websocket, t, seed, speed)
        else:
            await _stream_montecarlo(
                websocket, t, int(params.get("n", 10000)), seed, int(params.get("step", 25))
            )
    except WebSocketDisconnect:
        return
    finally:
        await _safe_close(websocket)


async def _stream_single(ws: WebSocket, t: Tournament, seed, speed: float) -> None:
    result = await asyncio.to_thread(
        simulate_tournament, t, np.random.default_rng(seed), collect_events=True
    )
    for ev in result.events:
        await ws.send_json(ev)
        delay = _PACING.get(ev["type"], 0.0) / speed
        if delay:
            await asyncio.sleep(delay)
    await ws.send_json({"type": "done", "mode": "single"})


async def _stream_montecarlo(ws: WebSocket, t: Tournament, n: int, seed, step: int = 25) -> None:
    queue: asyncio.Queue = asyncio.Queue()
    loop = asyncio.get_running_loop()

    def callback(agg) -> None:
        loop.call_soon_threadsafe(queue.put_nowait, agg.to_event())

    every = max(1, step)  # the client-chosen staircase step

    def _run():
        return run_montecarlo(t, n, seed=seed, progress_callback=callback, callback_every=every)

    task = loop.run_in_executor(None, _run)
    while not task.done() or not queue.empty():
        try:
            ev = await asyncio.wait_for(queue.get(), timeout=0.1)
        except TimeoutError:
            continue
        state.last_probabilities = ev
        await ws.send_json(ev)
        await asyncio.sleep(_mc_delay(ev.get("runsDone", 0)))
    await task
    await ws.send_json({"type": "done", "mode": "montecarlo"})


async def _safe_close(ws: WebSocket) -> None:
    with suppress(RuntimeError):
        await ws.close()
