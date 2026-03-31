"""Slack message dataset loader for an AMR robotics team.

Loads messages from a static JSON fixture (data/slack_messages.json)
whose structure exactly matches the Slack Web API response shape
(conversations.history / conversations.replies) as of March 2026.

The fixture uses Slack API field names (ts, user, thread_ts, reactions
with count). This loader transforms those fields into the internal
SlackMessage model used by the ingestion layer.

Next Steps — Live Slack Connection:
    1. Add slack-sdk to pyproject.toml dependencies.
    2. Create a SlackIngestionClient wrapping slack_sdk.WebClient.
    3. Implement channel iteration using conversations_list().
    4. Paginate conversations_history() and conversations_replies()
       per channel/thread using cursor-based pagination.
    5. Add OAuth token management (bot token scope: channels:history,
       channels:read, reactions:read, users:read).
    6. Replace this file loader with the live client behind a common
       interface (both return list[SlackMessage]).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from evercurrent.dataset.schema import SlackMessage, SlackReaction

_FIXTURE_PATH = Path(__file__).resolve().parents[3] / "data" / "slack_messages.json"

_CACHED_MESSAGES: list[SlackMessage] | None = None


def _transform_message(raw: dict[str, Any], channel_name: str) -> SlackMessage:
    """Transform a single Slack API message dict into a SlackMessage.

    Maps Slack field names to internal model fields:
        - ts → message_ts
        - user → user_id
        - channel_name → channel (with # prefix)
        - thread_ts == ts (parent) → thread_ts = None
        - thread_ts absent (standalone) → thread_ts = None
        - thread_ts != ts (reply) → thread_ts preserved
        - reactions[].count → stripped (computed from len(users))

    Args:
        raw: Message dict with Slack API field names.
        channel_name: Channel name without # prefix.

    Returns:
        A SlackMessage instance with internal field names.
    """
    slack_thread_ts = raw.get("thread_ts")
    ts = raw["ts"]

    # Slack convention: parent has thread_ts == ts, standalone has no thread_ts.
    # Internal convention: both map to thread_ts = None.
    thread_ts = None if slack_thread_ts is None or slack_thread_ts == ts else slack_thread_ts

    reactions = [SlackReaction(name=r["name"], users=r["users"]) for r in raw.get("reactions", [])]

    return SlackMessage(
        message_ts=ts,
        thread_ts=thread_ts,
        channel=f"#{channel_name}",
        user_id=raw["user"],
        text=raw["text"],
        reactions=reactions,
    )


def _load_from_fixture() -> list[SlackMessage]:
    """Load all messages from the Slack-API-shaped JSON fixture.

    Reads data/slack_messages.json, iterates channels, transforms
    each message from Slack API fields to SlackMessage objects,
    and returns them sorted by message_ts.

    Returns:
        List of SlackMessage objects sorted by timestamp ascending.

    Raises:
        FileNotFoundError: If the fixture file is missing.
    """
    if not _FIXTURE_PATH.exists():
        msg = f"Slack fixture not found: {_FIXTURE_PATH}"
        raise FileNotFoundError(msg)

    data = json.loads(_FIXTURE_PATH.read_text())
    messages: list[SlackMessage] = []

    for channel in data["channels"]:
        channel_name = channel["name"]
        for raw_msg in channel["messages"]:
            messages.append(_transform_message(raw_msg, channel_name))

    return sorted(messages, key=lambda m: m.message_ts)


def load_messages() -> list[SlackMessage]:
    """Load the Slack message dataset from the static JSON fixture.

    Returns a cached copy of all messages, sorted by timestamp.
    Thread-safe for read-only access.

    Returns:
        List of SlackMessage objects.
    """
    global _CACHED_MESSAGES  # noqa: PLW0603
    if _CACHED_MESSAGES is None:
        _CACHED_MESSAGES = _load_from_fixture()
    return list(_CACHED_MESSAGES)
