"""Dimension 2: role-type alignment matrix (weight 0.20).

Scores how well an atom type aligns with the persona's role archetype.
Engineers care most about SPEC_CHANGE and TEST_RESULT; managers about
BLOCKER and STATUS_UPDATE; supply chain about RISK and ACTION_ITEM.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from digest.config.loader import get_config

if TYPE_CHECKING:
    from digest.models.atom import Atom
    from digest.models.persona import Persona

_scoring_cfg = get_config()["scoring"]
_ALIGNMENT_MATRIX: dict[str, dict[str, float]] = _scoring_cfg["role_type_alignment"]
_DEFAULT_SCORE: float = _scoring_cfg["role_type_default"]


def score_role_alignment(atom: Atom, persona: Persona) -> float:
    """Score atom-persona role-type alignment.

    Args:
        atom: The atom to score.
        persona: The persona to score against.

    Returns:
        Float in [0, 1] from the alignment matrix.
    """
    role_scores = _ALIGNMENT_MATRIX.get(persona.role_archetype, {})
    return role_scores.get(atom.type, _DEFAULT_SCORE)
