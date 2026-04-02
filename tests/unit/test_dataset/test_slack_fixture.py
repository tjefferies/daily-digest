"""Tests for the Slack-API-shaped JSON fixture and loader.

Validates that data/slack_messages.json uses exact Slack Web API field
names and structure (conversations.history / conversations.replies),
and that the loader correctly transforms Slack fields to SlackMessage.
"""

from __future__ import annotations

import json
from pathlib import Path

from digest.dataset.messages import load_messages
from digest.dataset.schema import CHANNELS

_FIXTURE_PATH = Path(__file__).resolve().parents[3] / "data" / "slack_messages.json"


class TestFixtureFileStructure:
    """Tests that the JSON fixture uses Slack API response shape."""

    def test_fixture_file_exists(self) -> None:
        """The Slack messages fixture file exists."""
        assert _FIXTURE_PATH.exists(), f"Missing fixture: {_FIXTURE_PATH}"

    def test_fixture_is_valid_json(self) -> None:
        """The fixture file contains valid JSON."""
        data = json.loads(_FIXTURE_PATH.read_text())
        assert isinstance(data, dict)

    def test_fixture_has_channels_key(self) -> None:
        """Top-level structure has 'channels' array."""
        data = json.loads(_FIXTURE_PATH.read_text())
        assert "channels" in data
        assert isinstance(data["channels"], list)

    def test_each_channel_has_id_name_messages(self) -> None:
        """Each channel entry has id, name, and messages fields."""
        data = json.loads(_FIXTURE_PATH.read_text())
        for ch in data["channels"]:
            assert "id" in ch, "Channel missing 'id'"
            assert "name" in ch, "Channel missing 'name'"
            assert "messages" in ch, "Channel missing 'messages'"
            assert isinstance(ch["messages"], list)

    def test_all_eight_channels_present(self) -> None:
        """Fixture contains all 8 expected channels."""
        data = json.loads(_FIXTURE_PATH.read_text())
        names = {f"#{ch['name']}" for ch in data["channels"]}
        for channel in CHANNELS:
            assert channel in names, f"Missing channel: {channel}"


class TestSlackMessageFields:
    """Tests that individual messages use Slack API field names."""

    def _all_messages(self) -> list[dict]:
        """Load all messages from all channels."""
        data = json.loads(_FIXTURE_PATH.read_text())
        msgs = []
        for ch in data["channels"]:
            msgs.extend(ch["messages"])
        return msgs

    def test_messages_have_type_field(self) -> None:
        """Every message has a 'type' field set to 'message'."""
        for msg in self._all_messages():
            assert msg.get("type") == "message"

    def test_messages_have_ts_field(self) -> None:
        """Every message has a 'ts' field (Slack timestamp)."""
        for msg in self._all_messages():
            assert "ts" in msg

    def test_messages_have_user_field(self) -> None:
        """Every message has a 'user' field (not user_id)."""
        for msg in self._all_messages():
            assert "user" in msg
            assert "user_id" not in msg

    def test_messages_have_text_field(self) -> None:
        """Every message has a 'text' field."""
        for msg in self._all_messages():
            assert "text" in msg

    def test_no_message_ts_field(self) -> None:
        """Messages use 'ts' not 'message_ts' (Slack API convention)."""
        for msg in self._all_messages():
            assert "message_ts" not in msg


class TestSlackThreadStructure:
    """Tests for Slack API thread conventions."""

    def _all_messages(self) -> list[dict]:
        data = json.loads(_FIXTURE_PATH.read_text())
        msgs = []
        for ch in data["channels"]:
            msgs.extend(ch["messages"])
        return msgs

    def test_thread_parents_have_thread_ts_equal_ts(self) -> None:
        """Thread parents have thread_ts == ts (Slack API convention)."""
        msgs = self._all_messages()
        parents = [m for m in msgs if m.get("reply_count")]
        assert len(parents) > 0, "No thread parents found"
        for p in parents:
            assert p["thread_ts"] == p["ts"]

    def test_thread_parents_have_reply_metadata(self) -> None:
        """Thread parents include reply_count, reply_users_count."""
        msgs = self._all_messages()
        parents = [m for m in msgs if m.get("reply_count")]
        for p in parents:
            assert "reply_count" in p
            assert "reply_users_count" in p
            assert "reply_users" in p
            assert "latest_reply" in p

    def test_thread_replies_have_thread_ts_not_equal_ts(self) -> None:
        """Thread replies have thread_ts != ts (pointing to parent)."""
        msgs = self._all_messages()
        replies = [m for m in msgs if "thread_ts" in m and m["thread_ts"] != m["ts"]]
        assert len(replies) > 0, "No thread replies found"
        for r in replies:
            assert r["thread_ts"] != r["ts"]

    def test_standalone_messages_have_no_thread_ts(self) -> None:
        """Standalone messages have no thread_ts field."""
        msgs = self._all_messages()
        standalone = [m for m in msgs if "thread_ts" not in m]
        assert len(standalone) > 0, "No standalone messages found"


class TestSlackReactionFormat:
    """Tests for Slack API reaction structure."""

    def test_reactions_have_count_field(self) -> None:
        """Reactions include the 'count' field (Slack API convention)."""
        data = json.loads(_FIXTURE_PATH.read_text())
        found_reactions = False
        for ch in data["channels"]:
            for msg in ch["messages"]:
                if "reactions" in msg:
                    found_reactions = True
                    for reaction in msg["reactions"]:
                        assert "name" in reaction
                        assert "users" in reaction
                        assert "count" in reaction
                        assert reaction["count"] == len(reaction["users"])
        assert found_reactions, "No reactions found in fixture"


class TestLoaderTransformation:
    """Tests that load_messages() correctly transforms Slack API fields."""

    def test_load_messages_returns_slack_message_objects(self) -> None:
        """load_messages() returns SlackMessage objects, not raw dicts."""
        from digest.dataset.schema import SlackMessage

        messages = load_messages()
        assert len(messages) > 0
        for m in messages:
            assert isinstance(m, SlackMessage)

    def test_ts_mapped_to_message_ts(self) -> None:
        """Slack 'ts' field mapped to SlackMessage 'message_ts'."""
        messages = load_messages()
        for m in messages:
            assert m.message_ts

    def test_user_mapped_to_user_id(self) -> None:
        """Slack 'user' field mapped to SlackMessage 'user_id'."""
        messages = load_messages()
        for m in messages:
            assert m.user_id

    def test_channel_populated_from_grouping(self) -> None:
        """SlackMessage 'channel' comes from the channel grouping."""
        messages = load_messages()
        for m in messages:
            assert m.channel.startswith("#")

    def test_thread_parent_thread_ts_mapped_to_none(self) -> None:
        """Thread parents (thread_ts == ts in Slack) get thread_ts=None."""
        messages = load_messages()
        top_level = [m for m in messages if m.thread_ts is None]
        assert len(top_level) >= 20

    def test_thread_reply_thread_ts_preserved(self) -> None:
        """Thread replies keep their thread_ts pointing to parent."""
        messages = load_messages()
        replies = [m for m in messages if m.thread_ts is not None]
        assert len(replies) >= 50
        for r in replies:
            assert r.thread_ts != r.message_ts

    def test_reactions_count_stripped(self) -> None:
        """SlackReaction objects don't include the count field."""
        messages = load_messages()
        with_reactions = [m for m in messages if m.reactions]
        assert len(with_reactions) > 0
        for m in with_reactions:
            for r in m.reactions:
                assert not hasattr(r, "count") or "count" not in r.model_fields
