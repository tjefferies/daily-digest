"""Batch extraction runner using Anthropic Message Batches API.

Submits all Stage 1 (coarse extraction) prompts as a single batch,
polls for completion, then submits all Stage 2 (enrichment) prompts
as a second batch. Uses tool_use for structured JSON output — the LLM
returns clean JSON via tool calls, eliminating markdown fencing issues.
Provides 50% cost savings and avoids per-request rate limits.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from evercurrent.config.loader import get_config
from evercurrent.extraction.prompt import build_coarse_prompt, build_enrichment_prompt
from evercurrent.models.atom import Atom, AtomSource, AtomType
from evercurrent.models.responses import EnrichmentResponse

if TYPE_CHECKING:
    from anthropic import Anthropic

    from evercurrent.ingestion.context_window import ContextWindow

logger = logging.getLogger(__name__)

_pipeline_cfg = get_config()["pipeline"]
_MODEL = _pipeline_cfg["model"]
_MAX_TOKENS = _pipeline_cfg["extraction_max_tokens"]

_VALID_TYPES: set[str] = set(AtomType.__args__)  # type: ignore[attr-defined]

_POLL_INTERVAL = 5
_MAX_POLL_ATTEMPTS = 720  # 5s × 720 = 1 hour max

# Tool definitions for structured output via tool_use.
_COARSE_TOOL = {
    "name": "extract_atoms",
    "description": "Return extracted atoms from a Slack conversation thread.",
    "input_schema": {
        "type": "object",
        "properties": {
            "atoms": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "atom_id": {"type": "string"},
                        "type": {
                            "type": "string",
                            "enum": list(_VALID_TYPES),
                        },
                        "summary": {"type": "string"},
                        "detail": {"type": "string"},
                        "source": {
                            "type": "object",
                            "properties": {
                                "channel": {"type": "string"},
                                "thread_ts": {"type": "string"},
                                "message_range": {
                                    "type": "array",
                                    "items": {"type": "integer"},
                                },
                                "key_participants": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                },
                            },
                            "required": [
                                "channel",
                                "thread_ts",
                                "message_range",
                                "key_participants",
                            ],
                        },
                    },
                    "required": [
                        "atom_id",
                        "type",
                        "summary",
                        "detail",
                        "source",
                    ],
                },
            },
        },
        "required": ["atoms"],
    },
}

_ENRICHMENT_TOOL = {
    "name": "enrich_atom",
    "description": "Return metadata enrichment for an extracted atom.",
    "input_schema": {
        "type": "object",
        "properties": {
            "workstreams": {
                "type": "object",
                "properties": {
                    "originating": {"type": "string"},
                    "affected": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
                "required": ["originating", "affected"],
            },
            "urgency": {
                "type": "string",
                "enum": ["low", "medium", "high", "critical"],
            },
            "confidence": {"type": "number"},
            "implicit_decision": {"type": "boolean"},
            "phase_relevance": {
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": ["Concept", "EVT", "DVT", "PVT", "MP"],
                },
            },
        },
        "required": [
            "workstreams",
            "urgency",
            "confidence",
            "implicit_decision",
            "phase_relevance",
        ],
    },
}


def _build_enrichment_message(raw_atom: dict[str, Any], thread_text: str) -> str:
    """Build the user message for Stage 2 enrichment."""
    return (
        f"## Thread Context\n\n{thread_text}\n\n"
        f"## Event to Enrich\n\n```json\n{json.dumps(raw_atom, indent=2)}\n```"
    )


def _extract_tool_input(message: Any) -> dict[str, Any] | None:  # noqa: ANN401
    """Extract tool_use input from a message response.

    Args:
        message: Anthropic message object with content blocks.

    Returns:
        The tool input dict, or None if no tool_use block found.
    """
    for block in message.content:
        if block.type == "tool_use":
            return block.input
    return None


class BatchExtractionRunner:
    """Two-stage extraction runner using Anthropic Message Batches API.

    Uses tool_use for structured output — the LLM returns clean JSON
    via tool calls. Submits all prompts per stage as a single batch,
    polls for completion, then parses tool_use results.

    Attributes:
        stats: Dict tracking windows_processed and atoms_produced.
        progress: Dict with live batch progress from Anthropic API.
    """

    def __init__(self, client: Anthropic) -> None:
        """Initialize with an Anthropic SDK client (not async adapter).

        Args:
            client: Raw Anthropic SDK client for batch API access.
        """
        self._client = client
        self._coarse_prompt = build_coarse_prompt()
        self._enrichment_prompt = build_enrichment_prompt()
        self.stats: dict[str, int] = {
            "windows_processed": 0,
            "atoms_produced": 0,
        }
        self.progress: dict[str, Any] = {
            "stage": "",
            "batch_id": "",
            "total": 0,
            "succeeded": 0,
            "processing": 0,
            "errored": 0,
        }

    async def extract(self, windows: list[ContextWindow]) -> list[Atom]:
        """Extract atoms from context windows via batched two-stage pipeline.

        Args:
            windows: ContextWindow objects from Layer 1.

        Returns:
            List of validated Atom objects extracted from all windows.
        """
        if not windows:
            return []

        coarse_results = await self._run_stage1_batch(windows)
        if not coarse_results:
            return []

        atoms = await self._run_stage2_batch(coarse_results, windows)

        self.stats["windows_processed"] = len(windows)
        self.stats["atoms_produced"] = len(atoms)
        return atoms

    async def _run_stage1_batch(
        self,
        windows: list[ContextWindow],
    ) -> dict[int, list[dict[str, Any]]]:
        """Submit Stage 1 coarse extraction as a batch with tool_use.

        Args:
            windows: Context windows to extract from.

        Returns:
            Dict mapping window index to list of raw atom dicts.
        """
        requests = []
        for i, window in enumerate(windows):
            requests.append({
                "custom_id": f"stage1-{i}",
                "params": {
                    "model": _MODEL,
                    "max_tokens": _MAX_TOKENS,
                    "system": self._coarse_prompt,
                    "messages": [{"role": "user", "content": window.thread_text}],
                    "tools": [_COARSE_TOOL],
                    "tool_choice": {"type": "tool", "name": "extract_atoms"},
                },
            })

        results = await self._submit_and_poll(requests, stage="extraction_stage1")
        coarse_map: dict[int, list[dict[str, Any]]] = {}

        for custom_id, tool_input in results.items():
            idx = int(custom_id.split("-")[1])
            atoms_list = tool_input.get("atoms", [])
            if atoms_list:
                coarse_map[idx] = atoms_list

        logger.info(
            "Stage 1 batch: %d windows → %d with atoms",
            len(windows),
            len(coarse_map),
        )
        return coarse_map

    async def _run_stage2_batch(
        self,
        coarse_results: dict[int, list[dict[str, Any]]],
        windows: list[ContextWindow],
    ) -> list[Atom]:
        """Submit Stage 2 enrichment as a batch with tool_use.

        Args:
            coarse_results: Window index → raw atom dicts from Stage 1.
            windows: Original context windows for source metadata.

        Returns:
            List of merged Atom objects.
        """
        requests = []

        for win_idx, raw_atoms in coarse_results.items():
            window = windows[win_idx]
            for atom_idx, raw_atom in enumerate(raw_atoms):
                custom_id = f"stage2-{win_idx}-{atom_idx}"
                requests.append({
                    "custom_id": custom_id,
                    "params": {
                        "model": _MODEL,
                        "max_tokens": _MAX_TOKENS,
                        "system": self._enrichment_prompt,
                        "messages": [{
                            "role": "user",
                            "content": _build_enrichment_message(
                                raw_atom, window.thread_text,
                            ),
                        }],
                        "tools": [_ENRICHMENT_TOOL],
                        "tool_choice": {"type": "tool", "name": "enrich_atom"},
                    },
                })

        if not requests:
            return []

        results = await self._submit_and_poll(requests, stage="extraction_stage2")
        atoms: list[Atom] = []

        for custom_id, tool_input in results.items():
            parts = custom_id.split("-")
            win_idx = int(parts[1])
            atom_idx = int(parts[2])
            window = windows[win_idx]
            raw_atom = coarse_results[win_idx][atom_idx]

            try:
                enrichment = EnrichmentResponse.model_validate(tool_input)
                atom = self._merge_atom(raw_atom, enrichment, window)
                atoms.append(atom)
            except Exception:
                logger.warning(
                    "Failed to parse Stage 2 result for %s",
                    custom_id,
                    exc_info=True,
                )

        logger.info("Stage 2 batch: %d enrichments → %d atoms", len(requests), len(atoms))
        return atoms

    def _merge_atom(
        self,
        raw: dict[str, Any],
        enrichment: EnrichmentResponse,
        window: ContextWindow,
    ) -> Atom:
        """Merge a coarse atom dict with enrichment into a full Atom."""
        source_data = dict(raw.get("source", {}))
        source_data["channel"] = window.channel
        source_data["thread_ts"] = window.thread_ts
        raw_type = raw.get("type", "STATUS_UPDATE")
        atom_type = raw_type if raw_type in _VALID_TYPES else "STATUS_UPDATE"
        return Atom(
            atom_id=uuid4(),
            type=atom_type,
            summary=raw.get("summary", ""),
            detail=raw.get("detail", ""),
            source=AtomSource(**source_data),
            workstreams=enrichment.workstreams,
            urgency=enrichment.urgency,
            confidence=enrichment.confidence,
            implicit_decision=enrichment.implicit_decision,
            phase_relevance=enrichment.phase_relevance,
        )

    async def _submit_and_poll(
        self,
        requests: list[dict[str, Any]],
        stage: str = "",
    ) -> dict[str, dict[str, Any]]:
        """Submit a batch and poll until completion.

        Args:
            requests: List of batch request dicts with custom_id and params.
            stage: Stage name for progress tracking.

        Returns:
            Dict mapping custom_id to tool_use input dict for succeeded results.
        """
        logger.info("Submitting %s batch with %d requests", stage, len(requests))
        batch = self._client.messages.batches.create(requests=requests)
        batch_id = batch.id
        total = len(requests)
        self.progress.update(
            stage=stage, batch_id=batch_id,
            total=total, succeeded=0, processing=total, errored=0,
        )
        logger.info("Batch %s submitted: %d requests (%s)", batch_id, total, stage)

        for _attempt in range(_MAX_POLL_ATTEMPTS):
            await asyncio.sleep(_POLL_INTERVAL)
            status = self._client.messages.batches.retrieve(batch_id)
            counts = status.request_counts
            self.progress.update(
                succeeded=counts.succeeded,
                processing=counts.processing,
                errored=counts.errored,
            )
            logger.info(
                "Batch %s: %d/%d succeeded, %d processing, %d errored",
                batch_id, counts.succeeded, total,
                counts.processing, counts.errored,
            )
            if status.processing_status == "ended":
                logger.info("Batch %s completed", batch_id)
                break
        else:
            logger.warning("Batch %s timed out after polling", batch_id)
            return {}

        results: dict[str, dict[str, Any]] = {}
        succeeded = 0
        failed = 0
        for result in self._client.messages.batches.results(batch_id):
            if result.result.type == "succeeded":
                tool_input = _extract_tool_input(result.result.message)
                if tool_input is not None:
                    results[result.custom_id] = tool_input
                    succeeded += 1
                else:
                    failed += 1
                    logger.warning("No tool_use block in %s", result.custom_id)
            else:
                failed += 1
                logger.warning(
                    "Batch result %s: %s (error: %s)",
                    result.custom_id,
                    result.result.type,
                    getattr(result.result, "error", None),
                )
        logger.info(
            "Batch %s results: %d succeeded, %d failed of %d total",
            batch_id, succeeded, failed, total,
        )
        return results
