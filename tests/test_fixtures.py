"""Tests for the in-memory fixture store and data loader."""

from pathlib import Path

import pytest

from digest.fixtures import (
    FixtureStore,
    load_fixtures,
)
from digest.models.persona import Persona


@pytest.fixture
def sample_fixtures_dir(tmp_path: Path) -> Path:
    """Create a temporary fixtures directory with sample JSON data."""
    import json

    messages = [
        {
            "message_ts": "1700000001.000001",
            "thread_ts": "1700000001.000001",
            "channel": "#chassis-design",
            "user_id": "U02ABCDEF",
            "text": "Uploaded rev D STEP files to shared drive",
            "reactions": [],
        },
        {
            "message_ts": "1700000002.000002",
            "thread_ts": "1700000001.000001",
            "channel": "#chassis-design",
            "user_id": "U03XYZABC",
            "text": "Thanks, reviewing now",
            "reactions": [{"name": "eyes", "count": 1}],
        },
    ]

    team_roster = [
        {
            "user_id": "U02ABCDEF",
            "name": "Maya Chen",
            "title": "Senior Mechanical Engineer",
            "role_archetype": "IC Engineer",
        },
        {
            "user_id": "U03XYZABC",
            "name": "James Park",
            "title": "Engineering Manager",
            "role_archetype": "Eng Manager",
        },
    ]

    personas = [
        {
            "user_id": "U02ABCDEF",
            "name": "Maya Chen",
            "role_archetype": "IC Engineer",
            "title": "Senior Mechanical Engineer",
            "workstream_affinities": {"chassis": 1.0, "thermal": 0.85},
            "phase_context": {"chassis": "DVT", "thermal": "EVT"},
            "scoring_weights": {
                "workstream_proximity": 0.30,
                "role_type_alignment": 0.20,
                "phase_alignment": 0.20,
                "urgency": 0.15,
                "social_signal": 0.15,
            },
            "collaborator_graph": ["U03XYZABC"],
            "digest_preferences": {
                "max_items": 25,
                "critical_threshold": 0.85,
                "include_broader_context": True,
            },
        },
    ]

    workstream_phases = {
        "chassis": "DVT",
        "thermal": "EVT",
        "drivetrain": "EVT",
        "firmware": "Concept",
    }

    fixtures_dir = tmp_path / "fixtures"
    fixtures_dir.mkdir()

    (fixtures_dir / "messages.json").write_text(json.dumps(messages))
    (fixtures_dir / "team_roster.json").write_text(json.dumps(team_roster))
    (fixtures_dir / "personas.json").write_text(json.dumps(personas))
    (fixtures_dir / "workstream_phases.json").write_text(json.dumps(workstream_phases))

    return fixtures_dir


class TestLoadFixtures:
    """Tests for the load_fixtures function."""

    def test_load_fixtures_returns_store(self, sample_fixtures_dir: Path) -> None:
        """Verify load_fixtures returns a FixtureStore from a valid directory."""
        store = load_fixtures(sample_fixtures_dir)
        assert isinstance(store, FixtureStore)

    def test_load_fixtures_raises_on_missing_dir(self, tmp_path: Path) -> None:
        """Verify load_fixtures raises FileNotFoundError for missing directory."""
        with pytest.raises(FileNotFoundError):
            load_fixtures(tmp_path / "nonexistent")

    def test_load_fixtures_raises_on_missing_file(self, tmp_path: Path) -> None:
        """Verify load_fixtures raises FileNotFoundError when a required file is absent."""
        fixtures_dir = tmp_path / "fixtures"
        fixtures_dir.mkdir()
        with pytest.raises(FileNotFoundError):
            load_fixtures(fixtures_dir)


class TestFixtureStoreMessages:
    """Tests for FixtureStore.get_messages accessor."""

    def test_get_messages_returns_list(self, sample_fixtures_dir: Path) -> None:
        """Verify get_messages returns a list of message dicts."""
        store = load_fixtures(sample_fixtures_dir)
        messages = store.get_messages()
        assert isinstance(messages, list)
        assert len(messages) == 2

    def test_get_messages_preserves_fields(self, sample_fixtures_dir: Path) -> None:
        """Verify message dicts contain all expected fields."""
        store = load_fixtures(sample_fixtures_dir)
        msg = store.get_messages()[0]
        assert msg["channel"] == "#chassis-design"
        assert msg["user_id"] == "U02ABCDEF"
        assert msg["text"] == "Uploaded rev D STEP files to shared drive"
        assert msg["message_ts"] == "1700000001.000001"

    def test_get_messages_returns_copy(self, sample_fixtures_dir: Path) -> None:
        """Verify get_messages returns a copy, not a reference to internal state."""
        store = load_fixtures(sample_fixtures_dir)
        messages = store.get_messages()
        messages.clear()
        assert len(store.get_messages()) == 2


class TestFixtureStoreTeamRoster:
    """Tests for FixtureStore.get_team_roster accessor."""

    def test_get_team_roster_returns_list(self, sample_fixtures_dir: Path) -> None:
        """Verify get_team_roster returns a list of roster entries."""
        store = load_fixtures(sample_fixtures_dir)
        roster = store.get_team_roster()
        assert isinstance(roster, list)
        assert len(roster) == 2

    def test_get_team_roster_has_required_fields(self, sample_fixtures_dir: Path) -> None:
        """Verify roster entries contain user_id, name, title, and role_archetype."""
        store = load_fixtures(sample_fixtures_dir)
        entry = store.get_team_roster()[0]
        assert entry["user_id"] == "U02ABCDEF"
        assert entry["name"] == "Maya Chen"
        assert entry["title"] == "Senior Mechanical Engineer"
        assert entry["role_archetype"] == "IC Engineer"


class TestFixtureStorePersonas:
    """Tests for FixtureStore.get_personas accessor."""

    def test_get_personas_returns_list(self, sample_fixtures_dir: Path) -> None:
        """Verify get_personas returns a list of Persona objects."""
        store = load_fixtures(sample_fixtures_dir)
        personas = store.get_personas()
        assert isinstance(personas, list)
        assert len(personas) == 1

    def test_get_personas_returns_typed_models(self, sample_fixtures_dir: Path) -> None:
        """Verify get_personas returns validated Persona instances."""
        store = load_fixtures(sample_fixtures_dir)
        persona = store.get_personas()[0]
        assert isinstance(persona, Persona)
        assert persona.user_id == "U02ABCDEF"
        assert persona.role_archetype == "IC Engineer"
        assert persona.workstream_affinities["chassis"] == 1.0


class TestFixtureStoreWorkstreamPhases:
    """Tests for FixtureStore.get_workstream_phases accessor."""

    def test_get_workstream_phases_returns_dict(self, sample_fixtures_dir: Path) -> None:
        """Verify get_workstream_phases returns a workstream-to-phase mapping."""
        store = load_fixtures(sample_fixtures_dir)
        phases = store.get_workstream_phases()
        assert isinstance(phases, dict)
        assert phases["chassis"] == "DVT"
        assert phases["thermal"] == "EVT"

    def test_get_workstream_phases_returns_copy(self, sample_fixtures_dir: Path) -> None:
        """Verify get_workstream_phases returns a copy, not internal state."""
        store = load_fixtures(sample_fixtures_dir)
        phases = store.get_workstream_phases()
        phases.clear()
        assert len(store.get_workstream_phases()) == 4
