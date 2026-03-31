"""Layer 4: Relevance Scoring — five-dimension scoring pipeline.

Scores atoms against personas using workstream proximity, role-type
alignment, phase alignment, urgency, and social signals.
"""

from evercurrent.scoring.phase_alignment import score_phase_alignment
from evercurrent.scoring.role_alignment import score_role_alignment
from evercurrent.scoring.social_signal import score_social_signal
from evercurrent.scoring.urgency import score_urgency
from evercurrent.scoring.workstream_proximity import score_workstream_proximity

__all__ = [
    "score_phase_alignment",
    "score_role_alignment",
    "score_social_signal",
    "score_urgency",
    "score_workstream_proximity",
]
