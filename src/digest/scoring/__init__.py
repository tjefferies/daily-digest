"""Layer 4: Relevance Scoring - five-dimension scoring pipeline.

Scores atoms against personas using workstream proximity, role-type
alignment, phase alignment, urgency, and social signals. Assembles
composite scores, ranks atoms, and flags critical items.
"""

from digest.scoring.composite import ScoreBreakdown, ScoredAtom, score_atoms
from digest.scoring.phase_alignment import score_phase_alignment
from digest.scoring.role_alignment import score_role_alignment
from digest.scoring.social_signal import score_social_signal
from digest.scoring.urgency import score_urgency
from digest.scoring.workstream_proximity import score_workstream_proximity

__all__ = [
    "ScoreBreakdown",
    "ScoredAtom",
    "score_atoms",
    "score_phase_alignment",
    "score_role_alignment",
    "score_social_signal",
    "score_urgency",
    "score_workstream_proximity",
]
