"""Thread reconstruction Pass 2: detect implicit continuations.

Identifies top-level messages that continue earlier threads without
using Slack's reply mechanism. Uses a hybrid approach:
  - Fast-path (structural): @-mentions, quote blocks, back-references
  - Fallback (semantic): embedding cosine similarity above a threshold

Structural matches have confidence=1.0. Semantic matches carry the
cosine similarity score as confidence.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from digest.ingestion.embeddings import cosine_similarity

if TYPE_CHECKING:
    from digest.dataset.schema import SlackMessage
    from digest.ingestion.embeddings import Embedder
    from digest.ingestion.threads import ThreadBundle

logger = logging.getLogger(__name__)

_BACKREF_PATTERN = re.compile(
    r"(?:^re:\s*|following up on\s+(?:the\s+)?)",
    re.IGNORECASE,
)

_QUOTE_PATTERN = re.compile(r"^>\s*(.+)", re.MULTILINE)

_MENTION_PATTERN = re.compile(r"@(U\d+)")

_DEFAULT_SIMILARITY_THRESHOLD = 0.45


@dataclass
class ContinuationMatch:
    """A thread that has been linked to continuation messages.

    Attributes:
        root_message: The root of the original thread.
        continuations: Messages linked as implicit continuations.
        confidence: Match confidence. 1.0 for structural (regex) matches,
            cosine similarity score for semantic matches.
    """

    root_message: SlackMessage
    continuations: list[SlackMessage] = field(default_factory=list)
    confidence: float = 1.0


# ── Structural (keyword) detectors ──────────────────────────────────


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
    after = msg.text[match.end() :].lower().split("-")[0].split(".")[0].strip()
    if not after:
        return False
    thread_text = _get_thread_text(bundle)
    words = after.split()
    return any(w in thread_text for w in words if len(w) > 3)


def _structural_match(msg: SlackMessage, bundle: ThreadBundle) -> bool:
    """Return True if any structural (regex/keyword) signal fires."""
    return (
        _check_at_mention(msg, bundle)
        or _check_quote_block(msg, bundle)
        or _check_back_reference(msg, bundle)
    )


# ── Semantic (embedding) matching ───────────────────────────────────


def _find_best_bundle(
    msg: SlackMessage,
    bundles: list[ThreadBundle],
    standalone_vec: list[float],
    thread_vecs: list[list[float]],
) -> tuple[ThreadBundle | None, float]:
    """Find the same-channel bundle with highest cosine similarity.

    Args:
        msg: The standalone message to match.
        bundles: All thread bundles.
        standalone_vec: Embedding vector for the standalone message.
        thread_vecs: Pre-computed embedding vectors for each bundle.

    Returns:
        (best_bundle, best_score) or (None, -1.0) if no same-channel bundle.
    """
    best_score = -1.0
    best_bundle: ThreadBundle | None = None
    for bi, bundle in enumerate(bundles):
        if msg.channel != bundle.root_message.channel:
            continue
        score = cosine_similarity(standalone_vec, thread_vecs[bi])
        if score > best_score:
            best_score = score
            best_bundle = bundle
    return best_bundle, best_score


def _semantic_match(
    unmatched: list[SlackMessage],
    bundles: list[ThreadBundle],
    embedder: Embedder,
    threshold: float,
    matches: dict[str, ContinuationMatch],
) -> None:
    """Link remaining standalones to bundles via embedding similarity.

    Pre-computes one embedding per thread and one per standalone,
    then finds the best same-channel match for each standalone.
    Only mutates *matches* when similarity >= *threshold*.

    Args:
        unmatched: Standalone messages not matched by structural checks.
        bundles: All thread bundles.
        embedder: Text embedding provider.
        threshold: Minimum cosine similarity to create a link.
        matches: Mutable dict of existing ContinuationMatch objects
            keyed by root message_ts. Updated in place.
    """
    if not unmatched or not bundles:
        return

    thread_texts = [_get_thread_text(b) for b in bundles]
    standalone_texts = [m.text.lower() for m in unmatched]

    all_vecs = embedder.embed(thread_texts + standalone_texts)
    thread_vecs = all_vecs[: len(bundles)]
    standalone_vecs = all_vecs[len(bundles) :]

    for si, msg in enumerate(unmatched):
        best_bundle, best_score = _find_best_bundle(
            msg,
            bundles,
            standalone_vecs[si],
            thread_vecs,
        )
        if best_bundle is None or best_score < threshold:
            continue
        key = best_bundle.root_message.message_ts
        if key not in matches:
            matches[key] = ContinuationMatch(
                root_message=best_bundle.root_message,
                confidence=best_score,
            )
        matches[key].continuations.append(msg)
        if best_score < matches[key].confidence:
            matches[key].confidence = best_score
        logger.debug("Semantic match: %s → %s (%.3f)", msg.message_ts, key, best_score)


# ── Public API ──────────────────────────────────────────────────────


def detect_continuations(
    bundles: list[ThreadBundle],
    standalones: list[SlackMessage],
    embedder: Embedder | None = None,
    similarity_threshold: float = _DEFAULT_SIMILARITY_THRESHOLD,
) -> list[ContinuationMatch]:
    """Detect which standalone messages implicitly continue existing threads.

    Uses a hybrid approach: structural (regex) detectors run first as a
    fast-path. If an embedder is provided, unmatched standalones are then
    compared to thread embeddings via cosine similarity.

    Args:
        bundles: ThreadBundles from Pass 1.
        standalones: Top-level messages not yet assigned to a thread.
        embedder: Optional text embedding provider for semantic matching.
        similarity_threshold: Minimum cosine similarity for semantic links.

    Returns:
        List of ContinuationMatch objects for bundles that have
        at least one continuation. Structural matches have
        confidence=1.0; semantic matches carry the similarity score.
    """
    if not bundles or not standalones:
        return []

    matches: dict[str, ContinuationMatch] = {}
    unmatched: list[SlackMessage] = []

    # Fast-path: structural (keyword/regex) matching.
    for msg in standalones:
        matched = False
        for bundle in bundles:
            if _structural_match(msg, bundle):
                key = bundle.root_message.message_ts
                if key not in matches:
                    matches[key] = ContinuationMatch(
                        root_message=bundle.root_message,
                    )
                matches[key].continuations.append(msg)
                matched = True
                break
        if not matched:
            unmatched.append(msg)

    # Fallback: semantic (embedding) matching for remaining standalones.
    if embedder is not None and unmatched:
        _semantic_match(unmatched, bundles, embedder, similarity_threshold, matches)

    return list(matches.values())
