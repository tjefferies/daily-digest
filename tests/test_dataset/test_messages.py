"""Tests for synthetic Slack message dataset.

Validates that the generated messages fixture meets the design
document requirements: 300-500 messages, engineer-register prose,
thread depth variety, and coverage of all channels and team members.
"""

from evercurrent.dataset.messages import load_messages
from evercurrent.dataset.schema import CHANNELS, TeamRoster


class TestMessageCount:
    """Tests for message volume requirements."""

    def test_message_count_in_range(self) -> None:
        """Dataset has 300-500 messages per design doc spec."""
        messages = load_messages()
        assert 300 <= len(messages) <= 500


class TestMessageStructure:
    """Tests for individual message schema compliance."""

    def test_all_messages_have_required_fields(self) -> None:
        """Every message has message_ts, channel, user_id, text."""
        messages = load_messages()
        for msg in messages:
            assert msg.message_ts
            assert msg.channel
            assert msg.user_id
            assert msg.text

    def test_message_timestamps_are_unique(self) -> None:
        """Every message has a unique timestamp."""
        messages = load_messages()
        timestamps = [m.message_ts for m in messages]
        assert len(timestamps) == len(set(timestamps))


class TestChannelCoverage:
    """Tests for channel distribution."""

    def test_all_channels_have_messages(self) -> None:
        """Every channel has at least one message."""
        messages = load_messages()
        channels_seen = {m.channel for m in messages}
        for channel in CHANNELS:
            assert channel in channels_seen, f"No messages in {channel}"

    def test_no_unknown_channels(self) -> None:
        """Every message uses a known channel."""
        messages = load_messages()
        valid = set(CHANNELS)
        for msg in messages:
            assert msg.channel in valid, f"Unknown channel: {msg.channel}"


class TestUserCoverage:
    """Tests for team member participation."""

    def test_majority_of_team_participates(self) -> None:
        """At least 15 of 20 team members have messages."""
        messages = load_messages()
        roster = TeamRoster()
        valid_ids = {m.user_id for m in roster.members}
        users_seen = {m.user_id for m in messages}
        participating = users_seen & valid_ids
        assert len(participating) >= 15

    def test_all_messages_from_valid_users(self) -> None:
        """Every message user_id is in the team roster."""
        messages = load_messages()
        roster = TeamRoster()
        valid_ids = {m.user_id for m in roster.members}
        for msg in messages:
            assert msg.user_id in valid_ids, f"Unknown user: {msg.user_id}"


class TestThreadStructure:
    """Tests for thread depth variety."""

    def test_has_threaded_messages(self) -> None:
        """Dataset includes threaded replies (non-None thread_ts)."""
        messages = load_messages()
        threaded = [m for m in messages if m.thread_ts is not None]
        assert len(threaded) >= 50

    def test_has_top_level_messages(self) -> None:
        """Dataset includes top-level messages (None thread_ts)."""
        messages = load_messages()
        top_level = [m for m in messages if m.thread_ts is None]
        assert len(top_level) >= 20

    def test_thread_depth_variety(self) -> None:
        """Dataset has both short and long threads."""
        messages = load_messages()
        threads: dict[str, int] = {}
        for msg in messages:
            ts = msg.thread_ts or msg.message_ts
            threads[ts] = threads.get(ts, 0) + 1
        depths = sorted(threads.values(), reverse=True)
        has_short = any(d <= 5 for d in depths)
        has_long = any(d >= 10 for d in depths)
        assert has_short, "No short threads found"
        assert has_long, "No long threads (>=10 msgs) found"


class TestReactions:
    """Tests for emoji reaction presence."""

    def test_some_messages_have_reactions(self) -> None:
        """At least some messages have emoji reactions."""
        messages = load_messages()
        with_reactions = [m for m in messages if m.reactions]
        assert len(with_reactions) >= 10
