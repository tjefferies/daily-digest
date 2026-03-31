"""Dimension 3: phase alignment matrix (weight 0.20).

Scores how relevant an atom's phase_relevance is to the persona's
current workstream phases. An EVT-phase atom scores highest for
personas working in EVT workstreams.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from evercurrent.config.loader import get_config

if TYPE_CHECKING:
    from evercurrent.models.atom import Atom
    from evercurrent.models.persona import Persona

_pa_cfg = get_config()["scoring"]["phase_alignment"]
_NO_PHASE_RELEVANCE: float = _pa_cfg["no_phase_relevance"]
_NO_PERSONA_PHASES: float = _pa_cfg["no_persona_phases"]
_OVERLAP: float = _pa_cfg["overlap"]
_NO_OVERLAP: float = _pa_cfg["no_overlap"]


def score_phase_alignment(atom: Atom, persona: Persona) -> float:
    """Score atom-persona phase alignment.

    Score = max overlap between atom's phase_relevance and persona's
    phase_context values. If any workstream the persona works in
    matches a phase the atom is relevant to, that's a hit.

    Args:
        atom: The atom to score.
        persona: The persona to score against.

    Returns:
        Float in [0, 1]. 1.0 if any persona phase matches atom phases.
        0.3 default for atoms with no phase_relevance (always somewhat relevant).
    """
    if not atom.phase_relevance:
        return _NO_PHASE_RELEVANCE

    atom_phases = set(atom.phase_relevance)
    persona_phases = set(persona.phase_context.values())

    if not persona_phases:
        return _NO_PERSONA_PHASES

    overlap = atom_phases & persona_phases
    if overlap:
        return _OVERLAP

    return _NO_OVERLAP
