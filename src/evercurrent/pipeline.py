"""Pipeline orchestrator: wires Ingestion → Extraction → Filter → Validation.

Runs the full extraction pipeline from synthetic data through LLM
extraction, confidence filtering, and two-pass validation. Returns
a PipelineResult containing validated atoms ready for scoring.
Provides both sync (run_pipeline) and async (async_run_pipeline) variants.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from evercurrent.dataset.messages import load_messages
from evercurrent.extraction.filter import confidence_filter
from evercurrent.extraction.runner import AsyncExtractionRunner, ExtractionRunner
from evercurrent.extraction.validation import async_validate_atoms, validate_atoms
from evercurrent.ingestion.context_window import assemble_context_windows
from evercurrent.ingestion.threads import group_by_thread

if TYPE_CHECKING:
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


def run_pipeline(client: LLMClient) -> PipelineResult:
    """Run the full extraction pipeline: Ingestion → Extraction → Filter → Validation.

    Args:
        client: LLMClient-compatible adapter for LLM API calls.

    Returns:
        PipelineResult with validated, filtered atoms and processing stats.
    """
    # Layer 1: Ingestion
    messages = load_messages()
    bundles = group_by_thread(messages)
    windows = assemble_context_windows(bundles)
    logger.info(
        "Ingestion: %d messages → %d threads → %d windows",
        len(messages),
        len(bundles),
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
            "context_windows": len(windows),
            "atoms_extracted": len(raw_atoms),
            "atoms_after_filter": len(atoms),
        },
    )


async def async_run_pipeline(client: AsyncLLMClient) -> PipelineResult:
    """Run the full extraction pipeline asynchronously with concurrent LLM calls.

    Uses AsyncExtractionRunner for concurrent window processing and
    async_validate_atoms for concurrent validation. Eliminates the
    sync-to-async bridge in FastAPI endpoints.

    Args:
        client: AsyncLLMClient-compatible adapter for async LLM API calls.

    Returns:
        PipelineResult with validated, filtered atoms and processing stats.
    """
    # Layer 1: Ingestion (CPU-bound, no async needed)
    messages = load_messages()
    bundles = group_by_thread(messages)
    windows = assemble_context_windows(bundles)
    logger.info(
        "Ingestion: %d messages → %d threads → %d windows",
        len(messages),
        len(bundles),
        len(windows),
    )

    # Layer 2: Extraction (concurrent LLM calls)
    runner = AsyncExtractionRunner(client)
    raw_atoms = await runner.extract(windows)
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

    return PipelineResult(
        atoms=atoms,
        stats={
            "messages_loaded": len(messages),
            "threads_found": len(bundles),
            "context_windows": len(windows),
            "atoms_extracted": len(raw_atoms),
            "atoms_after_filter": len(atoms),
        },
    )
