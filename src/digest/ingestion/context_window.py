"""Context window assembly with long-thread compression.

Assembles ThreadBundles into ContextWindow objects for Layer 2.
Short threads are included in full; long threads are compressed to
root + most-reacted messages + final 5 messages.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel

from digest.config.loader import get_config

if TYPE_CHECKING:
    from digest.ingestion.threads import ThreadBundle

_cw_cfg = get_config()["pipeline"]["context_window"]
_DEFAULT_MAX_TOKENS = _cw_cfg["max_tokens"]
_TAIL_COUNT = _cw_cfg["tail_count"]
_CHARS_PER_TOKEN = _cw_cfg["chars_per_token"]


class ContextWindow(BaseModel):
    """Assembled context for a single thread, ready for extraction.

    Attributes:
        thread_text: The assembled text content of the thread.
        channel: The channel the thread belongs to.
        thread_ts: The root message timestamp.
        message_range: Tuple of (first_ts, last_ts) for source anchoring.
        compressed: Whether the thread was compressed to fit.
    """

    thread_text: str
    channel: str
    thread_ts: str
    message_range: tuple[str, str]
    compressed: bool


def _format_message(user_id: str, text: str) -> str:
    """Format a single message for the context window."""
    return f"[{user_id}] {text}"


def _estimate_tokens(text: str) -> int:
    """Rough token estimate: ~4 chars per token."""
    return len(text) // _CHARS_PER_TOKEN


def _assemble_full(bundle: ThreadBundle) -> ContextWindow:
    """Assemble a short thread without compression."""
    all_msgs = [bundle.root_message, *bundle.replies]
    lines = [_format_message(m.user_id, m.text) for m in all_msgs]
    thread_text = "\n".join(lines)

    timestamps = [m.message_ts for m in all_msgs]
    return ContextWindow(
        thread_text=thread_text,
        channel=bundle.root_message.channel,
        thread_ts=bundle.root_message.message_ts,
        message_range=(min(timestamps), max(timestamps)),
        compressed=False,
    )


def _assemble_compressed(bundle: ThreadBundle) -> ContextWindow:
    """Assemble a long thread with compression.

    Strategy: root message + most-reacted messages + final 5 messages.
    This preserves the narrative arc (opening problem + key reactions +
    resolution).
    """
    all_msgs = [bundle.root_message, *bundle.replies]
    root = bundle.root_message

    replies_by_reactions = sorted(
        bundle.replies,
        key=lambda m: sum(len(r.users) for r in m.reactions),
        reverse=True,
    )
    top_reacted = replies_by_reactions[:3] if replies_by_reactions else []

    tail = bundle.replies[-_TAIL_COUNT:] if len(bundle.replies) >= _TAIL_COUNT else bundle.replies

    selected_ts = {root.message_ts}
    selected = [root]
    for m in top_reacted:
        if m.message_ts not in selected_ts:
            selected_ts.add(m.message_ts)
            selected.append(m)
    for m in tail:
        if m.message_ts not in selected_ts:
            selected_ts.add(m.message_ts)
            selected.append(m)

    selected.sort(key=lambda m: m.message_ts)
    lines = [_format_message(m.user_id, m.text) for m in selected]
    thread_text = "\n".join(lines)

    timestamps = [m.message_ts for m in all_msgs]
    return ContextWindow(
        thread_text=thread_text,
        channel=bundle.root_message.channel,
        thread_ts=bundle.root_message.message_ts,
        message_range=(min(timestamps), max(timestamps)),
        compressed=True,
    )


def assemble_context_windows(
    bundles: list[ThreadBundle],
    max_tokens: int = _DEFAULT_MAX_TOKENS,
) -> list[ContextWindow]:
    """Assemble ContextWindows from ThreadBundles.

    Args:
        bundles: List of ThreadBundle objects from Pass 1/2.
        max_tokens: Maximum estimated tokens per context window.

    Returns:
        List of ContextWindow objects, one per bundle.
    """
    windows: list[ContextWindow] = []
    for bundle in bundles:
        full = _assemble_full(bundle)
        if _estimate_tokens(full.thread_text) <= max_tokens:
            windows.append(full)
        else:
            windows.append(_assemble_compressed(bundle))
    return windows
