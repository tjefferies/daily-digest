"""Tests for thread reconstruction Pass 2: implicit continuation detection.

Validates that top-level messages are linked to antecedent threads
via @-mentions, quote blocks, explicit back-references, and semantic
similarity (hybrid keyword + embedding approach).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from digest.dataset.schema import SlackMessage
from digest.ingestion.continuations import detect_continuations
from digest.ingestion.threads import ThreadBundle

if TYPE_CHECKING:
    from digest.ingestion.embeddings import Embedder


class MockEmbedder:
    """Deterministic embedder mapping known texts to fixed vectors.

    Keys are matched case-insensitively. Unknown texts get a zero vector.
    """

    def __init__(self, mapping: dict[str, list[float]]) -> None:
        """Initialize with a text-to-vector mapping.

        Args:
            mapping: Dict of text → embedding vector. Keys are lowercased.
        """
        self._mapping = {k.lower(): v for k, v in mapping.items()}
        self._dim = len(next(iter(mapping.values()))) if mapping else 3

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Return pre-defined vectors for known texts, zeros otherwise."""
        zero = [0.0] * self._dim
        return [self._mapping.get(t.lower().strip(), zero) for t in texts]


# Verify MockEmbedder satisfies the protocol at import time.
_: type[Embedder] = MockEmbedder  # type: ignore[assignment]


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
        standalone = _msg("1000.003", "re: magnesium housing - updated the spreadsheet")
        result = detect_continuations([thread], [standalone])
        assert len(result) == 1

    def test_following_up_links(self) -> None:
        """'following up on' phrase links to matching thread."""
        thread = _bundle(
            root=_msg("1000.001", "FPGA timing closure failing"),
        )
        standalone = _msg("1000.003", "Following up on the FPGA timing issue - resolved")
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


class TestSemanticContinuation:
    """Detect continuations via semantic embedding similarity."""

    def test_semantic_match_links_related_messages(self) -> None:
        """Semantically similar standalone links to matching thread."""
        thread = _bundle(
            root=_msg("1000.001", "Motor overheating during endurance test"),
        )
        standalone = _msg("1000.003", "thermal paste application was inconsistent")
        embedder = MockEmbedder(
            {
                "motor overheating during endurance test": [0.9, 0.1, 0.0],
                "thermal paste application was inconsistent": [0.85, 0.15, 0.0],
            }
        )
        result = detect_continuations(
            [thread],
            [standalone],
            embedder=embedder,
            similarity_threshold=0.4,
        )
        assert len(result) == 1
        assert result[0].confidence < 1.0

    def test_semantic_below_threshold_does_not_link(self) -> None:
        """Low similarity does not create a link."""
        thread = _bundle(root=_msg("1000.001", "Chassis weight budget"))
        standalone = _msg("1000.003", "Lunch in the break room")
        embedder = MockEmbedder(
            {
                "chassis weight budget": [1.0, 0.0, 0.0],
                "lunch in the break room": [0.0, 0.0, 1.0],
            }
        )
        result = detect_continuations(
            [thread],
            [standalone],
            embedder=embedder,
            similarity_threshold=0.4,
        )
        assert len(result) == 0

    def test_structural_match_takes_precedence_over_semantic(self) -> None:
        """Regex match yields confidence=1.0 even when embedder is provided."""
        thread = _bundle(
            root=_msg("1000.001", "Magnesium housing analysis"),
        )
        standalone = _msg("1000.003", "re: magnesium housing - updated")
        embedder = MockEmbedder({})
        result = detect_continuations(
            [thread],
            [standalone],
            embedder=embedder,
            similarity_threshold=0.4,
        )
        assert len(result) == 1
        assert result[0].confidence == 1.0

    def test_semantic_requires_same_channel(self) -> None:
        """Semantic match respects channel boundary."""
        thread = _bundle(
            root=_msg("1000.001", "Motor overheating", channel="#thermal-management"),
        )
        standalone = _msg(
            "1000.003",
            "Motor overheating fixed",
            channel="#firmware",
        )
        embedder = MockEmbedder(
            {
                "motor overheating": [1.0, 0.0, 0.0],
                "motor overheating fixed": [0.99, 0.01, 0.0],
            }
        )
        result = detect_continuations(
            [thread],
            [standalone],
            embedder=embedder,
            similarity_threshold=0.4,
        )
        assert len(result) == 0

    def test_no_embedder_uses_regex_only(self) -> None:
        """Without embedder, only regex matching is used."""
        thread = _bundle(root=_msg("1000.001", "Motor overheating"))
        standalone = _msg("1000.003", "thermal paste was inconsistent")
        result = detect_continuations([thread], [standalone])
        assert len(result) == 0

    def test_semantic_picks_best_match_among_bundles(self) -> None:
        """When multiple bundles are in the same channel, picks highest similarity."""
        thermal_thread = _bundle(
            root=_msg("1000.001", "Thermal paste application process"),
        )
        weight_thread = _bundle(
            root=_msg("1000.002", "Chassis weight budget review"),
        )
        standalone = _msg("1000.003", "Updated the paste application procedure")
        embedder = MockEmbedder(
            {
                "thermal paste application process": [0.9, 0.1, 0.0],
                "chassis weight budget review": [0.1, 0.0, 0.9],
                "updated the paste application procedure": [0.85, 0.15, 0.0],
            }
        )
        result = detect_continuations(
            [thermal_thread, weight_thread],
            [standalone],
            embedder=embedder,
            similarity_threshold=0.4,
        )
        assert len(result) == 1
        assert result[0].root_message.message_ts == "1000.001"

    def test_confidence_reflects_similarity_score(self) -> None:
        """Semantic match confidence equals the cosine similarity."""
        thread = _bundle(
            root=_msg("1000.001", "FPGA timing closure"),
        )
        standalone = _msg("1000.003", "Timing constraints resolved")
        embedder = MockEmbedder(
            {
                "fpga timing closure": [0.8, 0.2, 0.0],
                "timing constraints resolved": [0.7, 0.3, 0.0],
            }
        )
        result = detect_continuations(
            [thread],
            [standalone],
            embedder=embedder,
            similarity_threshold=0.4,
        )
        assert len(result) == 1
        assert 0.4 < result[0].confidence < 1.0
