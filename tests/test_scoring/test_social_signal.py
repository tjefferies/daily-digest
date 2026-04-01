"""Tests for Dimension 5: social signal scoring."""

from __future__ import annotations

from uuid import uuid4

from digest.models.atom import Atom, AtomSource, AtomWorkstreams
from digest.models.persona import Persona, ScoringWeights
from digest.scoring.social_signal import score_social_signal


def _make_atom(participants: list[str] | None = None) -> Atom:
    """Create an Atom with given key participants."""
    return Atom(
        atom_id=uuid4(),
        type="DECISION",
        summary="Test",
        detail="Detail",
        source=AtomSource(
            channel="#test",
            thread_ts="1.0",
            message_range=[0, 1],
            key_participants=participants or [],
        ),
        workstreams=AtomWorkstreams(originating="chassis"),
        urgency="medium",
        confidence=0.9,
    )


def _make_persona(
    user_id: str = "U001",
    collaborators: list[str] | None = None,
) -> Persona:
    """Create a Persona with given collaborator graph."""
    return Persona(
        user_id=user_id,
        name="Test",
        role_archetype="IC Engineer",
        title="Test",
        workstream_affinities={},
        phase_context={},
        scoring_weights=ScoringWeights(
            workstream_proximity=0.30,
            role_type_alignment=0.20,
            phase_alignment=0.20,
            urgency=0.15,
            social_signal=0.15,
        ),
        collaborator_graph=collaborators or [],
    )


class TestSocialSignal:
    """Tests for social signal scoring."""

    def test_self_mention_scores_highest(self) -> None:
        """Atom where persona is a key participant scores 1.0."""
        atom = _make_atom(["U001", "U002"])
        persona = _make_persona("U001", collaborators=["U003"])
        assert score_social_signal(atom, persona) == 1.0

    def test_collaborator_scores_high(self) -> None:
        """Atom from collaborator scores 0.75."""
        atom = _make_atom(["U002"])
        persona = _make_persona("U001", collaborators=["U002", "U003"])
        assert score_social_signal(atom, persona) == 0.75

    def test_unknown_participant_scores_low(self) -> None:
        """Atom from unknown person scores 0.25."""
        atom = _make_atom(["U099"])
        persona = _make_persona("U001", collaborators=["U002"])
        assert score_social_signal(atom, persona) == 0.25

    def test_no_participants_default(self) -> None:
        """Atom with no participants gets default 0.5."""
        atom = _make_atom([])
        persona = _make_persona("U001")
        assert score_social_signal(atom, persona) == 0.5

    def test_score_in_range(self) -> None:
        """All scores are in [0, 1]."""
        for participants in [[], ["U001"], ["U002"], ["U099"]]:
            score = score_social_signal(
                _make_atom(participants),
                _make_persona("U001", collaborators=["U002"]),
            )
            assert 0.0 <= score <= 1.0
