"""Calibration metrics for backtesting (Spec §5).

The goal is *calibration* — probabilities that mean what they say — not raw tip
accuracy. We report the Ranked Probability Score (the standard proper score for
ordered football outcomes), log-loss, argmax accuracy, and a goals sanity check.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class BacktestMetrics:
    n: int
    rps: float
    log_loss: float
    accuracy: float
    mean_goals_pred: float
    mean_goals_actual: float

    def as_dict(self) -> dict:
        return {
            "n": self.n,
            "rps": round(self.rps, 4),
            "log_loss": round(self.log_loss, 4),
            "accuracy": round(self.accuracy, 4),
            "mean_goals_pred": round(self.mean_goals_pred, 3),
            "mean_goals_actual": round(self.mean_goals_actual, 3),
        }


def ranked_probability_score(probs: np.ndarray, outcomes: np.ndarray) -> float:
    """Mean RPS for ordered 3-outcome predictions [home, draw, away].

    ``probs`` is (n, 3); ``outcomes`` is (n,) in {0,1,2}. RPS for r ordered
    categories is ``1/(r-1) * Σ (cumP_i - cumO_i)^2``; lower is better.
    """
    n, r = probs.shape
    cum_p = np.cumsum(probs, axis=1)
    obs = np.zeros_like(probs)
    obs[np.arange(n), outcomes] = 1.0
    cum_o = np.cumsum(obs, axis=1)
    return float(np.mean(np.sum((cum_p - cum_o) ** 2, axis=1) / (r - 1)))


def log_loss(probs: np.ndarray, outcomes: np.ndarray) -> float:
    """Multiclass log-loss with clipping for numerical safety."""
    n = probs.shape[0]
    p = np.clip(probs[np.arange(n), outcomes], 1e-12, 1.0)
    return float(-np.mean(np.log(p)))
