"""Tests for thread reconstruction Pass 1: structural grouping by thread_ts.

Validates that SlackMessages are grouped into ThreadBundle objects
based on their thread_ts field.
"""

from evercurrent.dataset.schema import SlackMessage
from evercurrent.ingestion.threads import ThreadBundle, group_by_thread


def _msg(
    ts: str,
    thread_ts: str | None = None,
    channel: str = "#chassis-design",
    user_id: str = "U001",
    text: str = "test",
) -> SlackMessage:
    """Create a minimal SlackMessage for testing."""
    return SlackMessage(
        message_ts=ts,
        thread_ts=thread_ts,
        channel=channel,
        user_id=user_id,
        text=text,
    )


class TestThreadBundle:
    """Tests for the ThreadBundle model."""

    def test_bundle_has_root_and_replies(self) -> None:
        """ThreadBundle holds a root_message and list of replies."""
        root = _msg("1000.001")
        reply = _msg("1000.002", thread_ts="1000.001")
        bundle = ThreadBundle(root_message=root, replies=[reply])
        assert bundle.root_message == root
        assert bundle.replies == [reply]

    def test_bundle_channel_from_root(self) -> None:
        """Bundle channel is the root message's channel."""
        root = _msg("1000.001", channel="#firmware")
        bundle = ThreadBundle(root_message=root, replies=[])
        assert bundle.root_message.channel == "#firmware"

    def test_bundle_empty_replies(self) -> None:
        """A standalone message creates a bundle with no replies."""
        root = _msg("1000.001")
        bundle = ThreadBundle(root_message=root, replies=[])
        assert len(bundle.replies) == 0


class TestGroupByThread:
    """Tests for group_by_thread function."""

    def test_single_thread(self) -> None:
        """Messages with same thread_ts form one bundle."""
        messages = [
            _msg("1000.001"),
            _msg("1000.002", thread_ts="1000.001"),
            _msg("1000.003", thread_ts="1000.001"),
        ]
        bundles = group_by_thread(messages)
        assert len(bundles) == 1
        assert bundles[0].root_message.message_ts == "1000.001"
        assert len(bundles[0].replies) == 2

    def test_multiple_threads(self) -> None:
        """Different thread_ts values create separate bundles."""
        messages = [
            _msg("1000.001"),
            _msg("1000.002", thread_ts="1000.001"),
            _msg("2000.001"),
            _msg("2000.002", thread_ts="2000.001"),
        ]
        bundles = group_by_thread(messages)
        assert len(bundles) == 2

    def test_standalone_messages_become_solo_bundles(self) -> None:
        """Top-level messages with no replies are solo bundles."""
        messages = [
            _msg("1000.001"),
            _msg("2000.001"),
        ]
        bundles = group_by_thread(messages)
        assert len(bundles) == 2
        assert all(len(b.replies) == 0 for b in bundles)

    def test_replies_ordered_by_timestamp(self) -> None:
        """Replies within a bundle are sorted by message_ts."""
        messages = [
            _msg("1000.003", thread_ts="1000.001"),
            _msg("1000.001"),
            _msg("1000.002", thread_ts="1000.001"),
        ]
        bundles = group_by_thread(messages)
        reply_ts = [r.message_ts for r in bundles[0].replies]
        assert reply_ts == sorted(reply_ts)

    def test_bundles_ordered_by_root_timestamp(self) -> None:
        """Bundles are sorted by root message timestamp."""
        messages = [
            _msg("2000.001"),
            _msg("1000.001"),
        ]
        bundles = group_by_thread(messages)
        root_ts = [b.root_message.message_ts for b in bundles]
        assert root_ts == sorted(root_ts)

    def test_empty_input(self) -> None:
        """Empty message list returns empty bundle list."""
        assert group_by_thread([]) == []

    def test_thread_ts_equal_message_ts_is_root(self) -> None:
        """Message where thread_ts == message_ts is treated as root."""
        messages = [
            _msg("1000.001", thread_ts="1000.001"),
            _msg("1000.002", thread_ts="1000.001"),
        ]
        bundles = group_by_thread(messages)
        assert len(bundles) == 1
        assert bundles[0].root_message.message_ts == "1000.001"
        assert len(bundles[0].replies) == 1

    def test_orphan_reply_creates_bundle(self) -> None:
        """Reply whose root is missing still forms a bundle."""
        messages = [
            _msg("1000.002", thread_ts="1000.001"),
            _msg("1000.003", thread_ts="1000.001"),
        ]
        bundles = group_by_thread(messages)
        assert len(bundles) == 1
