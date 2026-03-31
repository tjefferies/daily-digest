"""Tests for the pipeline orchestrator module (sync and async)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

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

    @patch("evercurrent.pipeline.AsyncExtractionRunner")
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

    @patch("evercurrent.pipeline.AsyncExtractionRunner")
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

    @patch("evercurrent.pipeline.AsyncExtractionRunner")
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
