"""Tests for the Atom Pydantic model."""

from uuid import UUID

import pytest
from pydantic import ValidationError

from evercurrent.models.atom import Atom, AtomSource, AtomType, AtomWorkstreams


class TestAtomType:
    """Tests for AtomType literal/enum values."""

    def test_all_eight_types_exist(self) -> None:
        """Verify all 8 atom type literals are defined."""
        expected = {
            "DECISION",
            "SPEC_CHANGE",
            "ACTION_ITEM",
            "BLOCKER",
            "RISK",
            "TEST_RESULT",
            "STATUS_UPDATE",
            "QUESTION",
        }
        assert set(AtomType.__args__) == expected


class TestAtomSource:
    """Tests for the AtomSource embedded model."""

    def test_valid_source(self) -> None:
        """Verify a valid AtomSource round-trips all fields."""
        source = AtomSource(
            channel="#drivetrain",
            thread_ts="1234567890.123456",
            message_range=[3, 47],
            key_participants=["@alex", "@priya"],
        )
        assert source.channel == "#drivetrain"
        assert source.thread_ts == "1234567890.123456"
        assert source.message_range == [3, 47]
        assert source.key_participants == ["@alex", "@priya"]

    def test_source_requires_channel(self) -> None:
        """Verify AtomSource rejects missing channel field."""
        with pytest.raises(ValidationError):
            AtomSource(
                thread_ts="1234567890.123456",
                message_range=[3, 47],
                key_participants=["@alex"],
            )


class TestAtomWorkstreams:
    """Tests for the AtomWorkstreams embedded model."""

    def test_valid_workstreams(self) -> None:
        """Verify a valid AtomWorkstreams round-trips all fields."""
        ws = AtomWorkstreams(
            originating="drivetrain",
            affected=["power-systems", "supply-chain", "thermal"],
        )
        assert ws.originating == "drivetrain"
        assert ws.affected == ["power-systems", "supply-chain", "thermal"]

    def test_workstreams_affected_defaults_empty(self) -> None:
        """Verify affected workstreams defaults to empty list."""
        ws = AtomWorkstreams(originating="chassis")
        assert ws.affected == []


class TestAtom:
    """Tests for the top-level Atom model."""

    @pytest.fixture
    def valid_atom_data(self) -> dict:
        """Return a complete valid atom data dict for test reuse."""
        return {
            "atom_id": "550e8400-e29b-41d4-a716-446655440000",
            "type": "SPEC_CHANGE",
            "summary": "Motor torque requirement increased from 2.5 Nm to 3.1 Nm",
            "detail": "Based on load testing results showing higher-than-expected friction...",
            "source": {
                "channel": "#drivetrain",
                "thread_ts": "1234567890.123456",
                "message_range": [3, 47],
                "key_participants": ["@alex", "@priya"],
            },
            "workstreams": {
                "originating": "drivetrain",
                "affected": ["power-systems", "supply-chain", "thermal"],
            },
            "urgency": "high",
            "confidence": 0.92,
            "implicit_decision": False,
            "phase_relevance": ["EVT", "DVT"],
        }

    def test_valid_atom_round_trips(self, valid_atom_data: dict) -> None:
        """Verify a valid Atom round-trips key fields correctly."""
        atom = Atom(**valid_atom_data)
        assert atom.type == "SPEC_CHANGE"
        assert atom.confidence == 0.92
        assert isinstance(atom.atom_id, UUID)
        assert atom.urgency == "high"
        assert atom.phase_relevance == ["EVT", "DVT"]

    def test_atom_rejects_invalid_type(self, valid_atom_data: dict) -> None:
        """Verify Atom rejects a type not in the 8 allowed literals."""
        valid_atom_data["type"] = "INVALID_TYPE"
        with pytest.raises(ValidationError):
            Atom(**valid_atom_data)

    def test_atom_rejects_confidence_out_of_range(self, valid_atom_data: dict) -> None:
        """Verify Atom rejects confidence > 1.0."""
        valid_atom_data["confidence"] = 1.5
        with pytest.raises(ValidationError):
            Atom(**valid_atom_data)

    def test_atom_rejects_negative_confidence(self, valid_atom_data: dict) -> None:
        """Verify Atom rejects confidence < 0.0."""
        valid_atom_data["confidence"] = -0.1
        with pytest.raises(ValidationError):
            Atom(**valid_atom_data)

    def test_atom_all_eight_types_accepted(self, valid_atom_data: dict) -> None:
        """Verify all 8 AtomType literals are accepted by the model."""
        for atom_type in AtomType.__args__:
            valid_atom_data["type"] = atom_type
            atom = Atom(**valid_atom_data)
            assert atom.type == atom_type

    def test_atom_urgency_values(self, valid_atom_data: dict) -> None:
        """Verify all 4 urgency levels are accepted."""
        for urgency in ("low", "medium", "high", "critical"):
            valid_atom_data["urgency"] = urgency
            atom = Atom(**valid_atom_data)
            assert atom.urgency == urgency

    def test_atom_rejects_invalid_urgency(self, valid_atom_data: dict) -> None:
        """Verify Atom rejects an urgency value not in the allowed set."""
        valid_atom_data["urgency"] = "EXTREME"
        with pytest.raises(ValidationError):
            Atom(**valid_atom_data)

    def test_atom_serialization(self, valid_atom_data: dict) -> None:
        """Verify model_dump preserves nested structure."""
        atom = Atom(**valid_atom_data)
        data = atom.model_dump()
        assert data["type"] == "SPEC_CHANGE"
        assert data["source"]["channel"] == "#drivetrain"
        assert data["workstreams"]["originating"] == "drivetrain"
