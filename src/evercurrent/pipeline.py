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
from evercurrent.db.repository import (
    get_processed_bundle_ts,
    persist_atoms,
    persist_bundle,
    persist_context_windows,
)
from evercurrent.db.session import get_session_factory
from evercurrent.extraction.batch_runner import BatchExtractionRunner
from evercurrent.extraction.filter import confidence_filter
from evercurrent.extraction.runner import AsyncExtractionRunner
from evercurrent.extraction.validation import async_validate_atoms_batch
from evercurrent.graph.client import GraphClient
from evercurrent.ingestion.cached_embedder import CachedEmbedder
from evercurrent.ingestion.context_window import assemble_context_windows
from evercurrent.ingestion.continuations import detect_continuations
from evercurrent.ingestion.threads import group_by_thread
from evercurrent.ingestion.vectorstore import VectorStore

if TYPE_CHECKING:
    from evercurrent.ingestion.embeddings import Embedder
    from evercurrent.llm.types import AsyncLLMClient
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


async def _postgres_dedup(bundles: list) -> tuple[list, int]:
    """Filter out bundles already in Postgres.

    Args:
        bundles: All ThreadBundles from ingestion.

    Returns:
        Tuple of (filtered bundles, count skipped).
    """
    total = len(bundles)
    try:
        factory = get_session_factory()
        async with factory() as session:
            processed = await get_processed_bundle_ts(session)
        if processed:
            bundles = [b for b in bundles if b.root_message.message_ts not in processed]
        skipped = total - len(bundles)
        if skipped:
            logger.info("Postgres dedup: skipped %d unchanged bundles", skipped)
        return bundles, skipped
    except Exception:
        logger.warning("Postgres dedup failed, processing all bundles", exc_info=True)
        return bundles, 0


async def _postgres_persist_bundles(bundles: list) -> None:
    """Persist bundles to Postgres before extraction.

    Args:
        bundles: ThreadBundles to persist.
    """
    try:
        factory = get_session_factory()
        async with factory() as session:
            for bundle in bundles:
                await persist_bundle(session, bundle)
            await session.commit()
        logger.info("Postgres: persisted %d bundles", len(bundles))
    except Exception:
        logger.warning("Postgres bundle persistence failed", exc_info=True)


async def _postgres_persist_context_windows(windows: list) -> None:
    """Persist context windows to Postgres.

    Args:
        windows: Assembled context windows.
    """
    try:
        factory = get_session_factory()
        async with factory() as session:
            await persist_context_windows(session, windows)
            await session.commit()
        logger.info("Postgres: persisted %d context windows", len(windows))
    except Exception:
        logger.warning("Postgres context window persistence failed", exc_info=True)


async def _postgres_persist_atoms(atoms: list[Atom]) -> None:
    """Persist atoms to Postgres after filtering.

    Args:
        atoms: Filtered atoms to persist.
    """
    try:
        factory = get_session_factory()
        async with factory() as session:
            await persist_atoms(session, atoms)
            await session.commit()
        logger.info("Postgres: persisted %d atoms", len(atoms))
    except Exception:
        logger.warning("Postgres atom persistence failed", exc_info=True)


def _dump_intermediate(filename: str, data: list) -> None:
    """Write intermediate pipeline results to a JSON file.

    Args:
        filename: Output filename in data/ directory.
        data: List of dicts/models to serialize.
    """
    import json

    outpath = Path("/tmp") / "evercurrent" / filename  # noqa: S108
    outpath.parent.mkdir(parents=True, exist_ok=True)
    serialized = [d.model_dump(mode="json") if hasattr(d, "model_dump") else d for d in data]
    outpath.write_text(json.dumps(serialized, indent=2, default=str))
    logger.info("Wrote %d items → %s", len(serialized), outpath)


async def _validate_atoms_by_source(
    raw_atoms: list[Atom],
    windows: list,
    client: AsyncLLMClient,  # noqa: ARG001
) -> list[Atom]:
    """Validate all atoms in a single batch, each against its own source window.

    Args:
        raw_atoms: All extracted atoms.
        windows: Context windows for source text lookup.
        client: Unused (kept for interface compat).

    Returns:
        Validated atom list with demoted confidence for invalid atoms.
    """
    window_text_by_ts = {w.thread_ts: w.thread_text for w in windows}

    # Collect ALL (atom, context) pairs for one batch
    atoms_with_context: list[tuple[int, Atom, str]] = []
    for i, atom in enumerate(raw_atoms):
        if atom.type in {"DECISION", "SPEC_CHANGE"}:
            context = window_text_by_ts.get(atom.source.thread_ts, "")
            if context:
                atoms_with_context.append((i, atom, context))

    logger.info(
        "Validation: %d atoms total, %d DECISION/SPEC_CHANGE → 1 batch",
        len(raw_atoms),
        len(atoms_with_context),
    )

    if not atoms_with_context:
        return raw_atoms

    validated = await async_validate_atoms_batch(atoms_with_context, raw_atoms)

    demoted = sum(1 for a in validated if a.confidence < 0.5)
    logger.info("Validation done: %d atoms, %d demoted", len(validated), demoted)
    return validated


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

    # Dedup: skip bundles already in Postgres (delta processing)
    total_bundles = len(bundles)
    bundles, threads_skipped = await _postgres_dedup(bundles)

    # Persist new bundles to Postgres BEFORE extraction
    # so delta dedup works even if extraction fails partway through
    await _postgres_persist_bundles(bundles)

    windows = assemble_context_windows(bundles)
    max_windows = get_config()["pipeline"].get("max_windows", 0)
    if max_windows > 0 and len(windows) > max_windows:
        logger.info("Capping windows: %d → %d", len(windows), max_windows)
        windows = windows[:max_windows]

    # Persist context windows to Postgres (what the LLM will see)
    await _postgres_persist_context_windows(windows)

    logger.info(
        "Ingestion: %d messages → %d threads (%d skipped, %d continuations) → %d windows",
        len(messages),
        total_bundles,
        threads_skipped,
        continuations_merged,
        len(windows),
    )

    # Layer 2: Extraction (configurable: batch or async)
    extraction_mode = get_config()["pipeline"].get("extraction_mode", "batch")
    if extraction_mode == "batch":
        if batch_runner is None:
            batch_runner = BatchExtractionRunner(Anthropic())
        raw_atoms = await batch_runner.extract(windows)
    else:
        runner = AsyncExtractionRunner(client)
        raw_atoms = await runner.extract(windows)
    logger.info("Extraction: %d raw atoms from %d windows", len(raw_atoms), len(windows))
    _dump_intermediate("step2_raw_atoms.json", raw_atoms)

    # Validation: each atom against its own source window only
    validated = await _validate_atoms_by_source(raw_atoms, windows, client)
    _dump_intermediate("step3_validated_atoms.json", validated)

    # Confidence filter
    filter_result = confidence_filter(validated)
    atoms = filter_result.passed
    logger.info(
        "Filter: %d passed, %d filtered",
        filter_result.passed_count,
        filter_result.filtered_count,
    )
    _dump_intermediate("step4_filtered_atoms.json", atoms)

    # Persist atoms to Postgres (bundles already persisted above)
    await _postgres_persist_atoms(atoms)
    await _persist_to_neo4j(graph, atoms)
    logger.info(
        "═══ PIPELINE COMPLETE: %d windows → %d extracted → %d passed ═══",
        len(windows),
        len(raw_atoms),
        len(atoms),
    )

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
