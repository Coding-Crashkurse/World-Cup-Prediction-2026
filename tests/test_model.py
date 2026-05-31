"""Dixon-Coles model: valid distributions, determinism, Elo monotonicity."""

from __future__ import annotations

import numpy as np

from wm2026.elo import importance_k
from wm2026.model import DixonColesModel


def _model() -> DixonColesModel:
    return DixonColesModel(mu=0.1, gamma=0.25, beta=0.18, rho=-0.04)


def test_score_matrix_is_a_distribution():
    grid = _model().score_matrix(1.5, 1.2)
    assert abs(grid.sum() - 1.0) < 1e-9
    assert (grid >= 0).all()


def test_outcome_probs_sum_to_one():
    p_home, p_draw, p_away = _model().outcome_probs(1900, 1700, neutral=True)
    assert abs(p_home + p_draw + p_away - 1.0) < 1e-9
    # Stronger side (home) should be favoured on neutral ground.
    assert p_home > p_away


def test_home_advantage_increases_home_rate():
    m = _model()
    lam_neutral, _ = m.rates(1800, 1800, neutral=True)
    lam_home, _ = m.rates(1800, 1800, neutral=False)
    assert lam_home > lam_neutral


def test_sampling_is_reproducible():
    m = _model()
    s1 = m.sample_score(1900, 1700, np.random.default_rng(123), neutral=True, rate_scale=1.0)
    s2 = m.sample_score(1900, 1700, np.random.default_rng(123), neutral=True, rate_scale=1.0)
    assert s1 == s2


def test_importance_exact_lookup_and_qualifier_suffix():
    assert importance_k("FIFA World Cup") == 60.0
    assert importance_k("FIFA World Cup qualification") == 40.0  # suffix, not the 60 final
    assert importance_k("Friendly") == 20.0
    assert importance_k("Some Obscure Cup") == 30.0  # default
