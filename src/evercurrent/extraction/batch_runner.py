"""Batch extraction runner using Anthropic Message Batches API.

Submits all Stage 1 (coarse extraction) prompts as a single batch,
polls for completion, then submits all Stage 2 (enrichment) prompts
as a second batch. Results are parsed with Pydantic (instructor does
not support the batches API). Provides 50% cost savings and avoids
per-request rate limits.
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


def _build_enrichment_message(raw_atom: dict[str, Any], thread_text: str) -> str:
    """Build the user message for Stage 2 enrichment."""
    return (
        f"## Thread Context\n\n{thread_text}\n\n"
        f"## Event to Enrich\n\n```json\n{json.dumps(raw_atom, indent=2)}\n```"
    )


class BatchExtractionRunner:
    """Two-stage extraction runner using Anthropic Message Batches API.

    Submits all prompts per stage as a single batch, polls for
    completion, then parses results with Pydantic. Avoids per-request
    rate limits and provides 50% cost savings.

    Attributes:
        stats: Dict tracking windows_processed and atoms_produced.
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

        # Stage 1: batch coarse extraction
        coarse_results = await self._run_stage1_batch(windows)
        if not coarse_results:
            return []

        # Stage 2: batch enrichment
        atoms = await self._run_stage2_batch(coarse_results, windows)

        self.stats["windows_processed"] = len(windows)
        self.stats["atoms_produced"] = len(atoms)
        return atoms

    async def _run_stage1_batch(
        self,
        windows: list[ContextWindow],
    ) -> dict[int, list[dict[str, Any]]]:
        """Submit Stage 1 coarse extraction as a batch.

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
                },
            })

        results = await self._submit_and_poll(requests, stage="extraction_stage1")
        coarse_map: dict[int, list[dict[str, Any]]] = {}

        for custom_id, text in results.items():
            idx = int(custom_id.split("-")[1])
            try:
                parsed = json.loads(text)
                atoms_list = parsed.get("atoms", [])
                if atoms_list:
                    coarse_map[idx] = atoms_list
            except (json.JSONDecodeError, KeyError):
                logger.warning("Failed to parse Stage 1 result for %s", custom_id)

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
        """Submit Stage 2 enrichment as a batch.

        Args:
            coarse_results: Window index → raw atom dicts from Stage 1.
            windows: Original context windows for source metadata.

        Returns:
            List of merged Atom objects.
        """
        requests = []
        request_keys: list[tuple[int, int]] = []

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
                    },
                })
                request_keys.append((win_idx, atom_idx))

        if not requests:
            return []

        results = await self._submit_and_poll(requests, stage="extraction_stage2")
        atoms: list[Atom] = []

        for custom_id, text in results.items():
            parts = custom_id.split("-")
            win_idx = int(parts[1])
            atom_idx = int(parts[2])
            window = windows[win_idx]
            raw_atom = coarse_results[win_idx][atom_idx]

            try:
                enrichment = EnrichmentResponse.model_validate_json(text)
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
    ) -> dict[str, str]:
        """Submit a batch and poll until completion.

        Args:
            requests: List of batch request dicts with custom_id and params.
            stage: Stage name for progress tracking (e.g. "extraction_stage1").

        Returns:
            Dict mapping custom_id to response text for succeeded results.
        """
        batch = self._client.messages.batches.create(requests=requests)
        batch_id = batch.id
        total = len(requests)
        self.progress.update(
            stage=stage, batch_id=batch_id,
            total=total, succeeded=0, processing=total, errored=0,
        )
        logger.info("Batch %s submitted: %d requests (%s)", batch_id, total, stage)

        # Poll for completion, updating progress each cycle
        for _attempt in range(_MAX_POLL_ATTEMPTS):
            await asyncio.sleep(_POLL_INTERVAL)
            status = self._client.messages.batches.retrieve(batch_id)
            counts = status.request_counts
            self.progress.update(
                succeeded=counts.succeeded,
                processing=counts.processing,
                errored=counts.errored,
            )
            logger.debug(
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

        # Collect results
        results: dict[str, str] = {}
        for result in self._client.messages.batches.results(batch_id):
            if result.result.type == "succeeded":
                text = result.result.message.content[0].text
                results[result.custom_id] = text
            else:
                logger.warning(
                    "Batch result %s: %s",
                    result.custom_id,
                    result.result.type,
                )

        return results
