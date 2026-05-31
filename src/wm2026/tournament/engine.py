"""Single-tournament simulation + ordered broadcast event stream (Spec §6, §7)."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .loader import SimConfig, Tournament
from .standings import group_fixtures, rank_group, rank_thirds, teams_elo
from .third_place import assign_thirds
from .types import (
    STAGE_FINAL,
    STAGE_GROUP,
    STAGE_R32,
    GroupTable,
    MatchResult,
    ScoreModel,
    Team,
)

# Stages eligible to update a team's "furthest reached" marker.
_REACH_STAGES = {STAGE_R32, "R16", "QF", "SF", STAGE_FINAL}
_REACH_ORDER = {"group": 0, STAGE_R32: 1, "R16": 2, "QF": 3, "SF": 4, STAGE_FINAL: 5, "champion": 6}


@dataclass
class TournamentResult:
    group_tables: dict[str, GroupTable]
    group_rank: dict[str, int]  # team code -> 1..4 within its group
    group_of: dict[str, str]  # team code -> group letter
    qualified_thirds: list[str]  # the 8 best thirds (codes), best-first
    group_results: list[MatchResult]
    ko_results: dict[int, MatchResult]  # match_no -> result
    reached: dict[str, str]  # team code -> furthest stage
    champion: str
    runner_up: str
    third_place: str
    fourth_place: str
    events: list[dict] = field(default_factory=list)

    def qualified(self) -> list[str]:
        """All 32 teams that reached the knockout phase."""
        return [c for c, s in self.reached.items() if _REACH_ORDER[s] >= _REACH_ORDER[STAGE_R32]]


def _resolve_venue(t: Tournament, a: Team, b: Team, stage: str) -> tuple[Team, Team, bool]:
    """Decide (home, away, neutral); a host in-region is treated as home."""
    cfg = t.config
    advantage = cfg.host_group_advantage if stage == STAGE_GROUP else cfg.host_knockout_advantage
    a_adv = a.is_host and advantage
    b_adv = b.is_host and advantage
    if a_adv and not b_adv:
        return a, b, False
    if b_adv and not a_adv:
        return b, a, False
    return a, b, True


def _shootout(
    elo_home: float, elo_away: float, rng: np.random.Generator, cfg: SimConfig
) -> tuple[int, int]:
    """Simulate a penalty shootout, slightly tilted toward the stronger side."""
    tilt = 0.05 * np.tanh((elo_home - elo_away) / cfg.penalty_elo_scale)
    p_home = float(np.clip(cfg.penalty_base_success + tilt, 0.5, 0.95))
    p_away = float(np.clip(cfg.penalty_base_success - tilt, 0.5, 0.95))
    hk = int(np.sum(rng.random(5) < p_home))
    ak = int(np.sum(rng.random(5) < p_away))
    # Sudden death.
    for _ in range(50):
        if hk != ak:
            break
        h = rng.random() < p_home
        a = rng.random() < p_away
        hk += int(h)
        ak += int(a)
    if hk == ak:  # pathological; nudge by the tilt
        if rng.random() < 0.5 + tilt:
            hk += 1
        else:
            ak += 1
    return hk, ak


def _play(
    t: Tournament,
    model: ScoreModel,
    a: Team,
    b: Team,
    stage: str,
    rng: np.random.Generator,
    *,
    group: str | None = None,
    match_no: int | None = None,
) -> MatchResult:
    """Play one match; resolve knockout draws via extra time + penalties."""
    cfg = t.config
    home, away, neutral = _resolve_venue(t, a, b, stage)
    lam, mu = model.rates(home.elo, away.elo, neutral)
    hg, ag = model.sample_score(home.elo, away.elo, rng, neutral, 1.0)

    decided_by, winner, hp, ap = "regulation", None, None, None
    if stage != STAGE_GROUP:
        if hg == ag:
            ehg, eag = model.sample_score(home.elo, away.elo, rng, neutral, cfg.extra_time_fraction)
            hg += ehg
            ag += eag
            if hg == ag:
                decided_by = "penalties"
                hp, ap = _shootout(home.elo, away.elo, rng, cfg)
                winner = home.code if hp > ap else away.code
            else:
                decided_by = "extra_time"
                winner = home.code if hg > ag else away.code
        else:
            winner = home.code if hg > ag else away.code

    return MatchResult(
        stage=stage,
        home=home.code,
        away=away.code,
        home_goals=hg,
        away_goals=ag,
        xg_home=lam,
        xg_away=mu,
        neutral=neutral,
        group=group,
        match_no=match_no,
        decided_by=decided_by,
        winner=winner,
        home_pens=hp,
        away_pens=ap,
    )


def simulate_tournament(
    t: Tournament,
    rng: np.random.Generator,
    *,
    collect_events: bool = False,
) -> TournamentResult:
    """Run one full tournament. With ``collect_events`` build the event stream."""
    model = t.require_model()
    elo = teams_elo(t.teams)
    cfg = t.config
    events: list[dict] = []

    def emit(ev_type: str, **payload) -> None:
        if collect_events:
            events.append({"type": ev_type, **payload})

    # Group stage: matchday by matchday, all groups in parallel.
    group_letters = sorted(t.groups)
    fixtures = {g: group_fixtures(t.groups[g]) for g in group_letters}
    results_by_group: dict[str, list[MatchResult]] = {g: [] for g in group_letters}
    group_results: list[MatchResult] = []

    emit("stage_change", **{"from": None, "to": STAGE_GROUP})
    for matchday in (1, 2, 3):
        emit("matchday", stage=STAGE_GROUP, matchday=matchday)
        for g in group_letters:
            for mday, h, a in fixtures[g]:
                if mday != matchday:
                    continue
                res = _play(t, model, t.teams[h], t.teams[a], STAGE_GROUP, rng, group=g)
                results_by_group[g].append(res)
                group_results.append(res)
                emit("match_result", **res.to_event())
            table = GroupTable(g, rank_group(t.groups[g], results_by_group[g], rng, cfg, elo))
            emit("table_update", **table.to_event())

    tables = {
        g: GroupTable(g, rank_group(t.groups[g], results_by_group[g], rng, cfg, elo))
        for g in group_letters
    }

    group_rank: dict[str, int] = {}
    group_of: dict[str, str] = {}
    for g in group_letters:
        for idx, row in enumerate(tables[g].rows):
            group_rank[row.code] = idx + 1
            group_of[row.code] = g

    # Determine qualifiers.
    third_rows = {tables[g].rows[2].code: tables[g].rows[2] for g in group_letters}
    ranked_thirds = rank_thirds(third_rows, rng, cfg, elo)
    qualified_thirds = ranked_thirds[:8]
    qualifying_groups = {group_of[c] for c in qualified_thirds}
    slot_assignment = assign_thirds(qualifying_groups, t.third_matrix)  # winnerGroup -> thirdGroup
    third_for_slot = {slot: tables[grp].rows[2].code for slot, grp in slot_assignment.items()}

    emit(
        "third_place_ranking",
        ranked=[
            {"team": c, "group": group_of[c], "qualified": c in qualified_thirds}
            for c in ranked_thirds
        ],
    )
    emit("stage_change", **{"from": STAGE_GROUP, "to": STAGE_R32})

    # Resolve R32 fixtures from slots.
    def resolve_slot(desc: dict) -> str:
        if desc["type"] == "groupRank":
            return tables[desc["group"]].rows[desc["rank"] - 1].code
        if desc["type"] == "third":
            return third_for_slot[desc["slot"]]
        raise ValueError(f"Unknown R32 slot descriptor: {desc}")

    reached: dict[str, str] = dict.fromkeys(t.teams, "group")

    def mark(stage: str, *codes: str) -> None:
        if stage not in _REACH_STAGES:
            return
        for c in codes:
            if _REACH_ORDER[stage] > _REACH_ORDER[reached[c]]:
                reached[c] = stage

    ko_results: dict[int, MatchResult] = {}

    def resolve_ref(desc: dict) -> str:
        ref = ko_results[desc["match"]]
        if desc["type"] == "winner":
            return ref.winner  # type: ignore[return-value]
        if desc["type"] == "loser":
            return ref.loser  # type: ignore[return-value]
        raise ValueError(f"Unknown knockout ref: {desc}")

    # A pairing is revealed (teams, no score yet) the moment its seeding is
    # fixed — the whole R32 column when the groups end, each later match as soon
    # as both its feeders are decided. The score then fills in once it's played.
    ko_by_match = {e["match"]: e for e in t.knockout}
    feeds: dict[int, list[int]] = {}
    for e in t.knockout:
        for ref in (e["home"], e["away"]):
            feeds.setdefault(ref["match"], []).append(e["match"])
    seeded: set[int] = set()

    def seed_downstream(played_match: int) -> None:
        for dep in feeds.get(played_match, []):
            entry = ko_by_match[dep]
            if dep in seeded:
                continue
            if entry["home"]["match"] in ko_results and entry["away"]["match"] in ko_results:
                seeded.add(dep)
                emit(
                    "bracket_seed",
                    matchNo=dep,
                    round=entry["round"],
                    home=resolve_ref(entry["home"]),
                    away=resolve_ref(entry["away"]),
                )

    for entry in t.r32:
        emit(
            "bracket_seed",
            matchNo=entry["match"],
            round=STAGE_R32,
            home=resolve_slot(entry["home"]),
            away=resolve_slot(entry["away"]),
        )

    for entry in t.r32:
        home = resolve_slot(entry["home"])
        away = resolve_slot(entry["away"])
        res = _play(t, model, t.teams[home], t.teams[away], STAGE_R32, rng, match_no=entry["match"])
        ko_results[entry["match"]] = res
        mark(STAGE_R32, home, away)
        emit("match_result", **res.to_event())
        emit(
            "bracket_update",
            matchNo=entry["match"],
            round=STAGE_R32,
            home=res.home,
            away=res.away,
            winner=res.winner,
        )
        seed_downstream(entry["match"])

    current_round = STAGE_R32
    for entry in t.knockout:
        rnd = entry["round"]
        if rnd != current_round:
            emit("stage_change", **{"from": current_round, "to": rnd})
            current_round = rnd
        home = resolve_ref(entry["home"])
        away = resolve_ref(entry["away"])
        res = _play(t, model, t.teams[home], t.teams[away], rnd, rng, match_no=entry["match"])
        ko_results[entry["match"]] = res
        mark(rnd, home, away)
        emit("match_result", **res.to_event())
        emit(
            "bracket_update",
            matchNo=entry["match"],
            round=rnd,
            home=res.home,
            away=res.away,
            winner=res.winner,
        )
        seed_downstream(entry["match"])

    final = ko_results[104]
    third_play = ko_results[103]
    champion = final.winner
    assert champion is not None
    reached[champion] = "champion"

    emit("champion", team=champion, runnerUp=final.loser)

    return TournamentResult(
        group_tables=tables,
        group_rank=group_rank,
        group_of=group_of,
        qualified_thirds=qualified_thirds,
        group_results=group_results,
        ko_results=ko_results,
        reached=reached,
        champion=champion,
        runner_up=final.loser,  # type: ignore[arg-type]
        third_place=third_play.winner,  # type: ignore[arg-type]
        fourth_place=third_play.loser,  # type: ignore[arg-type]
        events=events,
    )
