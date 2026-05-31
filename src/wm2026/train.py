"""Offline training pipeline (Spec §10, phase 1).

Produces two artifacts the backend later just *loads*:

* ``artifacts/model.joblib``      — the fitted Dixon-Coles model (+ metrics).
* ``artifacts/elo_ratings.json``  — final Elo per WC-2026 team code.

Run:  uv run wm2026 train  [--half-life 4.0] [--no-backtest]
"""

from __future__ import annotations

import json
from dataclasses import dataclass

import numpy as np
import pandas as pd

from .data import load_results
from .elo import compute_elo
from .features import build_training_data
from .metrics import BacktestMetrics, log_loss, ranked_probability_score
from .model import DixonColesModel, fit_dixon_coles
from .paths import ELO_FILE, ELO_HISTORY_FILE, TEAMS_FILE, ensure_dirs


@dataclass
class TrainingArtifacts:
    model: DixonColesModel
    ratings: dict[str, float]
    unmatched: list[str]


def _fit_from_history(
    history: pd.DataFrame, half_life_years: float, max_years: float, reference_date=None
) -> DixonColesModel:
    td = build_training_data(
        history,
        half_life_years=half_life_years,
        max_years=max_years,
        reference_date=reference_date,
    )
    model = fit_dixon_coles(td.elo_diff, td.home_field, td.home_goals, td.away_goals, td.weights)
    model.n_train = len(td.weights)
    model.half_life_years = half_life_years
    return model


def run_backtest(
    history: pd.DataFrame,
    *,
    half_life_years: float,
    max_years: float,
    test_years: float = 2.0,
) -> BacktestMetrics:
    """Temporal holdout: fit on the past, score the most recent window.

    Elo features are leak-free (rolling, past-only); refitting the model on the
    train split only keeps the parameters honest too.
    """
    ref = history["date"].max()
    split = ref - pd.Timedelta(days=int(test_years * 365.25))
    train_hist = history[history["date"] < split]
    test = history[history["date"] >= split]

    model = _fit_from_history(train_hist, half_life_years, max_years, reference_date=split)

    n = len(test)
    probs = np.zeros((n, 3))
    pred_goals = np.zeros(n)
    for i, row in enumerate(test.itertuples(index=False)):
        neutral = bool(row.neutral)
        p_home, p_draw, p_away = model.outcome_probs(row.home_elo_pre, row.away_elo_pre, neutral)
        probs[i] = (p_home, p_draw, p_away)
        lam, mu = model.rates(row.home_elo_pre, row.away_elo_pre, neutral)
        pred_goals[i] = lam + mu

    gd = (test["home_score"] - test["away_score"]).to_numpy()
    outcomes = np.where(gd > 0, 0, np.where(gd == 0, 1, 2))
    actual_goals = (test["home_score"] + test["away_score"]).to_numpy()

    return BacktestMetrics(
        n=n,
        rps=ranked_probability_score(probs, outcomes),
        log_loss=log_loss(probs, outcomes),
        accuracy=float(np.mean(np.argmax(probs, axis=1) == outcomes)),
        mean_goals_pred=float(np.mean(pred_goals)),
        mean_goals_actual=float(np.mean(actual_goals)),
    )


def map_ratings_to_teams(elo_ratings: dict[str, float]) -> tuple[dict[str, float], list[str]]:
    """Resolve each WC-2026 team's Elo via its dataset name / aliases."""
    teams = json.loads(TEAMS_FILE.read_text(encoding="utf-8"))["teams"]
    resolved: dict[str, float] = {}
    unmatched: list[str] = []
    for t in teams:
        names = [t["datasetName"], *t.get("aliases", []), t["name"]]
        rating = next((elo_ratings[name] for name in names if name in elo_ratings), None)
        if rating is None:
            unmatched.append(f"{t['code']} ({t['datasetName']})")
            rating = float(t["elo"])  # fall back to the seed value
        resolved[t["code"]] = round(float(rating), 1)
    return resolved, unmatched


def build_elo_history(
    history: pd.DataFrame, teams: list[dict], *, window_start: str = "1994-01-01"
) -> dict:
    """Per-team Elo trajectory (quarterly, downsampled) for the visualization.

    Uses each team's *pre-match* rating as the value entering each fixture, so
    every line literally starts at 1500 on the team's debut and steps after
    every match. Quarterly resampling keeps the artifact small.
    """
    home = history[["date", "home_team", "home_elo_pre"]].rename(
        columns={"home_team": "team", "home_elo_pre": "elo"}
    )
    away = history[["date", "away_team", "away_elo_pre"]].rename(
        columns={"away_team": "team", "away_elo_pre": "elo"}
    )
    long = pd.concat([home, away], ignore_index=True)
    start = pd.Timestamp(window_start)
    series: dict[str, list] = {}
    for t in teams:
        names = [t["datasetName"], *t.get("aliases", []), t["name"]]
        sub = long[long["team"].isin(names) & (long["date"] >= start)]
        if sub.empty:
            continue
        quarterly = sub.set_index("date")["elo"].sort_index().resample("QS").last().ffill().dropna()
        series[t["code"]] = [
            [d.strftime("%Y-%m-%d"), round(float(v), 1)] for d, v in quarterly.items()
        ]
    return {"baseline": 1500.0, "windowStart": window_start, "series": series}


def train(
    *,
    half_life_years: float = 4.0,
    max_years: float = 16.0,
    backtest: bool = True,
    since: str = "1995-01-01",
) -> TrainingArtifacts:
    """Full training run. Saves artifacts and returns them.

    ``since`` drops all matches before that date, so Elo resets to 1500 there
    and every team's line starts from the common 1500 baseline. Verified to
    barely move current ratings (corr 0.99 vs full history) — modern football is
    what matters for a 2026 prediction.
    """
    ensure_dirs()
    history_df = load_results()
    history_df = history_df[history_df["date"] >= pd.Timestamp(since)].reset_index(drop=True)
    elo = compute_elo(history_df)

    model = _fit_from_history(elo.history, half_life_years, max_years)
    model.trained_through = str(elo.history["date"].max().date())
    if backtest:
        model.metrics = run_backtest(
            elo.history, half_life_years=half_life_years, max_years=max_years
        ).as_dict()
    model.save()

    ratings, unmatched = map_ratings_to_teams(elo.ratings)
    ELO_FILE.write_text(
        json.dumps(
            {
                "computedThrough": model.trained_through,
                "homeAdvantageElo": 100.0,
                "ratings": dict(sorted(ratings.items(), key=lambda kv: -kv[1])),
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    teams_list = json.loads(TEAMS_FILE.read_text(encoding="utf-8"))["teams"]
    ELO_HISTORY_FILE.write_text(
        json.dumps(build_elo_history(elo.history, teams_list, window_start=since)),
        encoding="utf-8",
    )
    return TrainingArtifacts(model=model, ratings=ratings, unmatched=unmatched)
