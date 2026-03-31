"""Tests for the ingestion message loader.

Validates that the loader converts raw message dicts from the
FixtureStore into typed SlackMessage objects, time-ordered.
"""

from typing import Any

import pytest

from evercurrent.dataset.schema import SlackMessage
from evercurrent.fixtures import FixtureStore
from evercurrent.ingestion.loader import load_message_stream


def _make_store(
    messages: list[dict[str, Any]],
) -> FixtureStore:
    """Create a minimal FixtureStore with given messages."""
    return FixtureStore(
        messages=messages,
        team_roster=[],
        personas=[],
        workstream_phases={},
    )


@pytest.fixture
def sample_messages() -> list[dict[str, Any]]:
    """Three messages in non-chronological order."""
    return [
        {
            "message_ts": "1711901120.000003",
            "thread_ts": "1711901000.000001",
            "channel": "#chassis-design",
            "user_id": "U003",
            "text": "Third message in time",
            "reactions": [],
        },
        {
            "message_ts": "1711901000.000001",
            "thread_ts": None,
            "channel": "#chassis-design",
            "user_id": "U001",
            "text": "First message in time",
            "reactions": [{"name": "thumbsup", "users": ["U002"]}],
        },
        {
            "message_ts": "1711901060.000002",
            "thread_ts": "1711901000.000001",
            "channel": "#chassis-design",
            "user_id": "U002",
            "text": "Second message in time",
            "reactions": [],
        },
    ]


class TestLoadMessageStream:
    """Tests for load_message_stream function."""

    def test_returns_list_of_slack_messages(
        self,
        sample_messages: list[dict[str, Any]],
    ) -> None:
        """All returned items are SlackMessage instances."""
        store = _make_store(sample_messages)
        result = load_message_stream(store)
        assert all(isinstance(m, SlackMessage) for m in result)

    def test_preserves_message_count(
        self,
        sample_messages: list[dict[str, Any]],
    ) -> None:
        """Output has the same number of messages as input."""
        store = _make_store(sample_messages)
        result = load_message_stream(store)
        assert len(result) == len(sample_messages)

    def test_time_ordered(
        self,
        sample_messages: list[dict[str, Any]],
    ) -> None:
        """Messages are sorted by message_ts ascending."""
        store = _make_store(sample_messages)
        result = load_message_stream(store)
        timestamps = [m.message_ts for m in result]
        assert timestamps == sorted(timestamps)

    def test_preserves_fields(
        self,
        sample_messages: list[dict[str, Any]],
    ) -> None:
        """All message fields are correctly mapped."""
        store = _make_store(sample_messages)
        result = load_message_stream(store)
        first = result[0]
        assert first.message_ts == "1711901000.000001"
        assert first.thread_ts is None
        assert first.channel == "#chassis-design"
        assert first.user_id == "U001"
        assert first.text == "First message in time"

    def test_preserves_reactions(
        self,
        sample_messages: list[dict[str, Any]],
    ) -> None:
        """Reactions are parsed into SlackReaction objects."""
        store = _make_store(sample_messages)
        result = load_message_stream(store)
        first = result[0]
        assert len(first.reactions) == 1
        assert first.reactions[0].name == "thumbsup"
        assert first.reactions[0].users == ["U002"]

    def test_preserves_thread_ts(
        self,
        sample_messages: list[dict[str, Any]],
    ) -> None:
        """Thread timestamps are preserved for reply messages."""
        store = _make_store(sample_messages)
        result = load_message_stream(store)
        second = result[1]
        assert second.thread_ts == "1711901000.000001"

    def test_empty_store(self) -> None:
        """Empty message list returns empty stream."""
        store = _make_store([])
        result = load_message_stream(store)
        assert result == []
