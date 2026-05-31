"""Rolling Elo ratings, World-Football-Elo style (Spec §4).

Elo is the strongest single baseline predictor for international football and it
naturally handles the long tail of teams with few matches. We walk the match
history chronologically, and for every match we:

1. record each side's *pre-match* rating (used as a model feature), then
2. update both ratings from the result.

The update follows the well-known eloratings.net formulation:

    R' = R + K * G * (W - We)

* ``K``  — base weight from match importance (friendly … World Cup final).
* ``G``  — goal-difference multiplier (a 3-0 win moves more than a 1-0 win).
* ``We`` — expected result from the rating gap incl. a home-advantage offset.
* ``W``  — actual result (1 win / 0.5 draw / 0 loss).
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

import pandas as pd

DEFAULT_RATING = 1500.0
HOME_ADVANTAGE = 100.0  # Elo points added to the home side on non-neutral ground.

# Base K-factor by match importance, keyed by the EXACT tournament name. The
# martj42 dataset uses a controlled vocabulary in its ``tournament`` column, so
# exact lookup is both safe and clear — unlike substring matching, where
# ``"FIFA World Cup" in name`` would also (wrongly) swallow
# ``"FIFA World Cup qualification"``. Qualifiers share the same " qualification"
# suffix across confederations and are detected with a precise ``endswith``.
QUALIFIER_K = 40.0
FRIENDLY_K = 20.0
DEFAULT_K = 30.0  # any other competitive match not explicitly listed
QUALIFICATION_SUFFIX = " qualification"

IMPORTANCE_BY_TOURNAMENT: dict[str, float] = {
    "FIFA World Cup": 60.0,
    "FIFA Confederations Cup": 50.0,
    "Copa América": 50.0,
    "UEFA Euro": 50.0,
    "African Cup of Nations": 50.0,
    "AFC Asian Cup": 50.0,
    "Gold Cup": 50.0,
    "CONCACAF Championship": 50.0,
    "Oceania Nations Cup": 50.0,
    "UEFA Nations League": 40.0,
    "CONCACAF Nations League": 40.0,
    "Friendly": FRIENDLY_K,
}


def importance_k(tournament: str) -> float:
    """Map a tournament name to a base K-factor.

    Exact lookup against a known vocabulary; qualifiers (any name ending in
    " qualification") share one weight; unknown competitive matches fall back to
    a sensible default.
    """
    name = (tournament or "").strip()
    if name.endswith(QUALIFICATION_SUFFIX):
        return QUALIFIER_K
    return IMPORTANCE_BY_TOURNAMENT.get(name, DEFAULT_K)


def goal_diff_multiplier(goal_diff: int) -> float:
    """Goal-difference multiplier G (eloratings.net)."""
    gd = abs(goal_diff)
    if gd <= 1:
        return 1.0
    if gd == 2:
        return 1.5
    return (11.0 + gd) / 8.0


def expected_score(rating_a: float, rating_b: float) -> float:
    """Logistic expectation that A beats B given their (offset) ratings."""
    return 1.0 / (1.0 + 10.0 ** ((rating_b - rating_a) / 400.0))


@dataclass
class EloResult:
    """Output of an Elo pass over the match history."""

    ratings: dict[str, float]
    """Final rating per team."""
    history: pd.DataFrame
    """Input matches augmented with ``home_elo_pre`` / ``away_elo_pre`` columns."""
    last_played: dict[str, pd.Timestamp]
    """Most recent match date per team (used to flag stale ratings)."""


def compute_elo(
    matches: pd.DataFrame,
    *,
    default_rating: float = DEFAULT_RATING,
    home_advantage: float = HOME_ADVANTAGE,
) -> EloResult:
    """Compute rolling Elo ratings over a chronologically sorted match frame.

    ``matches`` must contain: date, home_team, away_team, home_score,
    away_score, neutral, tournament.
    """
    ratings: dict[str, float] = defaultdict(lambda: default_rating)
    last_played: dict[str, pd.Timestamp] = {}

    home_pre = []
    away_pre = []

    for row in matches.itertuples(index=False):
        home, away = row.home_team, row.away_team
        r_home = ratings[home]
        r_away = ratings[away]
        home_pre.append(r_home)
        away_pre.append(r_away)

        # Home-advantage offset only on non-neutral ground.
        hfa = 0.0 if row.neutral else home_advantage
        we_home = expected_score(r_home + hfa, r_away)

        gd = row.home_score - row.away_score
        if gd > 0:
            w_home = 1.0
        elif gd == 0:
            w_home = 0.5
        else:
            w_home = 0.0

        k = importance_k(row.tournament) * goal_diff_multiplier(gd)
        delta = k * (w_home - we_home)
        ratings[home] = r_home + delta
        ratings[away] = r_away - delta
        last_played[home] = row.date
        last_played[away] = row.date

    history = matches.copy()
    history["home_elo_pre"] = home_pre
    history["away_elo_pre"] = away_pre

    return EloResult(ratings=dict(ratings), history=history, last_played=last_played)
