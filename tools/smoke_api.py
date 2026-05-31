"""In-process smoke test of the FastAPI backend (REST + WebSocket).

Uses Starlette's TestClient so no live server/port is needed.
Run:  uv run python tools/smoke_api.py
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from wm2026.api import app


def main() -> None:
    with TestClient(app) as client:
        teams = client.get("/teams").json()["teams"]
        assert len(teams) == 48, len(teams)
        assert teams[0]["flagUrl"].startswith("https://flagcdn.com/")
        t0 = teams[0]
        print(f"GET /teams       -> {len(teams)} teams, e.g. {t0['name']} ({t0['elo']})")

        groups = client.get("/groups").json()
        assert len(groups["groups"]) == 12
        print(f"GET /groups      -> 12 groups, hosts={groups['hosts']}")

        model = client.get("/model").json()
        print(f"GET /model       -> beta={model['beta']:.3f}, RPS={model['metrics']['rps']}")

        single = client.post("/simulate", json={"mode": "single", "seed": 42}).json()
        assert len(single["koResults"]) == 32
        print(f"POST /simulate   -> champion={single['champion']}, {len(single['koResults'])} KO")

        mc = client.post("/simulate", json={"mode": "montecarlo", "n": 300, "seed": 1}).json()
        top = mc["teams"][0]
        print(f"POST /montecarlo -> {mc['runsDone']} runs, top {top['team']} {top['pTitle']:.3f}")

        # WebSocket single-run stream.
        with client.websocket_connect("/ws/simulate") as ws:
            ws.send_json({"mode": "single", "seed": 7, "speed": 1000})
            kinds: dict[str, int] = {}
            while True:
                ev = ws.receive_json()
                if ev["type"] == "done":
                    break
                kinds[ev["type"]] = kinds.get(ev["type"], 0) + 1
        print(f"WS /ws/simulate   -> streamed events {kinds}")
        assert kinds.get("match_result") == 104
        assert "champion" in kinds

    print("\nAll API smoke checks passed.")


if __name__ == "__main__":
    main()
