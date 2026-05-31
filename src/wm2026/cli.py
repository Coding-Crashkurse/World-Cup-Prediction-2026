"""Headless CLI (Spec §10, phase 2): download / train / simulate / serve."""

from __future__ import annotations

import sys
from collections.abc import Iterable
from contextlib import suppress

import numpy as np
import typer
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .tournament import load_tournament, run_montecarlo, simulate_tournament
from .tournament.engine import TournamentResult
from .tournament.loader import Tournament
from .tournament.types import GroupTable, MatchResult

# Windows consoles/pipes default to cp1252 and choke on µ, 🏆, ●, umlauts.
for _stream in (sys.stdout, sys.stderr):
    with suppress(AttributeError, ValueError):  # not a reconfigurable TextIOWrapper
        _stream.reconfigure(encoding="utf-8", errors="replace")

app = typer.Typer(add_completion=False, help="Road to the Cup — WM 2026 simulator.")
console = Console()

ROUND_NAMES = {
    "R32": "Round of 32",
    "R16": "Round of 16",
    "QF": "Quarter-finals",
    "SF": "Semi-finals",
    "3P": "Third-place play-off",
    "F": "Final",
}
KNOCKOUT_ROUNDS = ("R32", "R16", "QF", "SF", "3P", "F")
PROB_COLUMNS = (
    ("Win Grp", "pGroupWinner"),
    ("R16", "pR16"),
    ("QF", "pQF"),
    ("SF", "pSF"),
    ("Final", "pFinal"),
    ("Title", "pTitle"),
)


def _pct(x: float) -> str:
    return f"{100 * x:4.1f}%" if x >= 0.0005 else "   –"


def _name(t: Tournament, code: str) -> str:
    return t.teams[code].name


def _note(r: MatchResult) -> str:
    if r.decided_by == "penalties":
        return f"pens {r.home_pens}-{r.away_pens}"
    if r.decided_by == "extra_time":
        return "a.e.t."
    return ""


def _group_table(t: Tournament, gt: GroupTable) -> Table:
    table = Table(title=f"Group {gt.group}", box=box.SIMPLE_HEAVY, title_style="bold cyan")
    table.add_column("#", justify="right")
    table.add_column("Team")
    for col in ("P", "W", "D", "L", "GF", "GA", "GD", "Pts"):
        table.add_column(col, justify="right")
    for i, row in enumerate(gt.rows):
        # Top two qualify (green), the third is a play-off hopeful (amber).
        style = "green" if i < 2 else "yellow" if i == 2 else None
        marker = "●" if i < 2 else "○" if i == 2 else " "
        table.add_row(
            f"{i + 1} {marker}",
            _name(t, row.code),
            *map(str, (row.played, row.win, row.draw, row.loss, row.gf, row.ga)),
            f"{row.gd:+d}",
            str(row.pts),
            style=style,
        )
    return table


def _knockout_table(t: Tournament, matches: Iterable[MatchResult]) -> Table:
    table = Table(box=box.SIMPLE, show_header=False, pad_edge=False)
    table.add_column(justify="right")
    table.add_column(justify="center")
    table.add_column(justify="left")
    table.add_column(justify="left", style="dim")
    for r in matches:
        table.add_row(
            Text(_name(t, r.home), style="bold green" if r.winner == r.home else ""),
            f"{r.home_goals}–{r.away_goals}",
            Text(_name(t, r.away), style="bold green" if r.winner == r.away else ""),
            _note(r),
        )
    return table


@app.command("download-data")
def download_data(force: bool = typer.Option(False, help="Re-download even if present.")) -> None:
    """Download the historical international-results dataset."""
    from .data import download_results
    from .paths import RESULTS_CSV

    console.print("Downloading historical results…")
    download_results(force=force)
    console.print(f"[green]done[/] — saved to {RESULTS_CSV}")


