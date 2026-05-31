"""Group tiebreakers (Spec §2): overall criteria, then head-to-head."""

from __future__ import annotations

import numpy as np

from wm2026.tournament.loader import SimConfig
from wm2026.tournament.standings import rank_group
from wm2026.tournament.types import STAGE_GROUP, MatchResult


def _m(home: str, away: str, hg: int, ag: int) -> MatchResult:
    return MatchResult(
        stage=STAGE_GROUP,
        home=home,
        away=away,
        home_goals=hg,
        away_goals=ag,
        xg_home=0.0,
        xg_away=0.0,
        neutral=True,
        group="A",
    )


def test_head_to_head_breaks_a_two_way_tie():
    # A: 5 pts. B & C tie on (pts=4, GD=0, GF=2); B beat C 1-0 head-to-head.
    results = [
        _m("A", "B", 1, 1),
        _m("A", "C", 1, 1),
        _m("A", "D", 2, 0),
        _m("B", "C", 1, 0),  # B beats C
        _m("B", "D", 0, 1),  # D beats B
        _m("C", "D", 1, 0),  # C beats D
    ]
    elo = dict.fromkeys("ABCD", 1500.0)
    order = [
        r.code
        for r in rank_group(list("ABCD"), results, np.random.default_rng(0), SimConfig(), elo)
    ]
    assert order == ["A", "B", "C", "D"]


def test_overall_goal_difference_outranks_goals_scored():
    # X and Y both 4 pts; X has GD +3, Y has GD +2 with more goals scored.
    results = [
        _m("X", "Z", 3, 0),  # X: GD +3
        _m("Y", "Z", 4, 2),  # Y: GD +2 but more goals
        _m("X", "Y", 0, 0),  # both draw
    ]
    elo = dict.fromkeys("XYZ", 1500.0)
    order = [
        r.code for r in rank_group(list("XYZ"), results, np.random.default_rng(0), SimConfig(), elo)
    ]
    assert order == ["X", "Y", "Z"]  # GD +3 beats +2 despite Y scoring more
