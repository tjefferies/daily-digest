"""Composite scoring: weighted sum, ranking, and critical threshold.

Assembles the five scoring dimensions into a single composite relevance
score per (atom, persona) pair. Atoms are ranked descending by score,
capped at max_items, and flagged critical if above the persona's threshold.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from digest.scoring.phase_alignment import score_phase_alignment
from digest.scoring.role_alignment import score_role_alignment
from digest.scoring.social_signal import score_social_signal
from digest.scoring.urgency import score_urgency
from digest.scoring.workstream_proximity import score_workstream_proximity

if TYPE_CHECKING:
    from digest.models.atom import Atom
    from digest.models.persona import Persona


@dataclass(frozen=True)
class ScoreBreakdown:
    """Per-dimension score breakdown for transparency.

    Attributes:
        workstream_proximity: Dimension 1 score.
        role_type_alignment: Dimension 2 score.
        phase_alignment: Dimension 3 score.
        urgency: Dimension 4 score.
        social_signal: Dimension 5 score.
    """

    workstream_proximity: float
    role_type_alignment: float
    phase_alignment: float
    urgency: float
    social_signal: float


@dataclass(frozen=True)
class ScoredAtom:
    """An atom with its composite relevance score and breakdown.

    Attributes:
        atom: The original atom.
        score: Composite relevance score in [0, 1].
        breakdown: Per-dimension scores.
        critical: Whether this atom exceeds the critical threshold.
    """

    atom: Atom
    score: float
    breakdown: ScoreBreakdown
    critical: bool


def _score_one(atom: Atom, persona: Persona, threshold: float) -> ScoredAtom:
    """Compute composite score for a single atom-persona pair.

    Args:
        atom: The atom to score.
        persona: The persona to score against.
        threshold: Critical threshold for flagging.

    Returns:
        ScoredAtom with composite score, breakdown, and critical flag.
    """
    w = persona.scoring_weights
    breakdown = ScoreBreakdown(
        workstream_proximity=score_workstream_proximity(atom, persona),
        role_type_alignment=score_role_alignment(atom, persona),
        phase_alignment=score_phase_alignment(atom, persona),
        urgency=score_urgency(atom),
        social_signal=score_social_signal(atom, persona),
    )
    composite = (
        w.workstream_proximity * breakdown.workstream_proximity
        + w.role_type_alignment * breakdown.role_type_alignment
        + w.phase_alignment * breakdown.phase_alignment
        + w.urgency * breakdown.urgency
        + w.social_signal * breakdown.social_signal
    )
    return ScoredAtom(
        atom=atom,
        score=composite,
        breakdown=breakdown,
        critical=composite >= threshold,
    )


def score_atoms(atoms: list[Atom], persona: Persona) -> list[ScoredAtom]:
    """Score, rank, and threshold-filter atoms for a persona.

    Computes composite relevance = sum(weight_i * dim_i_score) for each
    atom, ranks descending, caps at max_items, and flags critical atoms.
    Critical atoms are always included even if they would be beyond top N.

    Args:
        atoms: List of atoms to score.
        persona: The persona whose relevance perspective to apply.

    Returns:
        List of ScoredAtom sorted by score descending, at most max_items
        plus any additional critical atoms beyond that limit.
    """
    if not atoms:
        return []

    prefs = persona.digest_preferences
    threshold = prefs.critical_threshold
    max_items = prefs.max_items

    scored = [_score_one(atom, persona, threshold) for atom in atoms]
    scored.sort(key=lambda s: s.score, reverse=True)

    top_n = scored[:max_items]
    # Include critical atoms that fell outside top N
    top_ids = {id(s) for s in top_n}
    overflow_critical = [s for s in scored[max_items:] if s.critical]
    return [*top_n, *[s for s in overflow_critical if id(s) not in top_ids]]
