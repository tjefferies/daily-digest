"""Pipeline orchestrator: wires Ingestion → Extraction → Filter → Validation.

Runs the full extraction pipeline from synthetic data through LLM
extraction, confidence filtering, and two-pass validation. Returns
a PipelineResult containing validated atoms ready for scoring.
Provides both sync (run_pipeline) and async (async_run_pipeline) variants.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from anthropic import Anthropic

from evercurrent.config.loader import get_config
from evercurrent.dataset.messages import load_messages
from evercurrent.extraction.batch_runner import BatchExtractionRunner
from evercurrent.extraction.filter import confidence_filter
from evercurrent.extraction.runner import ExtractionRunner
from evercurrent.extraction.validation import async_validate_atoms, validate_atoms
from evercurrent.graph.client import GraphClient
from evercurrent.ingestion.cached_embedder import CachedEmbedder
from evercurrent.ingestion.context_window import assemble_context_windows
from evercurrent.ingestion.continuations import detect_continuations
from evercurrent.ingestion.threads import group_by_thread
from evercurrent.ingestion.vectorstore import VectorStore

if TYPE_CHECKING:
    from evercurrent.ingestion.embeddings import Embedder
    from evercurrent.llm.types import AsyncLLMClient, LLMClient
    from evercurrent.models.atom import Atom

logger = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    """Result of a full extraction pipeline run.

    Attributes:
        atoms: Validated atoms that passed confidence filtering.
        stats: Processing statistics from the pipeline run.
    """

    atoms: list[Atom] = field(default_factory=list)
    stats: dict[str, Any] = field(default_factory=dict)


def _extract_standalones(
    messages: list[Any],
    bundles: list[Any],
) -> list[Any]:
    """Identify top-level messages not assigned to any thread bundle.

    Args:
        messages: All loaded SlackMessage objects.
        bundles: ThreadBundles from Pass 1 structural grouping.

    Returns:
        Messages that have no thread_ts and whose message_ts is not a
        bundle root (i.e. truly standalone top-level messages).
    """
    bundle_roots = {b.root_message.message_ts for b in bundles}
    return [m for m in messages if m.thread_ts is None and m.message_ts not in bundle_roots]


def _merge_continuations(
    bundles: list[Any],
    continuation_matches: list[Any],
) -> int:
    """Merge continuation messages back into their matched thread bundles.

    Args:
        bundles: ThreadBundles to merge into (mutated in place).
        continuation_matches: ContinuationMatch objects from detect_continuations.

    Returns:
        Total number of continuation messages merged.
    """
    match_map = {m.root_message.message_ts: m for m in continuation_matches}
    merged = 0
    for bundle in bundles:
        match = match_map.get(bundle.root_message.message_ts)
        if match:
            bundle.replies.extend(match.continuations)
            merged += len(match.continuations)
    return merged


def run_pipeline(
    client: LLMClient,
    embedder: Embedder | None = None,
) -> PipelineResult:
    """Run the full extraction pipeline: Ingestion → Extraction → Filter → Validation.

    Args:
        client: LLMClient-compatible adapter for LLM API calls.
        embedder: Optional text embedder for semantic continuation detection.

    Returns:
        PipelineResult with validated, filtered atoms and processing stats.
    """
    # Layer 1: Ingestion
    messages = load_messages()
    bundles = group_by_thread(messages)

    # Pass 2: Continuation detection (hybrid keyword + semantic)
    standalones = _extract_standalones(messages, bundles)
    continuation_matches = detect_continuations(bundles, standalones, embedder=embedder)
    continuations_merged = _merge_continuations(bundles, continuation_matches)

    windows = assemble_context_windows(bundles)
    logger.info(
        "Ingestion: %d messages → %d threads (%d continuations) → %d windows",
        len(messages),
        len(bundles),
        continuations_merged,
        len(windows),
    )

    # Layer 2: Extraction
    runner = ExtractionRunner(client)
    raw_atoms = runner.extract(windows)
    logger.info("Extraction: %d raw atoms from %d windows", len(raw_atoms), len(windows))

    # Validation (two-pass for DECISION/SPEC_CHANGE)
    validated = raw_atoms
    for window in windows:
        validated = validate_atoms(validated, client, window.thread_text)

    # Confidence filter
    filter_result = confidence_filter(validated)
    atoms = filter_result.passed
    logger.info(
        "Filter: %d passed, %d filtered",
        filter_result.passed_count,
        filter_result.filtered_count,
    )

    return PipelineResult(
        atoms=atoms,
        stats={
            "messages_loaded": len(messages),
            "threads_found": len(bundles),
            "standalones_found": len(standalones),
            "continuations_merged": continuations_merged,
            "context_windows": len(windows),
            "atoms_extracted": len(raw_atoms),
            "atoms_after_filter": len(atoms),
        },
    )


def _get_vectorstore_path() -> Path:
    """Get the vectorstore file path from pipeline config.

    Returns:
        Path to the FAISS index file.
    """
    cfg = get_config()["pipeline"]
    return Path(cfg.get("vectorstore", {}).get("path", "data/vectorstore.index"))


def _wrap_with_cache(embedder: Embedder | None) -> Embedder | None:
    """Wrap an embedder with FAISS caching if provided.

    Args:
        embedder: Optional inner embedder to wrap.

    Returns:
        CachedEmbedder wrapping the inner embedder, or None.
    """
    if embedder is None:
        return None
    store = VectorStore.load(_get_vectorstore_path())
    return CachedEmbedder(embedder, store)


def _save_vectorstore(cached: CachedEmbedder) -> None:
    """Save the vectorstore to disk after use.

    Args:
        cached: CachedEmbedder whose store should be persisted.
    """
    try:
        cached._store.save(_get_vectorstore_path())  # noqa: SLF001
    except Exception:
        logger.warning("Failed to save vectorstore", exc_info=True)


def _create_graph_client() -> GraphClient:
    """Create a GraphClient from pipeline config.

    Returns:
        GraphClient configured from pipeline.yml neo4j settings.
    """
    neo4j_cfg = get_config()["pipeline"]["neo4j"]
    return GraphClient(
        uri=neo4j_cfg["uri"],
        user=neo4j_cfg["user"],
        password=neo4j_cfg["password"],
    )


async def _get_processed_threads(graph: GraphClient) -> set[str]:
    """Query Neo4j for already-processed thread_ts values.

    Args:
        graph: Active GraphClient instance.

    Returns:
        Set of thread_ts strings, empty on failure.
    """
    try:
        return await graph.processed_thread_ts()
    except Exception:
        logger.warning("Neo4j dedup query failed, processing all threads", exc_info=True)
        return set()


async def _persist_to_neo4j(graph: GraphClient, atoms: list[Atom]) -> None:
    """Persist atoms to Neo4j, logging errors without raising.

    Args:
        graph: Active GraphClient instance.
        atoms: Validated atoms to persist.
    """
    try:
        await graph.ensure_schema()
        await graph.persist_atoms(atoms)
    except Exception:
        logger.warning("Neo4j persistence failed, atoms not stored", exc_info=True)


async def async_run_pipeline(
    client: AsyncLLMClient,
    embedder: Embedder | None = None,
    batch_runner: BatchExtractionRunner | None = None,
) -> PipelineResult:
    """Run the full extraction pipeline asynchronously with concurrent LLM calls.

    Uses BatchExtractionRunner for batched LLM calls (50% cost savings).
    Queries Neo4j to skip already-processed threads and persists new
    atoms after filtering.

    Args:
        client: AsyncLLMClient-compatible adapter for async LLM API calls.
        embedder: Optional text embedder for semantic continuation detection.
        batch_runner: Optional pre-created BatchExtractionRunner for
            progress tracking. If None, one is created internally.

    Returns:
        PipelineResult with validated, filtered atoms and processing stats.
    """
    graph = _create_graph_client()
    try:
        return await _async_run_pipeline_inner(client, embedder, graph, batch_runner)
    finally:
        await graph.close()


async def _async_run_pipeline_inner(
    client: AsyncLLMClient,
    embedder: Embedder | None,
    graph: GraphClient,
    batch_runner: BatchExtractionRunner | None = None,
) -> PipelineResult:
    """Inner pipeline logic with a shared GraphClient.

    Args:
        client: AsyncLLMClient-compatible adapter for async LLM API calls.
        embedder: Optional text embedder for semantic continuation detection.
        graph: Active GraphClient for dedup queries and persistence.
        batch_runner: Optional pre-created BatchExtractionRunner.

    Returns:
        PipelineResult with validated, filtered atoms and processing stats.
    """
    # Layer 1: Ingestion (CPU-bound, no async needed)
    messages = load_messages()
    bundles = group_by_thread(messages)

    # Pass 2: Continuation detection (hybrid keyword + semantic)
    # Wrap embedder with FAISS cache if provided
    cached_embedder = _wrap_with_cache(embedder)
    standalones = _extract_standalones(messages, bundles)
    continuation_matches = detect_continuations(
        bundles,
        standalones,
        embedder=cached_embedder,
    )
    continuations_merged = _merge_continuations(bundles, continuation_matches)
    # Save vectorstore after continuation detection
    if isinstance(cached_embedder, CachedEmbedder):
        _save_vectorstore(cached_embedder)

    # Dedup: skip threads already processed in Neo4j
    processed = await _get_processed_threads(graph)
    total_bundles = len(bundles)
    if processed:
        bundles = [b for b in bundles if b.root_message.message_ts not in processed]
    threads_skipped = total_bundles - len(bundles)
    if threads_skipped:
        logger.info("Dedup: skipped %d already-processed threads", threads_skipped)

    windows = assemble_context_windows(bundles)
    max_windows = get_config()["pipeline"].get("max_windows", 0)
    if max_windows > 0 and len(windows) > max_windows:
        logger.info("Capping windows: %d → %d", len(windows), max_windows)
        windows = windows[:max_windows]
    logger.info(
        "Ingestion: %d messages → %d threads (%d skipped, %d continuations) → %d windows",
        len(messages),
        total_bundles,
        threads_skipped,
        continuations_merged,
        len(windows),
    )

    # Layer 2: Extraction (batch API for 50% cost savings, no rate limits)
    if batch_runner is None:
        batch_runner = BatchExtractionRunner(Anthropic())
    raw_atoms = await batch_runner.extract(windows)
    logger.info("Extraction: %d raw atoms from %d windows", len(raw_atoms), len(windows))

    # Validation (concurrent LLM calls for DECISION/SPEC_CHANGE)
    validated = raw_atoms
    for window in windows:
        validated = await async_validate_atoms(validated, client, window.thread_text)

    # Confidence filter (CPU-bound)
    filter_result = confidence_filter(validated)
    atoms = filter_result.passed
    logger.info(
        "Filter: %d passed, %d filtered",
        filter_result.passed_count,
        filter_result.filtered_count,
    )

    # Persist to Neo4j (graceful degradation if unavailable)
    await _persist_to_neo4j(graph, atoms)

    return PipelineResult(
        atoms=atoms,
        stats={
            "messages_loaded": len(messages),
            "threads_found": total_bundles,
            "threads_skipped": threads_skipped,
            "standalones_found": len(standalones),
            "continuations_merged": continuations_merged,
            "context_windows": len(windows),
            "atoms_extracted": len(raw_atoms),
            "atoms_after_filter": len(atoms),
        },
    )
