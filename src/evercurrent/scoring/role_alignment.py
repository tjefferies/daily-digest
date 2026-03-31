"""Dimension 2: role-type alignment matrix (weight 0.20).

Scores how well an atom type aligns with the persona's role archetype.
Engineers care most about SPEC_CHANGE and TEST_RESULT; managers about
BLOCKER and STATUS_UPDATE; supply chain about RISK and ACTION_ITEM.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from evercurrent.models.atom import Atom
    from evercurrent.models.persona import Persona

_ALIGNMENT_MATRIX: dict[str, dict[str, float]] = {
    "IC Engineer": {
        "DECISION": 0.8,
        "SPEC_CHANGE": 1.0,
        "ACTION_ITEM": 0.7,
        "BLOCKER": 0.6,
        "RISK": 0.5,
        "TEST_RESULT": 1.0,
        "STATUS_UPDATE": 0.3,
        "QUESTION": 0.6,
    },
    "Eng Manager": {
        "DECISION": 1.0,
        "SPEC_CHANGE": 0.7,
        "ACTION_ITEM": 0.8,
        "BLOCKER": 1.0,
        "RISK": 0.9,
        "TEST_RESULT": 0.6,
        "STATUS_UPDATE": 0.9,
        "QUESTION": 0.5,
    },
    "Program Manager": {
        "DECISION": 0.9,
        "SPEC_CHANGE": 0.5,
        "ACTION_ITEM": 0.9,
        "BLOCKER": 1.0,
        "RISK": 1.0,
        "TEST_RESULT": 0.4,
        "STATUS_UPDATE": 1.0,
        "QUESTION": 0.3,
    },
    "Supply Chain": {
        "DECISION": 0.7,
        "SPEC_CHANGE": 0.9,
        "ACTION_ITEM": 0.8,
        "BLOCKER": 0.7,
        "RISK": 1.0,
        "TEST_RESULT": 0.3,
        "STATUS_UPDATE": 0.5,
        "QUESTION": 0.4,
    },
    "Executive": {
        "DECISION": 1.0,
        "SPEC_CHANGE": 0.4,
        "ACTION_ITEM": 0.5,
        "BLOCKER": 1.0,
        "RISK": 1.0,
        "TEST_RESULT": 0.3,
        "STATUS_UPDATE": 0.8,
        "QUESTION": 0.2,
    },
}


def score_role_alignment(atom: Atom, persona: Persona) -> float:
    """Score atom-persona role-type alignment.

    Args:
        atom: The atom to score.
        persona: The persona to score against.

    Returns:
        Float in [0, 1] from the alignment matrix.
    """
    role_scores = _ALIGNMENT_MATRIX.get(persona.role_archetype, {})
    return role_scores.get(atom.type, 0.5)
