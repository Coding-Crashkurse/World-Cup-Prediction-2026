"""End-to-end structural integrity of one simulated tournament (Spec §6)."""

from __future__ import annotations

import numpy as np
import pytest

from wm2026.model import DixonColesModel
from wm2026.tournament import load_tournament, simulate_tournament
from wm2026.tournament.types import STAGE_GROUP


@pytest.fixture(scope="module")
def tournament():
    # Deterministic inline model so the test never depends on trained artifacts.
    model = DixonColesModel(mu=0.1, gamma=0.25, beta=0.18, rho=-0.04)
    return load_tournament(model=model)


def test_config_is_complete(tournament):
    assert len(tournament.teams) == 48
    assert len(tournament.groups) == 12
    assert all(len(codes) == 4 for codes in tournament.groups.values())
    # 16 R32 matches + 16 later knockout matches = 32 knockout matches.
    assert len(tournament.r32) == 16
    assert len(tournament.knockout) == 16


def test_single_run_structure(tournament):
    result = simulate_tournament(tournament, np.random.default_rng(2026), collect_events=True)

    # 72 group + 32 knockout = 104 matches.
    assert len(result.group_results) == 72
    assert len(result.ko_results) == 32

    # Exactly 32 teams reach the knockout phase: 24 top-twos + 8 thirds.
    assert len(result.qualified()) == 32
    assert len(result.qualified_thirds) == 8

    # Every knockout tie has a winner; champion is a real team.
    for r in result.ko_results.values():
        assert r.winner in tournament.teams
    assert result.champion in tournament.teams
    assert result.runner_up != result.champion

    # Group tables are complete and well-formed.
    for table in result.group_tables.values():
        assert len(table.rows) == 4
        assert all(row.played == 3 for row in table.rows)


def test_event_stream_is_emitted(tournament):
    result = simulate_tournament(tournament, np.random.default_rng(1), collect_events=True)
    types = {e["type"] for e in result.events}
    assert {"match_result", "table_update", "stage_change", "bracket_update", "champion"} <= types
    # One match_result per match played.
    assert sum(e["type"] == "match_result" for e in result.events) == 104
    # First emitted match is a group game.
    first_match = next(e for e in result.events if e["type"] == "match_result")
    assert first_match["stage"] == STAGE_GROUP


def test_seed_reproducibility(tournament):
    a = simulate_tournament(tournament, np.random.default_rng(99))
    b = simulate_tournament(tournament, np.random.default_rng(99))
    assert a.champion == b.champion
    assert [r.code for r in a.group_tables["A"].rows] == [r.code for r in b.group_tables["A"].rows]