@app.command()
def train(
    half_life: float = typer.Option(4.0, help="Recency half-life in years."),
    backtest: bool = typer.Option(True, help="Run a temporal-holdout backtest."),
    since: str = typer.Option(
        "1995-01-01", help="Drop matches before this date; Elo resets to 1500."
    ),
) -> None:
    """Compute Elo and fit the Dixon-Coles model (offline) -> artifacts/."""
    from .train import train as run_train

    console.print("Training model (Elo + Dixon-Coles)…")
    arts = run_train(half_life_years=half_life, backtest=backtest, since=since)
    m = arts.model
    console.print(f"[green]done[/] — fitted on {m.n_train:,} matches through {m.trained_through}")
    console.print(f"  μ={m.mu:.3f}  γ(home)={m.gamma:.3f}  β(elo)={m.beta:.3f}  ρ(DC)={m.rho:.3f}")
    if m.metrics:
        console.print(f"  backtest: {m.metrics}")
    if arts.unmatched:
        console.print(f"[yellow]unmatched (seed Elo used):[/] {', '.join(arts.unmatched)}")

    table = Table(title="Top Elo ratings", box=box.SIMPLE)
    table.add_column("Team")
    table.add_column("Elo", justify="right")
    for code, elo in sorted(arts.ratings.items(), key=lambda kv: -kv[1])[:12]:
        table.add_row(code, f"{elo:.0f}")
    console.print(table)


@app.command()
def simulate(
    mode: str = typer.Option("single", help="'single' or 'montecarlo'."),
    n: int = typer.Option(10000, "-n", help="Monte-Carlo iterations."),
    seed: int | None = typer.Option(None, help="Random seed for reproducibility."),
) -> None:
    """Run a single dramatic tournament or a Monte-Carlo probability sweep."""
    t = load_tournament()
    try:
        t.require_model()
    except RuntimeError as exc:
        console.print(f"[red]{exc}[/]")
        raise typer.Exit(1) from exc

    if mode == "single":
        _run_single(t, seed)
    elif mode == "montecarlo":
        _run_montecarlo(t, n, seed)
    else:
        console.print(f"[red]Unknown mode '{mode}'. Use 'single' or 'montecarlo'.[/]")
        raise typer.Exit(1)


def _run_single(t: Tournament, seed: int | None) -> None:
    result = simulate_tournament(t, np.random.default_rng(seed))

    console.rule("[bold]Group stage")
    for g in sorted(result.group_tables):
        console.print(_group_table(t, result.group_tables[g]))

    thirds = ", ".join(_name(t, c) for c in result.qualified_thirds)
    console.print(Panel(thirds, title="Best 8 third-placed teams (qualified)", style="yellow"))

    console.rule("[bold]Knockout")
    for rnd in KNOCKOUT_ROUNDS:
        matches = sorted(
            (r for r in result.ko_results.values() if r.stage == rnd),
            key=lambda r: r.match_no or 0,
        )
        if matches:
            console.print(f"\n[bold magenta]{ROUND_NAMES[rnd]}[/]")
            console.print(_knockout_table(t, matches))

    _print_champion(t, result)


def _print_champion(t: Tournament, result: TournamentResult) -> None:
    console.print(
        Panel.fit(
            f"[bold yellow]🏆  {_name(t, result.champion).upper()}  🏆[/]\n"
            f"[dim]Runner-up:[/] {_name(t, result.runner_up)}    "
            f"[dim]3rd:[/] {_name(t, result.third_place)}    "
            f"[dim]4th:[/] {_name(t, result.fourth_place)}",
            title="WORLD CHAMPION",
            border_style="yellow",
        )
    )


def _run_montecarlo(t: Tournament, n: int, seed: int | None) -> None:
    console.print(f"Running {n:,} simulations…")
    with console.status("Simulating…"):
        agg = run_montecarlo(t, n, seed=seed)

    table = Table(title=f"Probabilities over {agg.runs:,} simulations", box=box.SIMPLE_HEAVY)
    table.add_column("Team")
    for label, _key in PROB_COLUMNS:
        table.add_column(label, justify="right")
    for row in agg.probabilities()[:20]:
        table.add_row(_name(t, row["team"]), *(_pct(row[key]) for _label, key in PROB_COLUMNS))
    console.print(table)


@app.command()
def serve(
    host: str = typer.Option("127.0.0.1", help="Bind host."),
    port: int = typer.Option(8000, help="Bind port."),
) -> None:
    """Start the FastAPI backend (REST + WebSocket)."""
    import uvicorn

    uvicorn.run("wm2026.api:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    app()
