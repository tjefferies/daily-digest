"""Tests for context window assembly with long-thread compression.

Validates that ThreadBundles are assembled into ContextWindow objects,
with compression applied when threads exceed the token limit.
"""

from digest.dataset.schema import SlackMessage, SlackReaction
from digest.ingestion.context_window import ContextWindow, assemble_context_windows
from digest.ingestion.threads import ThreadBundle


def _msg(
    ts: str,
    text: str,
    thread_ts: str | None = None,
    channel: str = "#chassis-design",
    user_id: str = "U001",
    reactions: list[SlackReaction] | None = None,
) -> SlackMessage:
    """Create a SlackMessage for testing."""
    return SlackMessage(
        message_ts=ts,
        thread_ts=thread_ts,
        channel=channel,
        user_id=user_id,
        text=text,
        reactions=reactions or [],
    )


def _bundle(
    root: SlackMessage,
    replies: list[SlackMessage] | None = None,
) -> ThreadBundle:
    """Create a ThreadBundle."""
    return ThreadBundle(root_message=root, replies=replies or [])


class TestContextWindow:
    """Tests for ContextWindow model fields."""

    def test_has_required_fields(self) -> None:
        """ContextWindow has thread_text, channel, thread_ts, message_range."""
        cw = ContextWindow(
            thread_text="hello world",
            channel="#chassis-design",
            thread_ts="1000.001",
            message_range=("1000.001", "1000.003"),
            compressed=False,
        )
        assert cw.thread_text == "hello world"
        assert cw.channel == "#chassis-design"
        assert cw.thread_ts == "1000.001"
        assert cw.message_range == ("1000.001", "1000.003")
        assert cw.compressed is False


class TestAssembleShortThreads:
    """Short threads should be included in full."""

    def test_short_thread_full_text(self) -> None:
        """Thread within token limit includes all messages."""
        bundle = _bundle(
            root=_msg("1000.001", "Root message"),
            replies=[
                _msg("1000.002", "Reply one", thread_ts="1000.001"),
                _msg("1000.003", "Reply two", thread_ts="1000.001"),
            ],
        )
        windows = assemble_context_windows([bundle])
        assert len(windows) == 1
        assert "Root message" in windows[0].thread_text
        assert "Reply one" in windows[0].thread_text
        assert "Reply two" in windows[0].thread_text
        assert windows[0].compressed is False

    def test_message_range_spans_thread(self) -> None:
        """Message range covers first to last timestamp."""
        bundle = _bundle(
            root=_msg("1000.001", "Root"),
            replies=[
                _msg("1000.002", "Middle", thread_ts="1000.001"),
                _msg("1000.003", "End", thread_ts="1000.001"),
            ],
        )
        windows = assemble_context_windows([bundle])
        assert windows[0].message_range == ("1000.001", "1000.003")

    def test_standalone_message_range(self) -> None:
        """Standalone message has same start and end range."""
        bundle = _bundle(root=_msg("1000.001", "Solo"))
        windows = assemble_context_windows([bundle])
        assert windows[0].message_range == ("1000.001", "1000.001")


class TestAssembleLongThreads:
    """Long threads should be compressed."""

    def _make_long_bundle(self, n_replies: int = 30) -> ThreadBundle:
        """Create a bundle with many replies to trigger compression."""
        root = _msg("1000.001", "Root: " + "x" * 200)
        replies = []
        for i in range(n_replies):
            ts = f"1000.{i + 2:03d}"
            reactions = []
            if i == 10:
                reactions = [
                    SlackReaction(name="rotating_light", users=["U002", "U003", "U004"]),
                ]
            replies.append(
                _msg(
                    ts,
                    f"Reply {i}: " + "y" * 200,
                    thread_ts="1000.001",
                    reactions=reactions,
                ),
            )
        return _bundle(root, replies)

    def test_long_thread_is_compressed(self) -> None:
        """Thread over token limit is marked compressed."""
        bundle = self._make_long_bundle()
        windows = assemble_context_windows([bundle], max_tokens=500)
        assert len(windows) == 1
        assert windows[0].compressed is True

    def test_compressed_includes_root(self) -> None:
        """Compressed thread always includes root message."""
        bundle = self._make_long_bundle()
        windows = assemble_context_windows([bundle], max_tokens=500)
        assert "Root:" in windows[0].thread_text

    def test_compressed_includes_final_messages(self) -> None:
        """Compressed thread includes the last 5 messages."""
        bundle = self._make_long_bundle()
        windows = assemble_context_windows([bundle], max_tokens=500)
        assert "Reply 29:" in windows[0].thread_text

    def test_compressed_includes_most_reacted(self) -> None:
        """Compressed thread includes the most-reacted message."""
        bundle = self._make_long_bundle()
        windows = assemble_context_windows([bundle], max_tokens=500)
        assert "Reply 10:" in windows[0].thread_text


class TestAssembleMultipleBundles:
    """Multiple bundles produce multiple context windows."""

    def test_one_window_per_bundle(self) -> None:
        """Each bundle becomes one ContextWindow."""
        bundles = [
            _bundle(root=_msg("1000.001", "Thread A")),
            _bundle(root=_msg("2000.001", "Thread B")),
        ]
        windows = assemble_context_windows(bundles)
        assert len(windows) == 2

    def test_empty_bundles(self) -> None:
        """No bundles returns no windows."""
        assert assemble_context_windows([]) == []
