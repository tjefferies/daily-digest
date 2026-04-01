"""Tests for batch extraction runner using Anthropic Message Batches API."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from evercurrent.ingestion.context_window import ContextWindow


def _make_window(
    thread_text: str = "Test thread",
    channel: str = "#test",
    thread_ts: str = "1000.001",
) -> ContextWindow:
    """Create a minimal ContextWindow for testing."""
    return ContextWindow(
        thread_text=thread_text,
        channel=channel,
        thread_ts=thread_ts,
        message_range=(thread_ts, thread_ts),
        compressed=False,
    )


def _make_batch_result(custom_id: str, text: str) -> MagicMock:
    """Create a mock batch result with succeeded status."""
    result = MagicMock()
    result.custom_id = custom_id
    result.result.type = "succeeded"
    content_block = MagicMock()
    content_block.text = text
    result.result.message.content = [content_block]
    return result


def _make_batch_error(custom_id: str) -> MagicMock:
    """Create a mock batch result with errored status."""
    result = MagicMock()
    result.custom_id = custom_id
    result.result.type = "errored"
    result.result.error = MagicMock(message="Test error")
    return result


class TestBatchExtractionRunner:
    """Tests for the batch-based extraction runner."""

    @pytest.mark.asyncio
    async def test_extract_returns_atoms(self) -> None:
        """Batch extraction returns Atom objects from batch results."""
        from evercurrent.extraction.batch_runner import BatchExtractionRunner

        mock_client = MagicMock()

        # Mock batch creation
        mock_batch = MagicMock()
        mock_batch.id = "batch_001"
        mock_client.messages.batches.create.return_value = mock_batch

        # Mock batch status polling
        mock_status = MagicMock()
        mock_status.processing_status = "ended"
        mock_client.messages.batches.retrieve.return_value = mock_status

        # Mock Stage 1 results: one window returns one atom
        coarse_json = json.dumps({"atoms": [{
            "atom_id": "test-id", "type": "DECISION",
            "summary": "Test", "detail": "Detail",
            "source": {
                "channel": "#test", "thread_ts": "1000.001",
                "message_range": [0, 1], "key_participants": ["U001"],
            },
        }]})
        stage1_result = _make_batch_result("stage1-0", coarse_json)

        # Mock Stage 2 results
        enrich_json = json.dumps({
            "workstreams": {"originating": "chassis", "affected": []},
            "urgency": "medium", "confidence": 0.9,
            "implicit_decision": False, "phase_relevance": [],
        })
        stage2_result = _make_batch_result("stage2-0-0", enrich_json)

        # Results returns different items per call
        mock_client.messages.batches.results.side_effect = [
            [stage1_result],
            [stage2_result],
        ]

        runner = BatchExtractionRunner(mock_client)
        windows = [_make_window()]
        atoms = await runner.extract(windows)

        assert len(atoms) >= 1
        assert atoms[0].type == "DECISION"
        assert atoms[0].summary == "Test"
        assert atoms[0].source.channel == "#test"

    @pytest.mark.asyncio
    async def test_extract_empty_windows(self) -> None:
        """Empty window list returns empty atom list."""
        from evercurrent.extraction.batch_runner import BatchExtractionRunner

        mock_client = MagicMock()
        runner = BatchExtractionRunner(mock_client)
        atoms = await runner.extract([])

        assert atoms == []

    @pytest.mark.asyncio
    async def test_handles_batch_errors(self) -> None:
        """Errored batch results are skipped without crashing."""
        from evercurrent.extraction.batch_runner import BatchExtractionRunner

        mock_client = MagicMock()

        mock_batch = MagicMock()
        mock_batch.id = "batch_err"
        mock_client.messages.batches.create.return_value = mock_batch

        mock_status = MagicMock()
        mock_status.processing_status = "ended"
        mock_client.messages.batches.retrieve.return_value = mock_status

        # Stage 1 returns an error
        error_result = _make_batch_error("stage1-0")
        mock_client.messages.batches.results.return_value = [error_result]

        runner = BatchExtractionRunner(mock_client)
        atoms = await runner.extract([_make_window()])

        assert atoms == []

    @pytest.mark.asyncio
    async def test_stats_tracked(self) -> None:
        """Runner tracks windows_processed and atoms_produced stats."""
        from evercurrent.extraction.batch_runner import BatchExtractionRunner

        mock_client = MagicMock()

        mock_batch = MagicMock()
        mock_batch.id = "batch_stats"
        mock_client.messages.batches.create.return_value = mock_batch

        mock_status = MagicMock()
        mock_status.processing_status = "ended"
        mock_client.messages.batches.retrieve.return_value = mock_status

        coarse_json = json.dumps({"atoms": [{
            "atom_id": "id1", "type": "BLOCKER",
            "summary": "Blocked", "detail": "Detail",
            "source": {
                "channel": "#test", "thread_ts": "1000.001",
                "message_range": [0, 1], "key_participants": ["U001"],
            },
        }]})
        stage1_result = _make_batch_result("stage1-0", coarse_json)

        enrich_json = json.dumps({
            "workstreams": {"originating": "chassis", "affected": []},
            "urgency": "high", "confidence": 0.85,
            "implicit_decision": False, "phase_relevance": [],
        })
        stage2_result = _make_batch_result("stage2-0-0", enrich_json)

        mock_client.messages.batches.results.side_effect = [
            [stage1_result],
            [stage2_result],
        ]

        runner = BatchExtractionRunner(mock_client)
        await runner.extract([_make_window()])

        assert runner.stats["windows_processed"] == 1
        assert runner.stats["atoms_produced"] >= 1
