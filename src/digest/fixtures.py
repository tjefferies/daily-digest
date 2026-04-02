"""In-memory fixture store for prototype data loading.

Loads synthetic JSON fixture files from a directory and provides
typed accessor functions for pipeline layers. Fixture data is also
persisted to Postgres and Neo4j during pipeline runs.
"""

import json
from pathlib import Path
from typing import Any

from digest.models.persona import Persona

REQUIRED_FILES = [
    "messages.json",
    "team_roster.json",
    "personas.json",
    "workstream_phases.json",
]


class FixtureStore:
    """In-memory store for loaded fixture data.

    Holds parsed JSON data and provides typed accessor functions that
    return copies to prevent mutation of internal state.

    Attributes:
        _messages: Raw message dicts from messages.json.
        _team_roster: Team roster entries from team_roster.json.
        _personas: Validated Persona model instances.
        _workstream_phases: Workstream name to phase mapping.
    """

    def __init__(
        self,
        messages: list[dict[str, Any]],
        team_roster: list[dict[str, Any]],
        personas: list[Persona],
        workstream_phases: dict[str, str],
    ) -> None:
        """Initialize the fixture store with pre-loaded data.

        Args:
            messages: List of raw Slack message dicts.
            team_roster: List of team member dicts.
            personas: List of validated Persona instances.
            workstream_phases: Map of workstream name to development phase.
        """
        self._messages = messages
        self._team_roster = team_roster
        self._personas = personas
        self._workstream_phases = workstream_phases

    def get_messages(self) -> list[dict[str, Any]]:
        """Return a copy of all loaded Slack messages.

        Returns:
            List of message dicts with keys: message_ts, thread_ts,
            channel, user_id, text, reactions.
        """
        return list(self._messages)

    def get_team_roster(self) -> list[dict[str, Any]]:
        """Return a copy of the team roster.

        Returns:
            List of roster entry dicts with keys: user_id, name,
            title, role_archetype.
        """
        return list(self._team_roster)

    def get_personas(self) -> list[Persona]:
        """Return the list of validated Persona models.

        Returns:
            List of Persona instances loaded from fixtures.
        """
        return list(self._personas)

    def get_workstream_phases(self) -> dict[str, str]:
        """Return a copy of the workstream-to-phase mapping.

        Returns:
            Dict mapping workstream names to development phase strings.
        """
        return dict(self._workstream_phases)


def load_fixtures(fixtures_dir: Path) -> FixtureStore:
    """Load all fixture JSON files from a directory into a FixtureStore.

    Args:
        fixtures_dir: Path to the directory containing fixture JSON files.

    Returns:
        A populated FixtureStore instance.

    Raises:
        FileNotFoundError: If the directory or any required file is missing.
    """
    if not fixtures_dir.is_dir():
        msg = f"Fixtures directory not found: {fixtures_dir}"
        raise FileNotFoundError(msg)

    for filename in REQUIRED_FILES:
        filepath = fixtures_dir / filename
        if not filepath.exists():
            msg = f"Required fixture file missing: {filepath}"
            raise FileNotFoundError(msg)

    messages = json.loads((fixtures_dir / "messages.json").read_text())
    team_roster = json.loads((fixtures_dir / "team_roster.json").read_text())
    raw_personas = json.loads((fixtures_dir / "personas.json").read_text())
    workstream_phases = json.loads((fixtures_dir / "workstream_phases.json").read_text())

    personas = [Persona(**p) for p in raw_personas]

    return FixtureStore(
        messages=messages,
        team_roster=team_roster,
        personas=personas,
        workstream_phases=workstream_phases,
    )
