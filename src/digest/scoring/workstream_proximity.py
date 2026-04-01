"""Dimension 1: workstream proximity scoring (weight 0.30).

Score = max(persona.workstream_affinities[ws] for ws in all atom workstreams).
Cross-workstream affected tags make this powerful - a spec change that
affects your workstream scores high even from a channel you don't follow.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from digest.models.atom import Atom
    from digest.models.persona import Persona


def score_workstream_proximity(atom: Atom, persona: Persona) -> float:
    """Score atom-persona workstream proximity.

    Args:
        atom: The atom to score.
        persona: The persona to score against.

    Returns:
        Float in [0, 1] - max affinity across originating + affected.
    """
    workstreams = [atom.workstreams.originating, *atom.workstreams.affected]
    affinities = persona.workstream_affinities
    scores = [affinities.get(ws, 0.0) for ws in workstreams]
    return max(scores) if scores else 0.0
