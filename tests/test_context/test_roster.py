"""Tests for the team roster with role-archetype taxonomy.

Validates the RosterEntry model and TeamRosterService that the
Layer 4 scoring engine queries to look up role archetypes for
the role-type alignment dimension.
"""

import pytest
from pydantic import ValidationError

from evercurrent.context.roster import RosterEntry, TeamRosterService
from evercurrent.models.persona import RoleArchetype  # noqa: TC001 (used in type annotation)


class TestRosterEntry:
    """Tests for the RosterEntry model."""

    def test_valid_roster_entry(self) -> None:
        """Construct a valid roster entry with all required fields."""
        entry = RosterEntry(
            user_id="U001",
            name="Maya Chen",
            title="Senior Mechanical Engineer",
            role_archetype="IC Engineer",
        )
        assert entry.user_id == "U001"
        assert entry.name == "Maya Chen"
        assert entry.title == "Senior Mechanical Engineer"
        assert entry.role_archetype == "IC Engineer"

    def test_all_role_archetypes_accepted(self) -> None:
        """Every valid RoleArchetype literal is accepted."""
        archetypes: list[RoleArchetype] = [
            "IC Engineer",
            "Eng Manager",
            "Program Manager",
            "Supply Chain",
            "Executive",
        ]
        for archetype in archetypes:
            entry = RosterEntry(
                user_id="U999",
                name="Test",
                title="Test",
                role_archetype=archetype,
            )
            assert entry.role_archetype == archetype

    def test_invalid_role_archetype_rejected(self) -> None:
        """Invalid role archetype raises validation error."""
        with pytest.raises(ValidationError):
            RosterEntry(
                user_id="U001",
                name="Test",
                title="Test",
                role_archetype="Invalid Role",  # type: ignore[arg-type]
            )

    def test_requires_user_id(self) -> None:
        """RosterEntry without user_id raises validation error."""
        with pytest.raises(ValidationError):
            RosterEntry(
                name="Maya Chen",
                title="Senior ME",
                role_archetype="IC Engineer",
            )

    def test_requires_name(self) -> None:
        """RosterEntry without name raises validation error."""
        with pytest.raises(ValidationError):
            RosterEntry(
                user_id="U001",
                title="Senior ME",
                role_archetype="IC Engineer",
            )

    def test_requires_title(self) -> None:
        """RosterEntry without title raises validation error."""
        with pytest.raises(ValidationError):
            RosterEntry(
                user_id="U001",
                name="Maya Chen",
                role_archetype="IC Engineer",
            )

    def test_requires_role_archetype(self) -> None:
        """RosterEntry without role_archetype raises validation error."""
        with pytest.raises(ValidationError):
            RosterEntry(
                user_id="U001",
                name="Maya Chen",
                title="Senior ME",
            )


class TestTeamRosterService:
    """Tests for the TeamRosterService lookup layer."""

    @pytest.fixture()
    def sample_entries(self) -> list[RosterEntry]:
        """Build a small roster for testing lookups."""
        return [
            RosterEntry(
                user_id="U001",
                name="Maya Chen",
                title="Senior Mechanical Engineer",
                role_archetype="IC Engineer",
            ),
            RosterEntry(
                user_id="U007",
                name="Elena Vasquez",
                title="Supply Chain Manager",
                role_archetype="Supply Chain",
            ),
            RosterEntry(
                user_id="U010",
                name="Ryan Torres",
                title="Engineering Manager",
                role_archetype="Eng Manager",
            ),
        ]

    def test_load_from_entries(
        self,
        sample_entries: list[RosterEntry],
    ) -> None:
        """Service loads from a list of RosterEntry objects."""
        service = TeamRosterService(sample_entries)
        assert len(service.all_members()) == 3

    def test_get_by_user_id(
        self,
        sample_entries: list[RosterEntry],
    ) -> None:
        """Look up a member by user_id returns correct entry."""
        service = TeamRosterService(sample_entries)
        entry = service.get_by_user_id("U007")
        assert entry is not None
        assert entry.name == "Elena Vasquez"
        assert entry.role_archetype == "Supply Chain"

    def test_get_by_user_id_missing(
        self,
        sample_entries: list[RosterEntry],
    ) -> None:
        """Look up a non-existent user_id returns None."""
        service = TeamRosterService(sample_entries)
        assert service.get_by_user_id("U999") is None

    def test_get_role_archetype(
        self,
        sample_entries: list[RosterEntry],
    ) -> None:
        """Retrieve role archetype for a known user."""
        service = TeamRosterService(sample_entries)
        assert service.get_role_archetype("U010") == "Eng Manager"

    def test_get_role_archetype_missing(
        self,
        sample_entries: list[RosterEntry],
    ) -> None:
        """Retrieve role archetype for unknown user returns None."""
        service = TeamRosterService(sample_entries)
        assert service.get_role_archetype("U999") is None

    def test_all_members_returns_copy(
        self,
        sample_entries: list[RosterEntry],
    ) -> None:
        """all_members returns a copy, not the internal list."""
        service = TeamRosterService(sample_entries)
        members = service.all_members()
        members.pop()
        assert len(service.all_members()) == 3

    def test_load_from_dicts(self) -> None:
        """Service can load from raw dicts (fixture store format)."""
        raw = [
            {
                "user_id": "U001",
                "name": "Maya Chen",
                "title": "Senior ME",
                "role_archetype": "IC Engineer",
            },
        ]
        service = TeamRosterService.from_dicts(raw)
        assert len(service.all_members()) == 1
        assert service.get_by_user_id("U001") is not None

    def test_default_roster_has_20_members(self) -> None:
        """Default roster built from dataset has 20 members."""
        service = TeamRosterService.default()
        assert len(service.all_members()) == 20

    def test_default_roster_all_have_archetypes(self) -> None:
        """Every member in the default roster has a valid archetype."""
        valid_archetypes = {
            "IC Engineer",
            "Eng Manager",
            "Program Manager",
            "Supply Chain",
            "Executive",
        }
        service = TeamRosterService.default()
        for member in service.all_members():
            assert member.role_archetype in valid_archetypes, (
                f"{member.name} has invalid archetype: {member.role_archetype}"
            )

    def test_default_roster_has_diverse_archetypes(self) -> None:
        """Default roster covers at least 3 different archetypes."""
        service = TeamRosterService.default()
        archetypes = {m.role_archetype for m in service.all_members()}
        assert len(archetypes) >= 3
