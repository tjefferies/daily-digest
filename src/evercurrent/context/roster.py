"""Team roster with role-archetype taxonomy for the Context Backbone.

Provides the RosterEntry model and TeamRosterService that the Layer 4
scoring engine queries to look up role archetypes for the role-type
alignment dimension (section 5.2).
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from evercurrent.config.loader import get_config
from evercurrent.models.persona import RoleArchetype  # noqa: TC001 (runtime Pydantic validation)


class RosterEntry(BaseModel):
    """A team member with role-archetype classification.

    Extends the raw dataset TeamMember with a role_archetype field
    used by the Layer 4 role-type alignment scoring matrix.

    Attributes:
        user_id: Slack user ID.
        name: Display name.
        title: Job title.
        role_archetype: One of five role archetypes from the scoring matrix.
    """

    user_id: str
    name: str
    title: str
    role_archetype: RoleArchetype


class TeamRosterService:
    """Lookup service for the team roster.

    Provides O(1) user_id lookups for the scoring engine to retrieve
    role archetypes and team member metadata.

    Attributes:
        _members: Ordered list of roster entries.
        _by_user_id: Index mapping user_id to RosterEntry.
    """

    def __init__(self, members: list[RosterEntry]) -> None:
        """Initialize the roster service from a list of entries.

        Args:
            members: List of RosterEntry objects.
        """
        self._members = list(members)
        self._by_user_id: dict[str, RosterEntry] = {m.user_id: m for m in self._members}

    @classmethod
    def from_dicts(cls, raw: list[dict[str, Any]]) -> TeamRosterService:
        """Create a roster service from raw dicts (fixture store format).

        Args:
            raw: List of dicts with keys matching RosterEntry fields.

        Returns:
            A populated TeamRosterService.
        """
        entries = [RosterEntry(**d) for d in raw]
        return cls(entries)

    @classmethod
    def default(cls) -> TeamRosterService:
        """Create the default 20-person AMR team roster.

        Builds the roster from the dataset schema's TeamRoster,
        assigning role archetypes based on job titles.

        Returns:
            A TeamRosterService with 20 members and assigned archetypes.
        """
        from evercurrent.dataset.schema import TeamRoster

        roster = TeamRoster()
        entries = [
            RosterEntry(
                user_id=m.user_id,
                name=m.name,
                title=m.title,
                role_archetype=_infer_archetype(m.title),
            )
            for m in roster.members
        ]
        return cls(entries)

    def get_by_user_id(self, user_id: str) -> RosterEntry | None:
        """Look up a team member by Slack user_id.

        Args:
            user_id: The Slack user ID to look up.

        Returns:
            The RosterEntry if found, None otherwise.
        """
        return self._by_user_id.get(user_id)

    def get_role_archetype(self, user_id: str) -> RoleArchetype | None:
        """Get the role archetype for a user.

        Args:
            user_id: The Slack user ID to look up.

        Returns:
            The role archetype string if found, None otherwise.
        """
        entry = self._by_user_id.get(user_id)
        return entry.role_archetype if entry else None

    def all_members(self) -> list[RosterEntry]:
        """Return a copy of all roster entries.

        Returns:
            List of all RosterEntry objects.
        """
        return list(self._members)


_scoring_cfg = get_config()["scoring"]
_TITLE_TO_ARCHETYPE: dict[str, RoleArchetype] = _scoring_cfg["title_to_archetype"]
_DEFAULT_ARCHETYPE: RoleArchetype = _scoring_cfg["default_archetype"]


def _infer_archetype(title: str) -> RoleArchetype:
    """Infer role archetype from job title.

    Uses exact match on known management/leadership titles,
    defaulting to IC Engineer for all technical individual
    contributor roles.

    Args:
        title: The job title string.

    Returns:
        The inferred RoleArchetype literal.
    """
    return _TITLE_TO_ARCHETYPE.get(title, _DEFAULT_ARCHETYPE)
