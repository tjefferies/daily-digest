"""Tests for the pipeline orchestrator module (sync and async)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from evercurrent.models.atom import Atom, AtomSource, AtomWorkstreams
from evercurrent.pipeline import PipelineResult, async_run_pipeline, run_pipeline


def _make_atom(
    *,
    summary: str = "Test decision",
    atom_type: str = "DECISION",
    confidence: float = 0.9,
) -> Atom:
    """Create a minimal Atom for testing."""
    return Atom(
        atom_id=uuid4(),
        type=atom_type,
        summary=summary,
        detail="Detail text",
        source=AtomSource(
            channel="#test",
            thread_ts="1000.0001",
            message_range=[0, 1],
            key_participants=["U001"],
        ),
        workstreams=AtomWorkstreams(originating="chassis"),
        urgency="medium",
        confidence=confidence,
    )


class TestRunPipeline:
    """Tests for the run_pipeline orchestrator."""

    @patch("evercurrent.pipeline.ExtractionRunner")
    @patch("evercurrent.pipeline.validate_atoms")
    @patch("evercurrent.pipeline.confidence_filter")
    def test_returns_pipeline_result(
        self,
        mock_filter: MagicMock,
        mock_validate: MagicMock,
        mock_runner_cls: MagicMock,
    ) -> None:
        """run_pipeline returns a PipelineResult with atoms and stats."""
        atom = _make_atom()
        mock_runner = MagicMock()
        mock_runner.extract.return_value = [atom]
        mock_runner_cls.return_value = mock_runner
        mock_validate.return_value = [atom]

        from evercurrent.extraction.filter import FilterResult

        mock_filter.return_value = FilterResult(passed=[atom], filtered=[])

        mock_client = MagicMock()
        result = run_pipeline(mock_client)

        assert isinstance(result, PipelineResult)
        assert len(result.atoms) == 1
        assert result.atoms[0].summary == "Test decision"

    @patch("evercurrent.pipeline.ExtractionRunner")
    @patch("evercurrent.pipeline.validate_atoms")
    @patch("evercurrent.pipeline.confidence_filter")
    def test_filters_low_confidence_atoms(
        self,
        mock_filter: MagicMock,
        mock_validate: MagicMock,
        mock_runner_cls: MagicMock,
    ) -> None:
        """Low-confidence atoms are filtered out by the pipeline."""
        high = _make_atom(summary="High conf", confidence=0.9)
        low = _make_atom(summary="Low conf", confidence=0.3)
        mock_runner = MagicMock()
        mock_runner.extract.return_value = [high, low]
        mock_runner_cls.return_value = mock_runner
        mock_validate.return_value = [high, low]

        from evercurrent.extraction.filter import FilterResult

        mock_filter.return_value = FilterResult(passed=[high], filtered=[low])

        mock_client = MagicMock()
        result = run_pipeline(mock_client)

        assert len(result.atoms) == 1
        assert result.atoms[0].summary == "High conf"

    @patch("evercurrent.pipeline.ExtractionRunner")
    @patch("evercurrent.pipeline.validate_atoms")
    @patch("evercurrent.pipeline.confidence_filter")
    def test_tracks_stats(
        self,
        mock_filter: MagicMock,
        mock_validate: MagicMock,
        mock_runner_cls: MagicMock,
    ) -> None:
        """Pipeline result includes processing stats."""
        atom = _make_atom()
        mock_runner = MagicMock()
        mock_runner.extract.return_value = [atom]
        mock_runner_cls.return_value = mock_runner
        mock_validate.return_value = [atom]

        from evercurrent.extraction.filter import FilterResult

        mock_filter.return_value = FilterResult(passed=[atom], filtered=[])

        mock_client = MagicMock()
        result = run_pipeline(mock_client)

        assert result.stats["atoms_extracted"] == 1
        assert result.stats["atoms_after_filter"] == 1

    @patch("evercurrent.pipeline.ExtractionRunner")
    @patch("evercurrent.pipeline.validate_atoms")
    @patch("evercurrent.pipeline.confidence_filter")
    def test_empty_extraction_returns_empty(
        self,
        mock_filter: MagicMock,
        mock_validate: MagicMock,
        mock_runner_cls: MagicMock,
    ) -> None:
        """Pipeline handles zero extracted atoms gracefully."""
        mock_runner = MagicMock()
        mock_runner.extract.return_value = []
        mock_runner_cls.return_value = mock_runner
        mock_validate.return_value = []

        from evercurrent.extraction.filter import FilterResult

        mock_filter.return_value = FilterResult(passed=[], filtered=[])

        mock_client = MagicMock()
        result = run_pipeline(mock_client)

        assert result.atoms == []
        assert result.stats["atoms_extracted"] == 0


class TestPipelineResult:
    """Tests for PipelineResult dataclass."""

    def test_result_stores_atoms_and_stats(self) -> None:
        """PipelineResult stores atoms and stats."""
        atom = _make_atom()
        result = PipelineResult(
            atoms=[atom],
            stats={"atoms_extracted": 1, "atoms_after_filter": 1},
        )
        assert len(result.atoms) == 1
        assert result.stats["atoms_extracted"] == 1


class TestAsyncRunPipeline:
    """Tests for the async_run_pipeline orchestrator."""

    @patch("evercurrent.pipeline.BatchExtractionRunner")
    @patch("evercurrent.pipeline.async_validate_atoms")
    @patch("evercurrent.pipeline.confidence_filter")
    async def test_returns_pipeline_result(
        self,
        mock_filter: MagicMock,
        mock_validate: MagicMock,
        mock_runner_cls: MagicMock,
    ) -> None:
        """async_run_pipeline returns a PipelineResult with atoms and stats."""
        atom = _make_atom()
        mock_runner = AsyncMock()
        mock_runner.extract.return_value = [atom]
        mock_runner_cls.return_value = mock_runner
        mock_validate.return_value = [atom]

        from evercurrent.extraction.filter import FilterResult

        mock_filter.return_value = FilterResult(passed=[atom], filtered=[])

        mock_client = AsyncMock()
        result = await async_run_pipeline(mock_client)

        assert isinstance(result, PipelineResult)
        assert len(result.atoms) == 1
        assert result.atoms[0].summary == "Test decision"

    @patch("evercurrent.pipeline.BatchExtractionRunner")
    @patch("evercurrent.pipeline.async_validate_atoms")
    @patch("evercurrent.pipeline.confidence_filter")
    async def test_tracks_stats(
        self,
        mock_filter: MagicMock,
        mock_validate: MagicMock,
        mock_runner_cls: MagicMock,
    ) -> None:
        """Async pipeline result includes processing stats."""
        atom = _make_atom()
        mock_runner = AsyncMock()
        mock_runner.extract.return_value = [atom]
        mock_runner_cls.return_value = mock_runner
        mock_validate.return_value = [atom]

        from evercurrent.extraction.filter import FilterResult

        mock_filter.return_value = FilterResult(passed=[atom], filtered=[])

        mock_client = AsyncMock()
        result = await async_run_pipeline(mock_client)

        assert result.stats["atoms_extracted"] == 1
        assert result.stats["atoms_after_filter"] == 1

    @patch("evercurrent.pipeline.BatchExtractionRunner")
    @patch("evercurrent.pipeline.async_validate_atoms")
    @patch("evercurrent.pipeline.confidence_filter")
    async def test_empty_extraction_returns_empty(
        self,
        mock_filter: MagicMock,
        mock_validate: MagicMock,
        mock_runner_cls: MagicMock,
    ) -> None:
        """Async pipeline handles zero extracted atoms gracefully."""
        mock_runner = AsyncMock()
        mock_runner.extract.return_value = []
        mock_runner_cls.return_value = mock_runner
        mock_validate.return_value = []

        from evercurrent.extraction.filter import FilterResult

        mock_filter.return_value = FilterResult(passed=[], filtered=[])

        mock_client = AsyncMock()
        result = await async_run_pipeline(mock_client)

        assert result.atoms == []
        assert result.stats["atoms_extracted"] == 0


class TestNeo4jPersistence:
    """Tests for Neo4j atom persistence in async pipeline."""

    @pytest.mark.asyncio
    @patch("evercurrent.pipeline.GraphClient")
    @patch("evercurrent.pipeline.BatchExtractionRunner")
    @patch("evercurrent.pipeline.async_validate_atoms")
    @patch("evercurrent.pipeline.confidence_filter")
    async def test_async_pipeline_persists_atoms_to_neo4j(
        self,
        mock_filter: MagicMock,
        mock_validate: MagicMock,
        mock_runner_cls: MagicMock,
        mock_graph_cls: MagicMock,
    ) -> None:
        """async_run_pipeline calls GraphClient.persist_atoms with filtered atoms."""
        atom = _make_atom()
        mock_runner = AsyncMock()
        mock_runner.extract.return_value = [atom]
        mock_runner_cls.return_value = mock_runner
        mock_validate.return_value = [atom]

        from evercurrent.extraction.filter import FilterResult

        mock_filter.return_value = FilterResult(passed=[atom], filtered=[])

        mock_graph = AsyncMock()
        mock_graph_cls.return_value = mock_graph

        mock_client = AsyncMock()
        result = await async_run_pipeline(mock_client)

        assert len(result.atoms) == 1
        mock_graph.ensure_schema.assert_called_once()
        mock_graph.persist_atoms.assert_called_once()
        persisted = mock_graph.persist_atoms.call_args[0][0]
        assert len(persisted) == 1
        assert persisted[0].summary == "Test decision"
        mock_graph.close.assert_called_once()

    @pytest.mark.asyncio
    @patch("evercurrent.pipeline.GraphClient")
    @patch("evercurrent.pipeline.BatchExtractionRunner")
    @patch("evercurrent.pipeline.async_validate_atoms")
    @patch("evercurrent.pipeline.confidence_filter")
    async def test_async_pipeline_graceful_neo4j_failure(
        self,
        mock_filter: MagicMock,
        mock_validate: MagicMock,
        mock_runner_cls: MagicMock,
        mock_graph_cls: MagicMock,
    ) -> None:
        """Pipeline does not crash when Neo4j is unreachable."""
        atom = _make_atom()
        mock_runner = AsyncMock()
        mock_runner.extract.return_value = [atom]
        mock_runner_cls.return_value = mock_runner
        mock_validate.return_value = [atom]

        from evercurrent.extraction.filter import FilterResult

        mock_filter.return_value = FilterResult(passed=[atom], filtered=[])

        mock_graph = AsyncMock()
        mock_graph.persist_atoms.side_effect = Exception("Connection refused")
        mock_graph_cls.return_value = mock_graph

        mock_client = AsyncMock()
        result = await async_run_pipeline(mock_client)

        # Pipeline still returns atoms even when Neo4j fails
        assert len(result.atoms) == 1
        assert result.atoms[0].summary == "Test decision"


class TestNeo4jDedup:
    """Tests for Neo4j deduplication: skip already-processed threads."""

    @pytest.mark.asyncio
    @patch("evercurrent.pipeline.GraphClient")
    @patch("evercurrent.pipeline.BatchExtractionRunner")
    @patch("evercurrent.pipeline.async_validate_atoms")
    @patch("evercurrent.pipeline.confidence_filter")
    async def test_skips_already_processed_threads(
        self,
        mock_filter: MagicMock,
        mock_validate: MagicMock,
        mock_runner_cls: MagicMock,
        mock_graph_cls: MagicMock,
    ) -> None:
        """Threads with atoms in Neo4j are skipped, reducing extraction calls."""
        atom = _make_atom()
        mock_runner = AsyncMock()
        mock_runner.extract.return_value = [atom]
        mock_runner_cls.return_value = mock_runner
        mock_validate.return_value = [atom]

        from evercurrent.extraction.filter import FilterResult

        mock_filter.return_value = FilterResult(passed=[atom], filtered=[])

        mock_graph = AsyncMock()
        # Return some already-processed thread_ts values
        mock_graph.processed_thread_ts.return_value = {"already.processed.001"}
        mock_graph_cls.return_value = mock_graph

        mock_client = AsyncMock()
        result = await async_run_pipeline(mock_client)

        # Stats should include threads_skipped
        assert "threads_skipped" in result.stats

    @pytest.mark.asyncio
    @patch("evercurrent.pipeline.GraphClient")
    @patch("evercurrent.pipeline.BatchExtractionRunner")
    @patch("evercurrent.pipeline.async_validate_atoms")
    @patch("evercurrent.pipeline.confidence_filter")
    async def test_dedup_failure_processes_all_threads(
        self,
        mock_filter: MagicMock,
        mock_validate: MagicMock,
        mock_runner_cls: MagicMock,
        mock_graph_cls: MagicMock,
    ) -> None:
        """If Neo4j dedup query fails, all threads are processed."""
        atom = _make_atom()
        mock_runner = AsyncMock()
        mock_runner.extract.return_value = [atom]
        mock_runner_cls.return_value = mock_runner
        mock_validate.return_value = [atom]

        from evercurrent.extraction.filter import FilterResult

        mock_filter.return_value = FilterResult(passed=[atom], filtered=[])

        mock_graph = AsyncMock()
        mock_graph.processed_thread_ts.side_effect = Exception("Connection refused")
        mock_graph_cls.return_value = mock_graph

        mock_client = AsyncMock()
        result = await async_run_pipeline(mock_client)

        # Pipeline should still work, processing all threads
        assert result.stats["threads_skipped"] == 0
