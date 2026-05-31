"""Road to the Cup — statistical FIFA World Cup 2026 simulator.

The package is split into three layers (Spec §3):

* ``wm2026.model``  — the offline-trained match model (Elo + Dixon-Coles Poisson).
* ``wm2026.tournament`` — the headless simulation engine (groups, knockout, MC).
* ``wm2026.api`` — the FastAPI backend that streams "broadcast" events.

Training happens offline via ``wm2026.train``; the backend only *loads* artifacts.
"""

__version__ = "0.1.0"
