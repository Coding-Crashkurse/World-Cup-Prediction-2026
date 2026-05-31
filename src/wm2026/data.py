"""Dataset acquisition and loading (Spec §4).

Primary source: the *International football results from 1872 to present* dataset.
The Kaggle version requires auth, but its author (martj42) maintains an identical
free GitHub mirror with ``results.csv``, which we download directly.

Columns: date, home_team, away_team, home_score, away_score, tournament, city,
country, neutral.
"""

from __future__ import annotations

import httpx
import pandas as pd

from .paths import RESULTS_CSV, ensure_dirs

RESULTS_URL = "https://raw.githubusercontent.com/martj42/international_results/master/results.csv"


def download_results(force: bool = False) -> None:
    """Download ``results.csv`` to the local data directory."""
    ensure_dirs()
    if RESULTS_CSV.exists() and not force:
        return
    with httpx.Client(timeout=60.0, follow_redirects=True) as client:
        resp = client.get(RESULTS_URL)
        resp.raise_for_status()
        RESULTS_CSV.write_bytes(resp.content)


def load_results() -> pd.DataFrame:
    """Load match results as a cleaned, chronologically sorted DataFrame.

    Returns rows with a parsed ``date``, integer scores and a boolean
    ``neutral`` flag. Matches missing scores (future fixtures) are dropped.
    """
    if not RESULTS_CSV.exists():
        raise FileNotFoundError(f"{RESULTS_CSV} not found. Run `wm2026 download-data` first.")
    df = pd.read_csv(RESULTS_CSV)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date", "home_score", "away_score"])
    df["home_score"] = df["home_score"].astype(int)
    df["away_score"] = df["away_score"].astype(int)
    df["neutral"] = df["neutral"].astype(bool)
    # Normalise whitespace on team names so joins are stable.
    df["home_team"] = df["home_team"].str.strip()
    df["away_team"] = df["away_team"].str.strip()
    df = df.sort_values("date").reset_index(drop=True)
    return df
