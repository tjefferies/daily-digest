"""Dimension 3: phase alignment via graduated distance scoring (weight 0.20).

Scores how close an atom's phase_relevance is to the persona's
current workstream phases. Uses phase distance (Concept → EVT →
DVT → PVT → MP) to produce graduated scores instead of binary
overlap/no-overlap, ensuring proportional weight influence.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from digest.config.loader import get_config

if TYPE_CHECKING:
    from digest.models.atom import Atom
    from digest.models.persona import Persona

_pa_cfg = get_config()["scoring"]["phase_alignment"]
_NO_PHASE_RELEVANCE: float = _pa_cfg["no_phase_relevance"]
_NO_PERSONA_PHASES: float = _pa_cfg["no_persona_phases"]
_DISTANCE_SCORES: dict[int, float] = {int(k): v for k, v in _pa_cfg["distance_scores"].items()}

# Phase ordering for distance calculation.
_PHASE_ORDER: dict[str, int] = {
    "Concept": 0,
    "EVT": 1,
    "DVT": 2,
    "PVT": 3,
    "MP": 4,
}

_MAX_DISTANCE = max(_DISTANCE_SCORES.keys())


def _phase_distance(phase_a: str, phase_b: str) -> int:
    """Compute distance between two phases in the phase order.

    Args:
        phase_a: First phase name.
        phase_b: Second phase name.

    Returns:
        Integer distance (0 = same, 4 = max). Unknown phases return max.
    """
    idx_a = _PHASE_ORDER.get(phase_a)
    idx_b = _PHASE_ORDER.get(phase_b)
    if idx_a is None or idx_b is None:
        return _MAX_DISTANCE
    return abs(idx_a - idx_b)


def score_phase_alignment(atom: Atom, persona: Persona) -> float:
    """Score atom-persona phase alignment using graduated distance.

    Computes the minimum phase distance between the atom's phase_relevance
    and the persona's phase_context values, then maps distance to a score
    via the configured distance_scores lookup.

    Args:
        atom: The atom to score.
        persona: The persona to score against.

    Returns:
        Float in [0, 1]. 1.0 for exact match, decreasing with distance.
    """
    if not atom.phase_relevance:
        return _NO_PHASE_RELEVANCE

    persona_phases = list(persona.phase_context.values())
    if not persona_phases:
        return _NO_PERSONA_PHASES

    min_dist = min(_phase_distance(ap, pp) for ap in atom.phase_relevance for pp in persona_phases)
    return _DISTANCE_SCORES.get(min_dist, _DISTANCE_SCORES[_MAX_DISTANCE])
