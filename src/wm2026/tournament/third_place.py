"""Assign qualifying third-placed teams to R32 slots (Spec §2, fummelige Stelle 2).

Primary path: the official 495-row FIFA combination table (loaded from
``third_place_matrix.json``), keyed by which 8 of the 12 groups supplied a
qualifying third. Fallback: a constraint-respecting bipartite matching against
each slot's published candidate-group set, so any combination still yields a
structurally valid bracket.
"""

from __future__ import annotations


def _solve_assignment(
    qualifying_groups: set[str], slot_candidates: dict[str, list[str]]
) -> dict[str, str]:
    """Bipartite matching: winner-slot group -> qualifying third's group.

    Uses Kuhn's augmenting-path algorithm (the graph is tiny, 8x8). Raises if no
    perfect matching exists (should be impossible for a valid combination).
    """
    slots = list(slot_candidates)
    quals = set(qualifying_groups)
    adj = {s: [g for g in slot_candidates[s] if g in quals] for s in slots}

    group_to_slot: dict[str, str] = {}

    def augment(slot: str, visited: set[str]) -> bool:
        for g in adj[slot]:
            if g in visited:
                continue
            visited.add(g)
            if g not in group_to_slot or augment(group_to_slot[g], visited):
                group_to_slot[g] = slot
                return True
        return False

    for s in slots:
        augment(s, set())

    if len(group_to_slot) != len(slots):
        raise ValueError(
            f"No valid third-place assignment for groups {sorted(quals)} "
            f"(matched {len(group_to_slot)}/{len(slots)})."
        )
    return {slot: group for group, slot in group_to_slot.items()}


def assign_thirds(qualifying_groups: set[str], third_matrix: dict) -> dict[str, str]:
    """Return {winner-slot group -> qualifying third's group} for these 8 groups."""
    combo = "".join(sorted(qualifying_groups))
    lookup = third_matrix.get("lookup", {})
    if combo in lookup:
        return dict(lookup[combo])
    slot_candidates = third_matrix["_meta"]["slotCandidates"]
    return _solve_assignment(qualifying_groups, slot_candidates)
