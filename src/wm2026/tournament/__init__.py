"""Headless tournament simulation engine (Spec §6).

Public surface:

* :class:`~wm2026.tournament.loader.Tournament` — loaded config + model.
* :func:`~wm2026.tournament.engine.simulate_tournament` — one full run.
* :func:`~wm2026.tournament.montecarlo.run_montecarlo` — N runs -> probabilities.
"""

from .engine import simulate_tournament
from .loader import SimConfig, Tournament, load_tournament
from .montecarlo import MonteCarloAggregator, run_montecarlo

__all__ = [
    "MonteCarloAggregator",
    "SimConfig",
    "Tournament",
    "load_tournament",
    "run_montecarlo",
    "simulate_tournament",
]
