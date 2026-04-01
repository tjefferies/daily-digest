"""Dimension 5: social signal scoring via collaborator graph (weight 0.15).

Scores how connected the atom's key participants are to the persona.
If a close collaborator produced the atom, it scores higher.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from digest.config.loader import get_config

if TYPE_CHECKING:
    from digest.models.atom import Atom
    from digest.models.persona import Persona

_ss_cfg = get_config()["scoring"]["social_signal"]
_NO_PARTICIPANTS: float = _ss_cfg["no_participants"]
_PERSONA_IS_PARTICIPANT: float = _ss_cfg["persona_is_participant"]
_COLLABORATOR_OVERLAP: float = _ss_cfg["collaborator_overlap"]
_UNKNOWN_PARTICIPANTS: float = _ss_cfg["unknown_participants"]


def score_social_signal(atom: Atom, persona: Persona) -> float:
    """Score atom-persona social signal.

    Args:
        atom: The atom to score.
        persona: The persona to score against.

    Returns:
        Float in [0, 1]. 1.0 if any key participant is a collaborator.
        0.3 baseline for unknown participants.
    """
    if not atom.source.key_participants:
        return _NO_PARTICIPANTS

    collaborators = set(persona.collaborator_graph)
    participants = set(atom.source.key_participants)

    if persona.user_id in participants:
        return _PERSONA_IS_PARTICIPANT

    overlap = collaborators & participants
    if overlap:
        return _COLLABORATOR_OVERLAP

    return _UNKNOWN_PARTICIPANTS
