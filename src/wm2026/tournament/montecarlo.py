"""Monte-Carlo aggregation of tournament probabilities (Spec §6, §7)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

import numpy as np

from .engine import _REACH_ORDER, simulate_tournament
from .loader import Tournament
from .types import STAGE_FINAL, STAGE_R32

# Cumulative milestones, each as the minimum "reached" rank that satisfies it.
_MILESTONES: dict[str, int] = {
    "pR32": _REACH_ORDER[STAGE_R32],  # reached the knockout phase
    "pR16": _REACH_ORDER["R16"],
    "pQF": _REACH_ORDER["QF"],
    "pSF": _REACH_ORDER["SF"],
    "pFinal": _REACH_ORDER[STAGE_FINAL],
    "pTitle": _REACH_ORDER["champion"],
}

@dataclass
class MonteCarloAggregator:
    teams: list[str]
    runs: int = 0
    total: int = 0
    group_winner: dict[str, int] = field(default_factory=dict)
    group_second: dict[str, int] = field(default_factory=dict)
    milestones: dict[str, dict[str, int]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.group_winner = dict.fromkeys(self.teams, 0)
        self.group_second = dict.fromkeys(self.teams, 0)
        self.milestones = {m: dict.fromkeys(self.teams, 0) for m in _MILESTONES}

    def update(self, result) -> None:
        self.runs += 1
        for code, rank in result.group_rank.items():
            if rank == 1:
                self.group_winner[code] += 1
            elif rank == 2:
                self.group_second[code] += 1
        for code, stage in result.reached.items():
            order = _REACH_ORDER[stage]
            for m, threshold in _MILESTONES.items():
                if order >= threshold:
                    self.milestones[m][code] += 1

    def probabilities(self) -> list[dict]:
        """Per-team probability rows, sorted by title chance descending."""
        n = max(self.runs, 1)
        rows = []
        for code in self.teams:
            row = {
                "team": code,
                "pGroupWinner": self.group_winner[code] / n,
                "pGroupSecond": self.group_second[code] / n,
            }
            row.update({m: self.milestones[m][code] / n for m in _MILESTONES})
            rows.append(row)
        rows.sort(key=lambda r: (-r["pTitle"], -r["pFinal"], -r["pR32"]))
        return rows

    def to_event(self) -> dict:
        return {
            "type": "probabilities",
            "runsDone": self.runs,
            "runsTotal": self.total,
            "teams": [
                {k: (round(v, 5) if isinstance(v, float) else v) for k, v in row.items()}
                for row in self.probabilities()
            ],
        }


def run_montecarlo(
    t: Tournament,
    n: int,
    *,
    seed: int | None = None,
    progress_callback: Callable[[MonteCarloAggregator], None] | None = None,
    callback_every: int = 250,
) -> MonteCarloAggregator:
    """Simulate the tournament ``n`` times and aggregate probabilities.

    ``progress_callback`` (if given) is invoked every ``callback_every`` runs and
    once at the end — used by the WebSocket layer to stream live convergence.
    """
    rng = np.random.default_rng(seed)
    agg = MonteCarloAggregator(teams=list(t.teams), total=n)
    for i in range(n):
        result = simulate_tournament(t, rng, collect_events=False)
        agg.update(result)
        done = i + 1
        # Emit on a fixed staircase: every `callback_every` runs, plus the final.
        if progress_callback and (done % callback_every == 0 or done == n):
            progress_callback(agg)
    return agg
