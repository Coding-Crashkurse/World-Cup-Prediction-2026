"""Group fixtures, standings and FIFA tiebreakers (Spec §2, fummelige Stelle 1).

Tiebreaker order (official 2026 regulations, overall criteria first):

1. points (all group matches)
2. goal difference (all)
3. goals scored (all)
4. head-to-head points (among the teams still level)
5. head-to-head goal difference
6. head-to-head goals scored
7. fair-play / conduct  — not modelled (no card data); skipped
8. drawing of lots      — random, seeded (or FIFA-ranking proxy if configured)

The standard interpretation is applied: head-to-head (4-6) is computed among the
*set* of teams tied on the overall criteria; any still-level subset then goes to
lots. Third-placed teams are ranked by the overall criteria only (they share no
fixtures), then lots.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable

import numpy as np

from .loader import SimConfig
from .types import GroupRow, MatchResult, Team

# Round-robin schedule for a 4-team group, as (matchday, home_index, away_index).
_GROUP_FIXTURES = [
    (1, 0, 1),
    (1, 2, 3),
    (2, 0, 2),
    (2, 3, 1),
    (3, 0, 3),
    (3, 1, 2),
]

RawMatch = tuple[str, str, int, int]  # home, away, home_goals, away_goals


def group_fixtures(codes: list[str]) -> list[tuple[int, str, str]]:
    """Six fixtures (matchday, home, away) covering each pairing once."""
    return [(md, codes[h], codes[a]) for md, h, a in _GROUP_FIXTURES]


def compute_rows(codes: Iterable[str], results: list[MatchResult]) -> dict[str, GroupRow]:
    """Tally a group table from its played matches."""
    rows = {c: GroupRow(c) for c in codes}
    for r in results:
        if r.home not in rows or r.away not in rows:
            continue
        h, a = rows[r.home], rows[r.away]
        h.played += 1
        a.played += 1
        h.gf += r.home_goals
        h.ga += r.away_goals
        a.gf += r.away_goals
        a.ga += r.home_goals
        if r.home_goals > r.away_goals:
            h.win += 1
            a.loss += 1
        elif r.home_goals < r.away_goals:
            a.win += 1
            h.loss += 1
        else:
            h.draw += 1
            a.draw += 1
    return rows


def _sort_and_group(subset: list[str], keyfn: Callable[[str], tuple]) -> list[list[str]]:
    """Order desc by keyfn and split into blocks sharing the same key."""
    ordered = sorted(subset, key=keyfn, reverse=True)
    blocks: list[list[str]] = []
    last_key = None
    for c in ordered:
        k = keyfn(c)
        if blocks and k == last_key:
            blocks[-1].append(c)
        else:
            blocks.append([c])
            last_key = k
    return blocks


def _h2h_keys(block: list[str], matches: list[RawMatch]) -> dict[str, tuple[int, int, int]]:
    """Head-to-head (pts, gd, gf) using only matches among `block`."""
    bs = set(block)
    pts = dict.fromkeys(block, 0)
    gf = dict.fromkeys(block, 0)
    ga = dict.fromkeys(block, 0)
    for h, a, hg, ag in matches:
        if h in bs and a in bs:
            gf[h] += hg
            ga[h] += ag
            gf[a] += ag
            ga[a] += hg
            if hg > ag:
                pts[h] += 3
            elif hg < ag:
                pts[a] += 3
            else:
                pts[h] += 1
                pts[a] += 1
    return {c: (pts[c], gf[c] - ga[c], gf[c]) for c in block}


def _resolve_final(
    block: list[str], rng: np.random.Generator, cfg: SimConfig, team_elo: dict[str, float]
) -> list[str]:
    """Criteria 7-8: fair-play (skipped) then lots / FIFA-ranking proxy."""
    if cfg.final_tiebreaker == "fifa":
        # Deterministic Elo order; randomise only exact Elo ties.
        jitter = {c: rng.random() for c in block}
        return sorted(block, key=lambda c: (team_elo.get(c, 1500.0), jitter[c]), reverse=True)
    order = list(block)
    rng.shuffle(order)  # drawing of lots
    return order


def rank_group(
    codes: list[str],
    results: list[MatchResult],
    rng: np.random.Generator,
    cfg: SimConfig,
    team_elo: dict[str, float],
) -> list[GroupRow]:
    """Return the four group rows ordered best-first per the tiebreakers."""
    rows = compute_rows(codes, results)
    matches: list[RawMatch] = [(r.home, r.away, r.home_goals, r.away_goals) for r in results]

    def overall_key(c: str) -> tuple[int, int, int]:
        r = rows[c]
        return (r.pts, r.gd, r.gf)

    ordered: list[str] = []
    for block in _sort_and_group(list(codes), overall_key):
        if len(block) == 1:
            ordered.append(block[0])
            continue
        # Tied on overall criteria -> head-to-head among this block.
        h2h = _h2h_keys(block, matches)
        for sub in _sort_and_group(block, lambda c, _h2h=h2h: _h2h[c]):
            if len(sub) == 1:
                ordered.append(sub[0])
            else:
                ordered.extend(_resolve_final(sub, rng, cfg, team_elo))
    return [rows[c] for c in ordered]


def rank_thirds(
    third_rows: dict[str, GroupRow],
    rng: np.random.Generator,
    cfg: SimConfig,
    team_elo: dict[str, float],
) -> list[str]:
    """Rank the twelve third-placed teams best-first (overall criteria + lots)."""

    def key(c: str) -> tuple[int, int, int]:
        r = third_rows[c]
        return (r.pts, r.gd, r.gf)

    ordered: list[str] = []
    for block in _sort_and_group(list(third_rows), key):
        if len(block) == 1:
            ordered.append(block[0])
        else:
            ordered.extend(_resolve_final(block, rng, cfg, team_elo))
    return ordered


def teams_elo(teams: dict[str, Team]) -> dict[str, float]:
    return {c: t.elo for c, t in teams.items()}
