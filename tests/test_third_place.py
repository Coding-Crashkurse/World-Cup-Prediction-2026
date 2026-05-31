"""Third-place matrix (Spec §2): official table validity + solver fallback."""

from __future__ import annotations

import itertools
import json

from wm2026.paths import THIRD_PLACE_MATRIX_FILE
from wm2026.tournament.third_place import _solve_assignment, assign_thirds

MATRIX = json.loads(THIRD_PLACE_MATRIX_FILE.read_text(encoding="utf-8"))
SLOT_CANDIDATES = MATRIX["_meta"]["slotCandidates"]
SLOTS = set(MATRIX["_meta"]["slotOrder"])


def test_matrix_has_all_495_combinations():
    assert len(MATRIX["lookup"]) == 495  # C(12, 8)


def test_every_official_assignment_is_a_valid_bijection():
    for combo, assignment in MATRIX["lookup"].items():
        qualifying = set(combo)
        # Each of the 8 winner slots is filled exactly once.
        assert set(assignment) == SLOTS
        # The assigned thirds are exactly the 8 qualifying groups (a bijection).
        assert set(assignment.values()) == qualifying
        # Each third respects its slot's candidate constraint.
        for slot, third in assignment.items():
            assert third in SLOT_CANDIDATES[slot], f"{combo}: {third} not allowed in slot {slot}"


def test_solver_fallback_produces_valid_assignments():
    # The solver should always yield a constraint-respecting bijection, even
    # though it need not match FIFA's specific published choice.
    sample = list(itertools.islice(itertools.combinations("ABCDEFGHIJKL", 8), 0, 495, 37))
    for groups in sample:
        qualifying = set(groups)
        assignment = _solve_assignment(qualifying, SLOT_CANDIDATES)
        assert set(assignment) == SLOTS
        assert set(assignment.values()) == qualifying
        for slot, third in assignment.items():
            assert third in SLOT_CANDIDATES[slot]


def test_assign_thirds_prefers_official_lookup():
    combo = "EFGHIJKL"
    assert assign_thirds(set(combo), MATRIX) == MATRIX["lookup"][combo]
