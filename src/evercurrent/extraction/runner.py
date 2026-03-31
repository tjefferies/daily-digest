"""Extraction runner: batch ContextWindows through LLM API (sync and async).

Processes context windows through an LLM to extract structured Atom
objects. Handles JSON parse failures gracefully and tracks stats.
The async runner processes windows concurrently via asyncio.gather.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import TYPE_CHECKING, Any

from pydantic import ValidationError

from evercurrent.config.loader import get_config
from evercurrent.extraction.prompt import build_extraction_prompt
from evercurrent.models.atom import Atom

if TYPE_CHECKING:
    from evercurrent.ingestion.context_window import ContextWindow
    from evercurrent.llm.types import AsyncLLMClient, LLMClient

logger = logging.getLogger(__name__)

_pipeline_cfg = get_config()["pipeline"]
_MODEL = _pipeline_cfg["model"]
_MAX_TOKENS = _pipeline_cfg["extraction_max_tokens"]


class ExtractionRunner:
    """Runs LLM extraction on context windows to produce Atoms.

    Attributes:
        stats: Dict tracking windows_processed and atoms_produced.
    """

    def __init__(self, client: LLMClient) -> None:
        """Initialize with an LLM client.

        Args:
            client: LLMClient-compatible adapter instance.
        """
        self._client = client
        self._system_prompt = build_extraction_prompt()
        self.stats: dict[str, int] = {
            "windows_processed": 0,
            "atoms_produced": 0,
        }

    def extract(self, windows: list[ContextWindow]) -> list[Atom]:
        """Extract atoms from a list of context windows.

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
        """Process a single context window through the API.

        Args:
            window: A single ContextWindow to extract from.

        Returns:
            List of Atom objects parsed from the API response.
        """
        try:
            response = self._client.create_message(
                model=_MODEL,
                max_tokens=_MAX_TOKENS,
                system=self._system_prompt,
                messages=[{"role": "user", "content": window.thread_text}],
            )
        except ValueError:
            logger.warning("LLM returned non-text response for window")
            return []
        return _parse_response(response.text)

    def _parse_response(self, raw_text: str) -> list[Atom]:
        """Parse JSON response text into Atom objects.

        Args:
            raw_text: Raw JSON string from the API.

        Returns:
            List of successfully parsed Atom objects.
            Invalid JSON or schema failures are logged and skipped.
        """
        return _parse_response(raw_text)


def _parse_response(raw_text: str) -> list[Atom]:
    """Parse JSON response text into Atom objects.

    Args:
        raw_text: Raw JSON string from the API.

    Returns:
        List of successfully parsed Atom objects.
        Invalid JSON or schema failures are logged and skipped.
    """
    try:
        data: Any = json.loads(raw_text)
    except json.JSONDecodeError:
        logger.warning("Failed to parse JSON response: %s...", raw_text[:100])
        return []

    if not isinstance(data, list):
        logger.warning("Expected JSON array, got %s", type(data).__name__)
        return []

    atoms: list[Atom] = []
    for item in data:
        try:
            atoms.append(Atom(**item))
        except ValidationError:
            logger.warning("Atom validation failed: %s", item.get("summary", "unknown"))
    return atoms


_DEFAULT_CONCURRENCY = 10


class AsyncExtractionRunner:
    """Async runner that extracts atoms from context windows concurrently.

    Uses asyncio.gather with a semaphore to limit concurrent LLM calls,
    avoiding rate-limit errors while maximizing throughput.

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
        self._system_prompt = build_extraction_prompt()
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
        """Process a single context window through the async API.

        Args:
            window: A single ContextWindow to extract from.

        Returns:
            List of Atom objects parsed from the API response.
        """
        async with self._semaphore:
            try:
                response = await self._client.create_message(
                    model=_MODEL,
                    max_tokens=_MAX_TOKENS,
                    system=self._system_prompt,
                    messages=[{"role": "user", "content": window.thread_text}],
                )
            except ValueError:
                logger.warning("LLM returned non-text response for window")
                return []
            return _parse_response(response.text)
