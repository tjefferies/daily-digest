"""Two-stage extraction runner: coarse extract → enrich (sync and async).

Stage 1 identifies events (type, summary, detail, source) using a focused
prompt. Stage 2 enriches each event with metadata (workstreams, urgency,
confidence, implicit_decision, phase_relevance) in a separate LLM call.

This two-stage approach replaces the monolithic single-prompt extraction,
reducing cognitive load per LLM call and improving extraction quality.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import TYPE_CHECKING
from uuid import uuid4

from evercurrent.config.loader import get_config
from evercurrent.extraction.prompt import build_coarse_prompt, build_enrichment_prompt
from evercurrent.models.atom import Atom, AtomSource, AtomType
from evercurrent.models.responses import CoarseExtractionResponse, EnrichmentResponse

_VALID_TYPES: set[str] = set(AtomType.__args__)  # type: ignore[attr-defined]

if TYPE_CHECKING:
    from evercurrent.ingestion.context_window import ContextWindow
    from evercurrent.llm.types import AsyncLLMClient, LLMClient

logger = logging.getLogger(__name__)

_pipeline_cfg = get_config()["pipeline"]
_MODEL = _pipeline_cfg["model"]
_MAX_TOKENS = _pipeline_cfg["extraction_max_tokens"]


def _merge_atom(raw: dict, enrichment: EnrichmentResponse, window: ContextWindow) -> Atom:
    """Merge a coarse atom dict with enrichment metadata into a full Atom.

    Overrides source.channel and source.thread_ts from the ContextWindow
    since the LLM cannot infer these from thread_text alone.
    """
    source_data = dict(raw.get("source", {}))
    source_data["channel"] = window.channel
    source_data["thread_ts"] = window.thread_ts
    raw_type = raw.get("type", "STATUS_UPDATE")
    atom_type = raw_type if raw_type in _VALID_TYPES else "STATUS_UPDATE"
    if raw_type != atom_type:
        logger.warning("Unknown atom type %r, defaulting to STATUS_UPDATE", raw_type)
    return Atom(
        atom_id=uuid4(),
        type=atom_type,
        summary=raw["summary"],
        detail=raw["detail"],
        source=AtomSource(**source_data),
        workstreams=enrichment.workstreams,
        urgency=enrichment.urgency,
        confidence=enrichment.confidence,
        implicit_decision=enrichment.implicit_decision,
        phase_relevance=enrichment.phase_relevance,
    )


def _build_enrichment_message(raw_atom: dict, thread_text: str) -> str:
    """Build the user message for Stage 2 enrichment."""
    return (
        f"## Thread Context\n\n{thread_text}\n\n"
        f"## Event to Enrich\n\n```json\n{json.dumps(raw_atom, indent=2)}\n```"
    )


class ExtractionRunner:
    """Two-stage extraction runner: coarse extract then enrich.

    Stage 1 calls the LLM with CoarseExtractionResponse to identify events.
    Stage 2 calls the LLM with EnrichmentResponse for each event to assign
    metadata. The results are merged into full Atom objects.

    Attributes:
        stats: Dict tracking windows_processed and atoms_produced.
    """

    def __init__(self, client: LLMClient) -> None:
        """Initialize with an LLM client.

        Args:
            client: LLMClient-compatible adapter instance.
        """
        self._client = client
        self._coarse_prompt = build_coarse_prompt()
        self._enrichment_prompt = build_enrichment_prompt()
        self.stats: dict[str, int] = {
            "windows_processed": 0,
            "atoms_produced": 0,
        }

    def extract(self, windows: list[ContextWindow]) -> list[Atom]:
        """Extract atoms from context windows via two-stage pipeline.

        Args:
            windows: ContextWindow objects from Layer 1.

        Returns:
            List of validated Atom objects extracted from all windows.
        """
        all_atoms: list[Atom] = []
        for window in windows:
            atoms = self._process_window(window)
            all_atoms.extend(atoms)
            self.stats["windows_processed"] += 1
        self.stats["atoms_produced"] = len(all_atoms)
        return all_atoms

    def _process_window(self, window: ContextWindow) -> list[Atom]:
        """Process a single window through Stage 1 → Stage 2."""
        # Stage 1: coarse extraction
        try:
            coarse = self._client.create_structured_message(
                model=_MODEL,
                max_tokens=_MAX_TOKENS,
                system=self._coarse_prompt,
                messages=[{"role": "user", "content": window.thread_text}],
                response_model=CoarseExtractionResponse,
            )
        except Exception:
            logger.warning("Stage 1 extraction failed for window", exc_info=True)
            return []

        # Stage 2: enrich each coarse atom
        atoms: list[Atom] = []
        for raw_atom in coarse.atoms:
            try:
                enrichment = self._client.create_structured_message(
                    model=_MODEL,
                    max_tokens=_MAX_TOKENS,
                    system=self._enrichment_prompt,
                    messages=[
                        {
                            "role": "user",
                            "content": _build_enrichment_message(raw_atom, window.thread_text),
                        }
                    ],
                    response_model=EnrichmentResponse,
                )
                atoms.append(_merge_atom(raw_atom, enrichment, window))
            except Exception:
                logger.warning("Stage 2 enrichment failed for atom", exc_info=True)
                continue
        return atoms


_DEFAULT_CONCURRENCY = get_config()["pipeline"].get("max_concurrency", 2)


class AsyncExtractionRunner:
    """Async two-stage extraction runner with concurrency control.

    Uses asyncio.gather with a semaphore to limit concurrent LLM calls.

    Attributes:
        stats: Dict tracking windows_processed and atoms_produced.
    """

    def __init__(
        self,
        client: AsyncLLMClient,
        max_concurrency: int = _DEFAULT_CONCURRENCY,
    ) -> None:
        """Initialize with an async LLM client and concurrency limit.

        Args:
            client: AsyncLLMClient-compatible adapter instance.
            max_concurrency: Maximum concurrent LLM calls.
        """
        self._client = client
        self._coarse_prompt = build_coarse_prompt()
        self._enrichment_prompt = build_enrichment_prompt()
        self._semaphore = asyncio.Semaphore(max_concurrency)
        self.stats: dict[str, int] = {
            "windows_processed": 0,
            "atoms_produced": 0,
        }

    async def extract(self, windows: list[ContextWindow]) -> list[Atom]:
        """Extract atoms from context windows concurrently.

        Args:
            windows: ContextWindow objects from Layer 1.

        Returns:
            List of validated Atom objects extracted from all windows.
        """
        if not windows:
            return []

        tasks = [self._process_window(w) for w in windows]
        results = await asyncio.gather(*tasks)

        all_atoms: list[Atom] = []
        for atoms in results:
            all_atoms.extend(atoms)
        self.stats["windows_processed"] = len(windows)
        self.stats["atoms_produced"] = len(all_atoms)
        return all_atoms

    async def _process_window(self, window: ContextWindow) -> list[Atom]:
        """Process a single window through async Stage 1 → Stage 2."""
        async with self._semaphore:
            # Stage 1: coarse extraction
            try:
                coarse = await self._client.create_structured_message(
                    model=_MODEL,
                    max_tokens=_MAX_TOKENS,
                    system=self._coarse_prompt,
                    messages=[{"role": "user", "content": window.thread_text}],
                    response_model=CoarseExtractionResponse,
                )
            except Exception:
                logger.warning("Stage 1 extraction failed for window", exc_info=True)
                return []

            # Stage 2: enrich each coarse atom
            atoms: list[Atom] = []
            for raw_atom in coarse.atoms:
                try:
                    enrichment = await self._client.create_structured_message(
                        model=_MODEL,
                        max_tokens=_MAX_TOKENS,
                        system=self._enrichment_prompt,
                        messages=[
                            {
                                "role": "user",
                                "content": _build_enrichment_message(raw_atom, window.thread_text),
                            }
                        ],
                        response_model=EnrichmentResponse,
                    )
                    atoms.append(_merge_atom(raw_atom, enrichment, window))
                except Exception:
                    logger.warning("Stage 2 enrichment failed for atom", exc_info=True)
                    continue
            return atoms
