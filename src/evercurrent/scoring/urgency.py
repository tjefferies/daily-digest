"""Dimension 4: urgency pass-through scoring (weight 0.15).

Maps atom urgency directly to a score. Critical items always surface;
low items get lower base scores.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from evercurrent.models.atom import Atom

_URGENCY_SCORES: dict[str, float] = {
    "critical": 1.0,
    "high": 0.8,
    "medium": 0.5,
    "low": 0.2,
}


def score_urgency(atom: Atom) -> float:
    """Score atom urgency.

    Args:
        atom: The atom to score.

    Returns:
        Float in [0, 1] based on urgency level.
    """
    return _URGENCY_SCORES.get(atom.urgency, 0.5)
