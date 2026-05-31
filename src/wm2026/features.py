"""Assemble model training inputs from the Elo-augmented match history (Spec §4).

We keep the feature set deliberately small — the Elo gap plus a home-field flag
— because Elo already absorbs most attack/defence quality and generalises to the
data-sparse teams that populate a World Cup. Training matches are weighted by
recency (an exponential half-life) and by importance (friendlies count less).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .elo import importance_k


@dataclass
class TrainingData:
    elo_diff: np.ndarray  # home_elo_pre - away_elo_pre
    home_field: np.ndarray  # 1.0 if non-neutral (home side at home), else 0.0
    home_goals: np.ndarray
    away_goals: np.ndarray
    weights: np.ndarray
    dates: pd.Series


def importance_weight(tournament: str) -> float:
    """Down-weight friendlies relative to competitive matches (cap at 1.0)."""
    return min(1.0, importance_k(tournament) / 40.0)


def build_training_data(
    history: pd.DataFrame,
    *,
    half_life_years: float = 4.0,
    max_years: float = 16.0,
    reference_date: pd.Timestamp | None = None,
) -> TrainingData:
    """Turn the Elo history into weighted training arrays.

    ``history`` must contain ``home_elo_pre`` / ``away_elo_pre`` (from
    :func:`wm2026.elo.compute_elo`). Matches older than ``max_years`` are
    dropped; the rest are weighted by ``0.5 ** (years_ago / half_life_years)``
    times an importance factor.
    """
    ref = reference_date if reference_date is not None else history["date"].max()
    years_ago = (ref - history["date"]).dt.days / 365.25

    df = history.loc[years_ago <= max_years].copy()
    years_ago = years_ago.loc[df.index]

    decay = np.power(0.5, years_ago / half_life_years)
    imp = df["tournament"].map(importance_weight).to_numpy()
    weights = decay.to_numpy() * imp

    return TrainingData(
        elo_diff=(df["home_elo_pre"] - df["away_elo_pre"]).to_numpy(dtype=float),
        home_field=np.where(df["neutral"].to_numpy(), 0.0, 1.0),
        home_goals=df["home_score"].to_numpy(dtype=int),
        away_goals=df["away_score"].to_numpy(dtype=int),
        weights=weights,
        dates=df["date"],
    )
