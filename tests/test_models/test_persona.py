"""Tests for the Persona Pydantic model."""

import pytest
from pydantic import ValidationError

from evercurrent.models.persona import (
    DigestPreferences,
    Persona,
    RoleArchetype,
    ScoringWeights,
)


class TestScoringWeights:
    """Tests for ScoringWeights model and weight validation."""

    def test_valid_weights_sum_to_one(self) -> None:
        """Verify valid weights construct and sum to 1.0."""
        weights = ScoringWeights(
            workstream_proximity=0.30,
            role_type_alignment=0.20,
            phase_alignment=0.20,
            urgency=0.15,
            social_signal=0.15,
        )
        total = (
            weights.workstream_proximity
            + weights.role_type_alignment
            + weights.phase_alignment
            + weights.urgency
            + weights.social_signal
        )
        assert abs(total - 1.0) < 1e-9

    def test_weights_reject_negative(self) -> None:
        """Verify ScoringWeights rejects negative weight values."""
        with pytest.raises(ValidationError):
            ScoringWeights(
                workstream_proximity=-0.1,
                role_type_alignment=0.30,
                phase_alignment=0.30,
                urgency=0.25,
                social_signal=0.25,
            )


class TestDigestPreferences:
    """Tests for DigestPreferences model."""

    def test_default_values(self) -> None:
        """Verify DigestPreferences defaults match design spec."""
        prefs = DigestPreferences()
        assert prefs.max_items == 25
        assert prefs.critical_threshold == 0.85
        assert prefs.include_broader_context is True

    def test_custom_values(self) -> None:
        """Verify DigestPreferences accepts custom overrides."""
        prefs = DigestPreferences(
            max_items=10,
            critical_threshold=0.90,
            include_broader_context=False,
        )
        assert prefs.max_items == 10
        assert prefs.critical_threshold == 0.90
        assert prefs.include_broader_context is False


class TestRoleArchetype:
    """Tests for RoleArchetype literal values."""

    def test_expected_archetypes(self) -> None:
        """Verify all 5 role archetypes from the scoring matrix exist."""
        expected = {
            "IC Engineer",
            "Eng Manager",
            "Program Manager",
            "Supply Chain",
            "Executive",
        }
        assert set(RoleArchetype.__args__) == expected


class TestPersona:
    """Tests for the top-level Persona model."""

    @pytest.fixture
    def valid_persona_data(self) -> dict:
        """Return a complete valid persona data dict for test reuse."""
        return {
            "user_id": "U02ABCDEF",
            "name": "Maya Chen",
            "role_archetype": "IC Engineer",
            "title": "Senior Mechanical Engineer",
            "workstream_affinities": {
                "chassis": 1.0,
                "thermal": 0.85,
                "drivetrain": 0.4,
            },
            "phase_context": {
                "chassis": "DVT",
                "thermal": "EVT",
            },
            "scoring_weights": {
                "workstream_proximity": 0.30,
                "role_type_alignment": 0.20,
                "phase_alignment": 0.20,
                "urgency": 0.15,
                "social_signal": 0.15,
            },
            "collaborator_graph": ["U03XYZABC", "U04QRSTUV"],
            "digest_preferences": {
                "max_items": 25,
                "critical_threshold": 0.85,
                "include_broader_context": True,
            },
        }

    def test_valid_persona_round_trips(self, valid_persona_data: dict) -> None:
        """Verify a valid Persona round-trips all fields correctly."""
        persona = Persona(**valid_persona_data)
        assert persona.user_id == "U02ABCDEF"
        assert persona.name == "Maya Chen"
        assert persona.role_archetype == "IC Engineer"
        assert persona.workstream_affinities["chassis"] == 1.0
        assert persona.phase_context["chassis"] == "DVT"
        assert persona.scoring_weights.workstream_proximity == 0.30
        assert persona.collaborator_graph == ["U03XYZABC", "U04QRSTUV"]
        assert persona.digest_preferences.max_items == 25

    def test_persona_rejects_invalid_archetype(self, valid_persona_data: dict) -> None:
        """Verify Persona rejects a role archetype not in allowed set."""
        valid_persona_data["role_archetype"] = "Janitor"
        with pytest.raises(ValidationError):
            Persona(**valid_persona_data)

    def test_persona_default_collaborators_empty(self, valid_persona_data: dict) -> None:
        """Verify collaborator_graph defaults to empty list."""
        del valid_persona_data["collaborator_graph"]
        persona = Persona(**valid_persona_data)
        assert persona.collaborator_graph == []

    def test_persona_default_digest_preferences(self, valid_persona_data: dict) -> None:
        """Verify digest_preferences defaults to spec values."""
        del valid_persona_data["digest_preferences"]
        persona = Persona(**valid_persona_data)
        assert persona.digest_preferences.max_items == 25

    def test_persona_serialization(self, valid_persona_data: dict) -> None:
        """Verify model_dump preserves nested scoring weights."""
        persona = Persona(**valid_persona_data)
        data = persona.model_dump()
        assert data["user_id"] == "U02ABCDEF"
        assert data["scoring_weights"]["urgency"] == 0.15
