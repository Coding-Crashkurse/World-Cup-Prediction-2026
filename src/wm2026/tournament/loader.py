"""Load verified config + trained artifacts into a ready-to-simulate object."""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from ..model import DixonColesModel
from ..paths import (
    ELO_FILE,
    GROUPS_FILE,
    KNOCKOUT_FILE,
    MODEL_FILE,
    TEAMS_FILE,
    THIRD_PLACE_MATRIX_FILE,
)
from .types import Team


@dataclass
class SimConfig:
    """Tunable knobs for one simulation (Spec §11 open points)."""

    # Host home advantage (Spec §2). Applied via the model's home-field term.
    host_group_advantage: bool = True
    host_knockout_advantage: bool = False
    # Knockout draw resolution.
    extra_time_fraction: float = 1.0 / 3.0  # 30 of 90 minutes
    penalty_elo_scale: float = 1000.0  # large -> shootout near coin-flip
    penalty_base_success: float = 0.75
    # Final group tiebreaker once points/GD/goals/H2H are exhausted.
    final_tiebreaker: str = "lots"  # "lots" (random) | "fifa" (Elo proxy)


@dataclass
class Tournament:
    teams: dict[str, Team]
    groups: dict[str, list[str]]  # group letter -> 4 team codes
    r32: list[dict]
    knockout: list[dict]
    third_matrix: dict  # {"lookup":..., slot meta}
    config: SimConfig = field(default_factory=SimConfig)
    model: DixonColesModel | None = None

    @property
    def hosts(self) -> list[str]:
        return [c for c, t in self.teams.items() if t.is_host]

    def require_model(self) -> DixonColesModel:
        if self.model is None:
            raise RuntimeError(
                "No match model loaded. Run `uv run wm2026 train` first, or pass model=."
            )
        return self.model


def _load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_tournament(
    *, config: SimConfig | None = None, model: DixonColesModel | None = None
) -> Tournament:
    """Build a Tournament from config files + trained Elo/model artifacts.

    Elo is taken from ``artifacts/elo_ratings.json`` when present (the trained
    values), otherwise from the seed fallbacks in ``teams.json``.
    """
    teams_raw = _load_json(TEAMS_FILE)["teams"]
    trained_elo: dict[str, float] = {}
    if ELO_FILE.exists():
        trained_elo = _load_json(ELO_FILE).get("ratings", {})

    teams: dict[str, Team] = {}
    for t in teams_raw:
        teams[t["code"]] = Team(
            code=t["code"],
            name=t["name"],
            iso2=t["iso2"],
            confederation=t["confederation"],
            is_host=bool(t.get("isHost", False)),
            elo=float(trained_elo.get(t["code"], t["elo"])),
        )

    groups_raw = _load_json(GROUPS_FILE)
    groups = {k: v for k, v in groups_raw.items() if not k.startswith("_")}

    bracket = _load_json(KNOCKOUT_FILE)
    third_matrix = _load_json(THIRD_PLACE_MATRIX_FILE)

    loaded_model = model
    if loaded_model is None and MODEL_FILE.exists():
        loaded_model = DixonColesModel.load()

    return Tournament(
        teams=teams,
        groups=groups,
        r32=bracket["r32"],
        knockout=bracket["knockout"],
        third_matrix=third_matrix,
        config=config or SimConfig(),
        model=loaded_model,
    )
