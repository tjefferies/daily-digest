"""Dimension 4: urgency pass-through scoring.

Maps atom urgency level to a configured score via lookup table.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from digest.config.loader import get_config

if TYPE_CHECKING:
    from digest.models.atom import Atom

_URGENCY_SCORES: dict[str, float] = get_config()["scoring"]["urgency_scores"]


def score_urgency(atom: Atom) -> float:
    """Score atom urgency.

    Args:
        atom: The atom to score.

    Returns:
        Float in [0, 1] based on urgency level.
    """
    return _URGENCY_SCORES.get(atom.urgency, 0.5)
