"""Core value types for the simulation engine."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import numpy as np

# Stage identifiers used across events, results and aggregation.
STAGE_GROUP = "group"
STAGE_R32 = "R32"
STAGE_R16 = "R16"
STAGE_QF = "QF"
STAGE_SF = "SF"
STAGE_THIRD = "3P"
STAGE_FINAL = "F"

# Knockout rounds in order; the value is how far a team reached.
KO_ROUNDS = [STAGE_R32, STAGE_R16, STAGE_QF, STAGE_SF, STAGE_FINAL]


class ScoreModel(Protocol):
    """What the engine needs from a match model (DixonColesModel satisfies it)."""

    def rates(self, elo_home: float, elo_away: float, neutral: bool) -> tuple[float, float]: ...

    def sample_score(
        self,
        elo_home: float,
        elo_away: float,
        rng: np.random.Generator,
        neutral: bool,
        rate_scale: float,
    ) -> tuple[int, int]: ...


@dataclass(frozen=True)
class Team:
    code: str
    name: str
    iso2: str
    confederation: str
    is_host: bool
    elo: float


@dataclass
class MatchResult:
    """Outcome of one played match."""

    stage: str
    home: str  # team code
    away: str  # team code
    home_goals: int
    away_goals: int
    xg_home: float
    xg_away: float
    neutral: bool
    group: str | None = None
    match_no: int | None = None
    decided_by: str = "regulation"  # regulation | extra_time | penalties
    winner: str | None = None  # code (knockout only)
    home_pens: int | None = None
    away_pens: int | None = None

    @property
    def loser(self) -> str | None:
        if self.winner is None:
            return None
        return self.away if self.winner == self.home else self.home

    def to_event(self) -> dict:
        return {
            "stage": self.stage,
            "group": self.group,
            "matchNo": self.match_no,
            "home": self.home,
            "away": self.away,
            "score": [self.home_goals, self.away_goals],
            "xg": [round(self.xg_home, 2), round(self.xg_away, 2)],
            "neutral": self.neutral,
            "decidedBy": self.decided_by,
            "winner": self.winner,
            "pens": [self.home_pens, self.away_pens] if self.home_pens is not None else None,
        }


@dataclass
class GroupRow:
    code: str
    played: int = 0
    win: int = 0
    draw: int = 0
    loss: int = 0
    gf: int = 0
    ga: int = 0

    @property
    def pts(self) -> int:
        return 3 * self.win + self.draw

    @property
    def gd(self) -> int:
        return self.gf - self.ga

    def to_event(self, rank: int) -> dict:
        return {
            "team": self.code,
            "rank": rank,
            "p": self.played,
            "w": self.win,
            "d": self.draw,
            "l": self.loss,
            "gf": self.gf,
            "ga": self.ga,
            "gd": self.gd,
            "pts": self.pts,
        }


@dataclass
class GroupTable:
    group: str
    rows: list[GroupRow]  # ordered best-first after tiebreakers

    def to_event(self) -> dict:
        return {
            "group": self.group,
            "rows": [r.to_event(i + 1) for i, r in enumerate(self.rows)],
        }
