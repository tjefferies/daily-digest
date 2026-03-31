"""Thread reconstruction Pass 2: detect implicit continuations.

Identifies top-level messages that continue earlier threads without
using Slack's reply mechanism. Detection signals:
  (a) @-mention of a recent thread participant
  (b) Quote block matching earlier message text
  (c) Explicit back-reference ('re:', 'following up on')
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from evercurrent.dataset.schema import SlackMessage
    from evercurrent.ingestion.threads import ThreadBundle

_BACKREF_PATTERN = re.compile(
    r"(?:^re:\s*|following up on\s+(?:the\s+)?)",
    re.IGNORECASE,
)

_QUOTE_PATTERN = re.compile(r"^>\s*(.+)", re.MULTILINE)

_MENTION_PATTERN = re.compile(r"@(U\d+)")


@dataclass
class ContinuationMatch:
    """A thread that has been linked to continuation messages.

    Attributes:
        root_message: The root of the original thread.
        continuations: Messages linked as implicit continuations.
    """

    root_message: SlackMessage
    continuations: list[SlackMessage] = field(default_factory=list)


def _get_thread_participants(bundle: ThreadBundle) -> set[str]:
    """Get all user_ids that participated in a thread."""
    participants = {bundle.root_message.user_id}
    for reply in bundle.replies:
        participants.add(reply.user_id)
    return participants


def _get_thread_text(bundle: ThreadBundle) -> str:
    """Get all text in a thread as one lowercase string."""
    parts = [bundle.root_message.text.lower()]
    for reply in bundle.replies:
        parts.append(reply.text.lower())
    return " ".join(parts)


def _check_at_mention(
    msg: SlackMessage,
    bundle: ThreadBundle,
) -> bool:
    """Check if msg @-mentions a participant of the bundle's thread."""
    if msg.channel != bundle.root_message.channel:
        return False
    mentions = _MENTION_PATTERN.findall(msg.text)
    participants = _get_thread_participants(bundle)
    return bool(set(mentions) & participants)


def _check_quote_block(
    msg: SlackMessage,
    bundle: ThreadBundle,
) -> bool:
    """Check if msg contains a quote matching text in the bundle."""
    if msg.channel != bundle.root_message.channel:
        return False
    quotes = _QUOTE_PATTERN.findall(msg.text)
    if not quotes:
        return False
    thread_text = _get_thread_text(bundle)
    return any(q.strip().lower() in thread_text for q in quotes)


def _check_back_reference(
    msg: SlackMessage,
    bundle: ThreadBundle,
) -> bool:
    """Check if msg has an explicit back-reference to the bundle's topic."""
    if msg.channel != bundle.root_message.channel:
        return False
    match = _BACKREF_PATTERN.search(msg.text)
    if not match:
        return False
    after = msg.text[match.end() :].lower().split("—")[0].split(".")[0].strip()
    if not after:
        return False
    thread_text = _get_thread_text(bundle)
    words = after.split()
    return any(w in thread_text for w in words if len(w) > 3)


def detect_continuations(
    bundles: list[ThreadBundle],
    standalones: list[SlackMessage],
) -> list[ContinuationMatch]:
    """Detect which standalone messages implicitly continue existing threads.

    Args:
        bundles: ThreadBundles from Pass 1.
        standalones: Top-level messages not yet assigned to a thread.

    Returns:
        List of ContinuationMatch objects for bundles that have
        at least one continuation. Each standalone is matched to
        at most one bundle (first match wins).
    """
    if not bundles or not standalones:
        return []

    matches: dict[str, ContinuationMatch] = {}

    for msg in standalones:
        for bundle in bundles:
            if (
                _check_at_mention(msg, bundle)
                or _check_quote_block(msg, bundle)
                or _check_back_reference(msg, bundle)
            ):
                key = bundle.root_message.message_ts
                if key not in matches:
                    matches[key] = ContinuationMatch(
                        root_message=bundle.root_message,
                    )
                matches[key].continuations.append(msg)
                break

    return list(matches.values())
