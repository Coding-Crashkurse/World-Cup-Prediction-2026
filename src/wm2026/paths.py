"""Canonical filesystem locations for data, config and trained artifacts."""

from __future__ import annotations

from pathlib import Path

# .../src/wm2026/paths.py  ->  project root is three parents up.
PACKAGE_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_ROOT.parent.parent

DATA_DIR = PROJECT_ROOT / "data"
ARTIFACTS_DIR = PROJECT_ROOT / "artifacts"
CONFIG_DIR = PACKAGE_ROOT / "config"

# Raw dataset: martj42/international_results (the free GitHub mirror of the
# Kaggle "International football results from 1872 to present" dataset).
RESULTS_CSV = DATA_DIR / "results.csv"

# Trained model artifacts.
MODEL_FILE = ARTIFACTS_DIR / "model.joblib"
ELO_FILE = ARTIFACTS_DIR / "elo_ratings.json"
ELO_HISTORY_FILE = ARTIFACTS_DIR / "elo_history.json"

# Tournament config (Spec §4).
TEAMS_FILE = CONFIG_DIR / "teams.json"
GROUPS_FILE = CONFIG_DIR / "groups.json"
KNOCKOUT_FILE = CONFIG_DIR / "knockout_bracket.json"
SCHEDULE_FILE = CONFIG_DIR / "schedule.json"
THIRD_PLACE_MATRIX_FILE = CONFIG_DIR / "third_place_matrix.json"


def ensure_dirs() -> None:
    """Create the regenerable output directories if they do not yet exist."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
