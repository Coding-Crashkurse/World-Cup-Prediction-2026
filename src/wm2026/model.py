"""Match model: Elo-driven Poisson with a Dixon-Coles correction (Spec §5).

Why goal-based and not a win/draw/loss classifier? Group tables are decided by
goal difference and goals scored, so we must predict *scorelines*, not just
outcomes. Goals are well approximated by a Poisson process at the low counts
typical of football, which is exactly where this model lives.

Expected scoring rates are a log-linear function of the Elo gap plus a home
boost::

    log λ_home = μ + γ·home_field + β·(elo_home − elo_away)/100
    log λ_away = μ            − β·(elo_home − elo_away)/100

The four low-score cells (0-0, 1-0, 0-1, 1-1) are then re-weighted by the
Dixon-Coles τ(x, y; ρ) factor, which corrects the independence assumption of
two separate Poissons. Parameters (μ, γ, β, ρ) are fit once, offline, by
maximising a time- and importance-weighted log-likelihood over match history.

This 4-parameter form is deliberately lean: Elo already encodes most of a
team's attacking/defensive quality, so it generalises cleanly to all 48 teams
including those with sparse recent data. The optional XGBoost hybrid (Spec §5)
can later replace the mean function without touching the sampling code.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

import joblib
import numpy as np
from scipy.optimize import minimize
from scipy.special import gammaln

from .paths import MODEL_FILE

ELO_SCALE = 100.0
MAX_GOALS = 10  # truncation for the score-probability grid


def _dc_tau(
    x: np.ndarray, y: np.ndarray, lam: np.ndarray, mu: np.ndarray, rho: float
) -> np.ndarray:
    """Dixon-Coles low-score dependence factor τ(x, y), vectorised."""
    tau = np.ones_like(lam, dtype=float)
    m00 = (x == 0) & (y == 0)
    m01 = (x == 0) & (y == 1)
    m10 = (x == 1) & (y == 0)
    m11 = (x == 1) & (y == 1)
    tau[m00] = 1.0 - lam[m00] * mu[m00] * rho
    tau[m01] = 1.0 + lam[m01] * rho
    tau[m10] = 1.0 + mu[m10] * rho
    tau[m11] = 1.0 - rho
    return tau


@dataclass
class DixonColesModel:
    """Trained match model. Persisted as a small joblib artifact."""

    mu: float
    gamma: float
    beta: float
    rho: float
    elo_scale: float = ELO_SCALE
    # Provenance / calibration metadata (filled by the trainer).
    n_train: int = 0
    trained_through: str = ""
    half_life_years: float = 0.0
    metrics: dict | None = None

    def rates(self, elo_home: float, elo_away: float, neutral: bool = True) -> tuple[float, float]:
        """Return expected goals (λ_home, λ_away) for a single fixture."""
        d = (elo_home - elo_away) / self.elo_scale
        home_field = 0.0 if neutral else 1.0
        lam = np.exp(self.mu + self.gamma * home_field + self.beta * d)
        mu_rate = np.exp(self.mu - self.beta * d)
        return float(lam), float(mu_rate)

    def score_matrix(self, lam: float, mu_rate: float, max_goals: int = MAX_GOALS) -> np.ndarray:
        """Joint P(home=x, away=y) grid incl. the Dixon-Coles correction."""
        goals = np.arange(max_goals + 1)
        # Independent Poisson pmfs.
        log_ph = goals * np.log(lam) - lam - gammaln(goals + 1)
        log_pa = goals * np.log(mu_rate) - mu_rate - gammaln(goals + 1)
        grid = np.exp(log_ph[:, None] + log_pa[None, :])
        # Apply τ to the four low-score cells.
        grid[0, 0] *= 1.0 - lam * mu_rate * self.rho
        grid[0, 1] *= 1.0 + lam * self.rho
        grid[1, 0] *= 1.0 + mu_rate * self.rho
        grid[1, 1] *= 1.0 - self.rho
        grid = np.clip(grid, 0.0, None)
        grid /= grid.sum()
        return grid

    def sample_score(
        self,
        elo_home: float,
        elo_away: float,
        rng: np.random.Generator,
        neutral: bool = True,
        rate_scale: float = 1.0,
    ) -> tuple[int, int]:
        """Sample a concrete scoreline.

        ``rate_scale`` shrinks both rates for shorter periods (e.g. 30/90 for
        knockout extra time).
        """
        lam, mu_rate = self.rates(elo_home, elo_away, neutral)
        grid = self.score_matrix(lam * rate_scale, mu_rate * rate_scale)
        flat = rng.choice(grid.size, p=grid.ravel())
        h, a = divmod(int(flat), grid.shape[1])
        return h, a

    def outcome_probs(
        self, elo_home: float, elo_away: float, neutral: bool = True
    ) -> tuple[float, float, float]:
        """(P(home win), P(draw), P(away win)) — for calibration/diagnostics."""
        lam, mu_rate = self.rates(elo_home, elo_away, neutral)
        grid = self.score_matrix(lam, mu_rate)
        p_home = float(np.tril(grid, -1).sum())  # x > y
        p_draw = float(np.trace(grid))
        p_away = float(np.triu(grid, 1).sum())  # y > x
        return p_home, p_draw, p_away

    def save(self, path=MODEL_FILE) -> None:
        joblib.dump(self, path)

    @staticmethod
    def load(path=MODEL_FILE) -> DixonColesModel:
        return joblib.load(path)

    def as_dict(self) -> dict:
        return asdict(self)


def negative_log_likelihood(
    theta: np.ndarray,
    elo_diff: np.ndarray,
    home_field: np.ndarray,
    x: np.ndarray,
    y: np.ndarray,
    weights: np.ndarray,
) -> float:
    """Weighted negative log-likelihood of the Dixon-Coles Poisson model."""
    mu, gamma, beta, rho = theta
    d = elo_diff / ELO_SCALE
    lam = np.exp(mu + gamma * home_field + beta * d)
    mu_rate = np.exp(mu - beta * d)

    base = x * np.log(lam) - lam - gammaln(x + 1) + y * np.log(mu_rate) - mu_rate - gammaln(y + 1)
    tau = _dc_tau(x, y, lam, mu_rate, rho)
    tau = np.clip(tau, 1e-10, None)
    ll = base + np.log(tau)
    return -float(np.sum(weights * ll))


def fit_dixon_coles(
    elo_diff: np.ndarray,
    home_field: np.ndarray,
    home_goals: np.ndarray,
    away_goals: np.ndarray,
    weights: np.ndarray,
) -> DixonColesModel:
    """Maximum-likelihood fit of (μ, γ, β, ρ)."""
    x = home_goals.astype(float)
    y = away_goals.astype(float)
    theta0 = np.array([0.2, 0.25, 0.4, -0.05])
    bounds = [(-2.0, 2.0), (0.0, 1.0), (0.0, 2.0), (-0.2, 0.2)]
    res = minimize(
        negative_log_likelihood,
        theta0,
        args=(elo_diff, home_field, x, y, weights),
        method="L-BFGS-B",
        bounds=bounds,
    )
    mu, gamma, beta, rho = res.x
    return DixonColesModel(mu=float(mu), gamma=float(gamma), beta=float(beta), rho=float(rho))
