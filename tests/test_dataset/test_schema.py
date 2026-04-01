"""Tests for Slack message JSON schema and team roster definitions.

Validates the data contracts between the synthetic dataset and
the ingestion layer: raw message format, channel registry, and
team roster with role/channel assignments.
"""

import pytest
from pydantic import ValidationError

from digest.dataset.schema import (
    CHANNELS,
    SlackMessage,
    SlackReaction,
    TeamMember,
    TeamRoster,
)


class TestSlackReaction:
    """Tests for the SlackReaction model."""

    def test_valid_reaction(self) -> None:
        """Construct a valid reaction with name and user list."""
        reaction = SlackReaction(name="thumbsup", users=["U001", "U002"])
        assert reaction.name == "thumbsup"
        assert reaction.users == ["U001", "U002"]

    def test_reaction_empty_users(self) -> None:
        """Reaction with no users is valid (default empty list)."""
        reaction = SlackReaction(name="eyes", users=[])
        assert reaction.users == []


class TestSlackMessage:
    """Tests for the SlackMessage model."""

    def test_valid_message_minimal(self) -> None:
        """Construct a message with only required fields."""
        msg = SlackMessage(
            message_ts="1711900000.000001",
            channel="#chassis-design",
            user_id="U001",
            text="Updated torque spec to 3.1 Nm.",
        )
        assert msg.message_ts == "1711900000.000001"
        assert msg.thread_ts is None
        assert msg.reactions == []

    def test_valid_message_full(self) -> None:
        """Construct a message with all optional fields populated."""
        msg = SlackMessage(
            message_ts="1711900000.000001",
            thread_ts="1711899000.000001",
            channel="#drivetrain",
            user_id="U002",
            text="This affects the gearbox housing too.",
            reactions=[
                SlackReaction(name="eyes", users=["U003"]),
            ],
        )
        assert msg.thread_ts == "1711899000.000001"
        assert len(msg.reactions) == 1

    def test_message_requires_message_ts(self) -> None:
        """Message without message_ts raises validation error."""
        with pytest.raises(ValidationError):
            SlackMessage(
                channel="#chassis-design",
                user_id="U001",
                text="Hello",
            )

    def test_message_requires_channel(self) -> None:
        """Message without channel raises validation error."""
        with pytest.raises(ValidationError):
            SlackMessage(
                message_ts="1711900000.000001",
                user_id="U001",
                text="Hello",
            )

    def test_message_requires_user_id(self) -> None:
        """Message without user_id raises validation error."""
        with pytest.raises(ValidationError):
            SlackMessage(
                message_ts="1711900000.000001",
                channel="#chassis-design",
                text="Hello",
            )

    def test_message_requires_text(self) -> None:
        """Message without text raises validation error."""
        with pytest.raises(ValidationError):
            SlackMessage(
                message_ts="1711900000.000001",
                channel="#chassis-design",
                user_id="U001",
            )


class TestChannels:
    """Tests for the channel registry constant."""

    def test_channel_count(self) -> None:
        """Exactly 8 channels are defined per the design document."""
        assert len(CHANNELS) == 8

    def test_required_channels_present(self) -> None:
        """All 8 design-doc channels are present."""
        expected = {
            "#chassis-design",
            "#drivetrain",
            "#thermal-management",
            "#power-systems",
            "#sensors",
            "#firmware",
            "#supply-chain",
            "#amr-general",
        }
        assert set(CHANNELS) == expected

    def test_channels_are_hashtagged(self) -> None:
        """Every channel name starts with #."""
        for channel in CHANNELS:
            assert channel.startswith("#"), f"{channel} missing # prefix"


class TestTeamMember:
    """Tests for the TeamMember model."""

    def test_valid_team_member(self) -> None:
        """Construct a valid team member with all fields."""
        member = TeamMember(
            user_id="U001",
            name="Maya Chen",
            title="Senior Mechanical Engineer",
            primary_channels=["#chassis-design", "#thermal-management"],
        )
        assert member.user_id == "U001"
        assert member.name == "Maya Chen"
        assert len(member.primary_channels) == 2

    def test_team_member_requires_user_id(self) -> None:
        """TeamMember without user_id raises validation error."""
        with pytest.raises(ValidationError):
            TeamMember(
                name="Maya Chen",
                title="Senior ME",
                primary_channels=["#chassis-design"],
            )

    def test_team_member_requires_name(self) -> None:
        """TeamMember without name raises validation error."""
        with pytest.raises(ValidationError):
            TeamMember(
                user_id="U001",
                title="Senior ME",
                primary_channels=["#chassis-design"],
            )

    def test_team_member_requires_title(self) -> None:
        """TeamMember without title raises validation error."""
        with pytest.raises(ValidationError):
            TeamMember(
                user_id="U001",
                name="Maya Chen",
                primary_channels=["#chassis-design"],
            )

    def test_team_member_default_channels(self) -> None:
        """TeamMember with no primary_channels gets empty list."""
        member = TeamMember(
            user_id="U001",
            name="Maya Chen",
            title="Senior ME",
        )
        assert member.primary_channels == []


class TestTeamRoster:
    """Tests for the TeamRoster - the full 20-person team."""

    def test_roster_has_20_members(self) -> None:
        """Exactly 20 team members are defined per the issue spec."""
        roster = TeamRoster()
        assert len(roster.members) == 20

    def test_roster_user_ids_unique(self) -> None:
        """All user_ids in the roster are unique."""
        roster = TeamRoster()
        ids = [m.user_id for m in roster.members]
        assert len(ids) == len(set(ids))

    def test_roster_names_unique(self) -> None:
        """All names in the roster are unique."""
        roster = TeamRoster()
        names = [m.name for m in roster.members]
        assert len(names) == len(set(names))

    def test_roster_covers_all_channels(self) -> None:
        """Every channel has at least one team member assigned to it."""
        roster = TeamRoster()
        covered = set()
        for member in roster.members:
            covered.update(member.primary_channels)
        for channel in CHANNELS:
            assert channel in covered, f"No member assigned to {channel}"

    def test_roster_members_use_valid_channels(self) -> None:
        """Every primary_channel reference is a valid channel."""
        roster = TeamRoster()
        for member in roster.members:
            for ch in member.primary_channels:
                assert ch in CHANNELS, f"{member.name} references invalid channel {ch}"

    def test_roster_has_diverse_titles(self) -> None:
        """Roster has at least 5 distinct titles (diverse roles)."""
        roster = TeamRoster()
        titles = {m.title for m in roster.members}
        assert len(titles) >= 5
