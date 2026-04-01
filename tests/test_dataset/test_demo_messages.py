"""Tests for the demo dataset (data/demo_messages.json).

Verifies the demo dataset has the correct structure, message count,
thread distribution, and persona coverage for the live demo.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from digest.dataset.schema import CHANNELS

_DEMO_PATH = Path(__file__).resolve().parents[2] / "data" / "demo_messages.json"


@pytest.fixture
def demo_data() -> dict:
    """Load the demo dataset."""
    return json.loads(_DEMO_PATH.read_text())


@pytest.fixture
def all_messages(demo_data: dict) -> list[dict]:
    """Flatten all messages from all channels."""
    msgs = []
    for ch in demo_data["channels"]:
        msgs.extend(ch["messages"])
    return msgs


class TestDemoDatasetStructure:
    """Tests for demo dataset structure and content."""

    def test_file_exists(self) -> None:
        """Demo dataset file must exist."""
        assert _DEMO_PATH.exists(), "data/demo_messages.json not found"

    def test_message_count_range(self, all_messages: list[dict]) -> None:
        """Demo dataset should have 15-20 messages."""
        count = len(all_messages)
        assert 15 <= count <= 20, f"Expected 15-20 messages, got {count}"

    def test_channels_are_valid(self, demo_data: dict) -> None:
        """All channels in demo data must be in the known channel list."""
        for ch in demo_data["channels"]:
            assert f"#{ch['name']}" in CHANNELS, f"Unknown channel: {ch['name']}"

    def test_at_least_3_threads(self, all_messages: list[dict]) -> None:
        """Demo dataset should have at least 3 distinct threads."""
        root_ts = set()
        for msg in all_messages:
            root = msg.get("thread_ts", msg["ts"])
            if root == msg["ts"]:
                root_ts.add(root)
        assert len(root_ts) >= 3, f"Expected >= 3 threads, got {len(root_ts)}"

    def test_every_message_has_required_fields(self, all_messages: list[dict]) -> None:
        """Every message must have ts, user, text, and type."""
        for msg in all_messages:
            assert "ts" in msg, f"Missing 'ts' in message: {msg}"
            assert "user" in msg, f"Missing 'user' in message: {msg}"
            assert "text" in msg, f"Missing 'text' in message: {msg}"
            assert "type" in msg, f"Missing 'type' in message: {msg}"


class TestDemoDatasetPersonaCoverage:
    """Tests that demo data covers all 3 persona workstreams."""

    def test_chassis_coverage(self, demo_data: dict) -> None:
        """At least one thread in chassis-design for Maya."""
        channels = [ch["name"] for ch in demo_data["channels"]]
        assert "chassis-design" in channels

    def test_supply_chain_mention(self, all_messages: list[dict]) -> None:
        """Supply chain implications mentioned for Elena."""
        texts = " ".join(m["text"] for m in all_messages).lower()
        assert any(
            term in texts for term in ["supply", "vendor", "lead time", "procurement", "die cast"]
        ), "No supply chain content for Elena"

    def test_manager_coverage(self, all_messages: list[dict]) -> None:
        """Cross-team blocker or action items for Ryan (U010)."""
        ryan_messages = [m for m in all_messages if m["user"] == "U010"]
        assert len(ryan_messages) >= 2, "Ryan (U010) should have >= 2 messages"


class TestDemoDatasetAtomTypes:
    """Tests that demo data contains signals for required atom types."""

    def test_decision_signal(self, all_messages: list[dict]) -> None:
        """At least one message contains a decision."""
        texts = " ".join(m["text"] for m in all_messages).lower()
        assert any(term in texts for term in ["decision", "agreed", "going with", "let's go"])

    def test_spec_change_signal(self, all_messages: list[dict]) -> None:
        """At least one message contains a spec change."""
        texts = " ".join(m["text"] for m in all_messages).lower()
        assert any(
            term in texts for term in ["spec change", "updated", "changed from", "requirement"]
        )

    def test_blocker_signal(self, all_messages: list[dict]) -> None:
        """At least one message contains a blocker."""
        texts = " ".join(m["text"] for m in all_messages).lower()
        assert any(term in texts for term in ["blocked", "block", "can't proceed", "waiting"])

    def test_action_item_signal(self, all_messages: list[dict]) -> None:
        """At least one message contains an action item."""
        texts = " ".join(m["text"] for m in all_messages).lower()
        assert any(
            term in texts for term in ["action item", "by friday", "by wednesday", "target"]
        )
