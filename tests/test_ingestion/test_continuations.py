"""Tests for thread reconstruction Pass 2: implicit continuation detection.

Validates that top-level messages are linked to antecedent threads
via @-mentions, quote blocks, and explicit back-references.
"""

from evercurrent.dataset.schema import SlackMessage
from evercurrent.ingestion.continuations import detect_continuations
from evercurrent.ingestion.threads import ThreadBundle


def _msg(
    ts: str,
    text: str,
    thread_ts: str | None = None,
    channel: str = "#chassis-design",
    user_id: str = "U001",
) -> SlackMessage:
    """Create a minimal SlackMessage for testing."""
    return SlackMessage(
        message_ts=ts,
        thread_ts=thread_ts,
        channel=channel,
        user_id=user_id,
        text=text,
    )


def _bundle(
    root: SlackMessage,
    replies: list[SlackMessage] | None = None,
) -> ThreadBundle:
    """Create a ThreadBundle from root and optional replies."""
    return ThreadBundle(root_message=root, replies=replies or [])


class TestAtMentionContinuation:
    """Detect continuations via @-mention of a recent thread author."""

    def test_at_mention_links_to_thread(self) -> None:
        """Top-level msg mentioning a thread's last author is a continuation."""
        thread = _bundle(
            root=_msg("1000.001", "Starting the thermal discussion", user_id="U001"),
            replies=[
                _msg("1000.002", "I'll check the data", thread_ts="1000.001", user_id="U002"),
            ],
        )
        standalone = _msg("1000.003", "@U002 got the thermal results back")
        result = detect_continuations([thread], [standalone])
        assert len(result) == 1
        assert result[0].root_message.message_ts == "1000.001"
        assert any(m.message_ts == "1000.003" for m in result[0].continuations)

    def test_at_mention_requires_same_channel(self) -> None:
        """@-mention in a different channel does not link."""
        thread = _bundle(
            root=_msg("1000.001", "Thermal issue", channel="#thermal-management", user_id="U001"),
            replies=[
                _msg(
                    "1000.002",
                    "Checking",
                    thread_ts="1000.001",
                    channel="#thermal-management",
                    user_id="U002",
                ),
            ],
        )
        standalone = _msg("1000.003", "@U002 unrelated", channel="#firmware")
        result = detect_continuations([thread], [standalone])
        assert len(result) == 0


class TestQuoteBlockContinuation:
    """Detect continuations via quote blocks matching earlier text."""

    def test_quote_block_links_to_thread(self) -> None:
        """Top-level msg quoting thread text is a continuation."""
        thread = _bundle(
            root=_msg("1000.001", "The thermal pad resistance is 2.8 C/W"),
        )
        standalone = _msg("1000.003", "> The thermal pad resistance is 2.8 C/W\nUpdated results")
        result = detect_continuations([thread], [standalone])
        assert len(result) == 1

    def test_partial_quote_still_matches(self) -> None:
        """Quote matching a substring of thread text links."""
        thread = _bundle(
            root=_msg("1000.001", "Motor junction temp hit 145C during peak load testing"),
        )
        standalone = _msg("1000.003", "> junction temp hit 145C\nFixed it")
        result = detect_continuations([thread], [standalone])
        assert len(result) == 1


class TestBackReferenceContinuation:
    """Detect continuations via explicit back-references."""

    def test_re_prefix_links_to_thread(self) -> None:
        """Message with 're: topic' links to thread about that topic."""
        thread = _bundle(
            root=_msg("1000.001", "Magnesium housing weight analysis"),
        )
        standalone = _msg("1000.003", "re: magnesium housing — updated the spreadsheet")
        result = detect_continuations([thread], [standalone])
        assert len(result) == 1

    def test_following_up_links(self) -> None:
        """'following up on' phrase links to matching thread."""
        thread = _bundle(
            root=_msg("1000.001", "FPGA timing closure failing"),
        )
        standalone = _msg("1000.003", "Following up on the FPGA timing issue — resolved")
        result = detect_continuations([thread], [standalone])
        assert len(result) == 1


class TestContinuationEdgeCases:
    """Edge cases for continuation detection."""

    def test_no_continuations(self) -> None:
        """Unrelated standalone messages don't link anywhere."""
        thread = _bundle(root=_msg("1000.001", "Chassis weight budget"))
        standalone = _msg("2000.001", "Lunch in the break room at noon")
        result = detect_continuations([thread], [standalone])
        assert len(result) == 0

    def test_empty_standalones(self) -> None:
        """No standalones means no continuations."""
        thread = _bundle(root=_msg("1000.001", "Some thread"))
        result = detect_continuations([thread], [])
        assert len(result) == 0

    def test_empty_threads(self) -> None:
        """No threads means no matches possible."""
        standalone = _msg("1000.001", "@U002 hey")
        result = detect_continuations([], [standalone])
        assert len(result) == 0
