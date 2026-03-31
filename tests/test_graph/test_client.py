"""Tests for the Neo4j graph client module.

Validates atom persistence, temporal queries, schema initialization,
and connection lifecycle. Neo4j driver is mocked (system boundary).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from evercurrent.models.atom import Atom, AtomSource, AtomWorkstreams

_TEST_PASSWORD = "test"  # noqa: S105


def _make_atom(**overrides: Any) -> Atom:  # noqa: ANN401
    """Build a test atom with sensible defaults."""
    defaults: dict[str, Any] = {
        "atom_id": uuid4(),
        "type": "DECISION",
        "summary": "Switch to titanium housing",
        "detail": "Team agreed to use titanium for thermal reasons.",
        "source": AtomSource(
            channel="#chassis-design",
            thread_ts="1711900000.000100",
            message_range=[0, 3],
            key_participants=["U001", "U003"],
        ),
        "workstreams": AtomWorkstreams(
            originating="chassis",
            affected=["thermal", "supply-chain"],
        ),
        "urgency": "high",
        "confidence": 0.92,
        "implicit_decision": False,
        "phase_relevance": ["DVT"],
    }
    defaults.update(overrides)
    return Atom(**defaults)


def _make_mock_driver_and_session() -> tuple[MagicMock, AsyncMock]:
    """Build a mock driver whose session() returns an async context manager.

    neo4j's AsyncDriver.session() is a sync call returning an
    AsyncSession (async context manager). We replicate that here.

    Returns:
        Tuple of (mock_driver, mock_session).
    """
    mock_session = AsyncMock()
    # session() is sync, returns an object with __aenter__/__aexit__
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=mock_session)
    ctx.__aexit__ = AsyncMock(return_value=False)
    mock_driver = MagicMock()
    mock_driver.session.return_value = ctx
    # close() is async
    mock_driver.close = AsyncMock()
    return mock_driver, mock_session


class TestGraphClientInit:
    """Verify client initialization and connection lifecycle."""

    async def test_create_client_stores_driver(self) -> None:
        """GraphClient stores the driver instance."""
        with patch("evercurrent.graph.client.AsyncGraphDatabase") as mock_agd:
            mock_driver, _ = _make_mock_driver_and_session()
            mock_agd.driver.return_value = mock_driver
            from evercurrent.graph.client import GraphClient

            client = GraphClient(
                uri="bolt://localhost:7687",
                user="neo4j",
                password=_TEST_PASSWORD,
            )
            assert client._driver is not None
            mock_agd.driver.assert_called_once_with(
                "bolt://localhost:7687", auth=("neo4j", "test")
            )

    async def test_close_shuts_down_driver(self) -> None:
        """close() calls driver.close()."""
        with patch("evercurrent.graph.client.AsyncGraphDatabase") as mock_agd:
            mock_driver, _ = _make_mock_driver_and_session()
            mock_agd.driver.return_value = mock_driver
            from evercurrent.graph.client import GraphClient

            client = GraphClient(
                uri="bolt://localhost:7687", user="neo4j", password=_TEST_PASSWORD
            )
            await client.close()
            mock_driver.close.assert_awaited_once()


class TestEnsureSchema:
    """Verify schema initialization creates constraints and indexes."""

    async def test_ensure_schema_runs_constraint_queries(self) -> None:
        """ensure_schema() must execute constraint and index Cypher."""
        with patch("evercurrent.graph.client.AsyncGraphDatabase") as mock_agd:
            mock_driver, mock_session = _make_mock_driver_and_session()
            mock_agd.driver.return_value = mock_driver
            from evercurrent.graph.client import GraphClient

            client = GraphClient(
                uri="bolt://localhost:7687", user="neo4j", password=_TEST_PASSWORD
            )
            await client.ensure_schema()

            assert mock_session.run.await_count >= 3, (
                "Expected at least 3 schema statements (constraint + indexes)"
            )


class TestPersistAtom:
    """Verify atom persistence to graph."""

    async def test_persist_atom_runs_merge_query(self) -> None:
        """persist_atoms() must MERGE atom nodes into the graph."""
        with patch("evercurrent.graph.client.AsyncGraphDatabase") as mock_agd:
            mock_driver, mock_session = _make_mock_driver_and_session()
            mock_agd.driver.return_value = mock_driver
            from evercurrent.graph.client import GraphClient

            client = GraphClient(
                uri="bolt://localhost:7687", user="neo4j", password=_TEST_PASSWORD
            )
            atom = _make_atom()
            await client.persist_atoms([atom])

            assert mock_session.run.await_count >= 1
            cypher_query = mock_session.run.call_args_list[0][0][0]
            assert "MERGE" in cypher_query

    async def test_persist_atom_includes_workstream_edges(self) -> None:
        """persist_atoms() must create workstream relationship edges."""
        with patch("evercurrent.graph.client.AsyncGraphDatabase") as mock_agd:
            mock_driver, mock_session = _make_mock_driver_and_session()
            mock_agd.driver.return_value = mock_driver
            from evercurrent.graph.client import GraphClient

            client = GraphClient(
                uri="bolt://localhost:7687", user="neo4j", password=_TEST_PASSWORD
            )
            atom = _make_atom(
                workstreams=AtomWorkstreams(originating="chassis", affected=["thermal"]),
            )
            await client.persist_atoms([atom])

            all_cypher = " ".join(str(c[0][0]) for c in mock_session.run.call_args_list)
            assert "Workstream" in all_cypher or "ORIGINATES_IN" in all_cypher

    async def test_persist_multiple_atoms(self) -> None:
        """persist_atoms() handles a list of atoms."""
        with patch("evercurrent.graph.client.AsyncGraphDatabase") as mock_agd:
            mock_driver, mock_session = _make_mock_driver_and_session()
            mock_agd.driver.return_value = mock_driver
            from evercurrent.graph.client import GraphClient

            client = GraphClient(
                uri="bolt://localhost:7687", user="neo4j", password=_TEST_PASSWORD
            )
            atoms = [_make_atom() for _ in range(3)]
            await client.persist_atoms(atoms)

            assert mock_session.run.await_count >= 3

    async def test_persist_empty_list_is_noop(self) -> None:
        """persist_atoms([]) should not execute any queries."""
        with patch("evercurrent.graph.client.AsyncGraphDatabase") as mock_agd:
            mock_driver, mock_session = _make_mock_driver_and_session()
            mock_agd.driver.return_value = mock_driver
            from evercurrent.graph.client import GraphClient

            client = GraphClient(
                uri="bolt://localhost:7687", user="neo4j", password=_TEST_PASSWORD
            )
            await client.persist_atoms([])
            mock_session.run.assert_not_awaited()


class TestTemporalQueries:
    """Verify temporal query methods return structured results."""

    async def test_atoms_since_returns_records(self) -> None:
        """atoms_since() must run a datetime-filtered Cypher query."""
        with patch("evercurrent.graph.client.AsyncGraphDatabase") as mock_agd:
            mock_driver, mock_session = _make_mock_driver_and_session()
            mock_result = AsyncMock()
            mock_result.data.return_value = [
                {"type": "DECISION", "summary": "test", "urgency": "high"},
            ]
            mock_session.run.return_value = mock_result
            mock_agd.driver.return_value = mock_driver
            from evercurrent.graph.client import GraphClient

            client = GraphClient(
                uri="bolt://localhost:7687", user="neo4j", password=_TEST_PASSWORD
            )
            since = datetime.now(tz=UTC) - timedelta(days=1)
            results = await client.atoms_since(since)

            assert isinstance(results, list)
            cypher = mock_session.run.call_args_list[0][0][0]
            assert "created_at" in cypher

    async def test_spec_changes_this_week_filters_by_type(self) -> None:
        """spec_changes_this_week() must filter for SPEC_CHANGE atoms."""
        with patch("evercurrent.graph.client.AsyncGraphDatabase") as mock_agd:
            mock_driver, mock_session = _make_mock_driver_and_session()
            mock_result = AsyncMock()
            mock_result.data.return_value = []
            mock_session.run.return_value = mock_result
            mock_agd.driver.return_value = mock_driver
            from evercurrent.graph.client import GraphClient

            client = GraphClient(
                uri="bolt://localhost:7687", user="neo4j", password=_TEST_PASSWORD
            )
            results = await client.spec_changes_this_week()

            assert isinstance(results, list)
            cypher = mock_session.run.call_args_list[0][0][0]
            assert "SPEC_CHANGE" in cypher

    async def test_blocker_patterns_groups_by_workstream(self) -> None:
        """blocker_patterns() must group BLOCKER atoms by workstream."""
        with patch("evercurrent.graph.client.AsyncGraphDatabase") as mock_agd:
            mock_driver, mock_session = _make_mock_driver_and_session()
            mock_result = AsyncMock()
            mock_result.data.return_value = [
                {"workstream": "chassis", "blocker_count": 2, "summaries": ["a", "b"]},
            ]
            mock_session.run.return_value = mock_result
            mock_agd.driver.return_value = mock_driver
            from evercurrent.graph.client import GraphClient

            client = GraphClient(
                uri="bolt://localhost:7687", user="neo4j", password=_TEST_PASSWORD
            )
            results = await client.blocker_patterns()

            assert isinstance(results, list)
            cypher = mock_session.run.call_args_list[0][0][0]
            assert "BLOCKER" in cypher


class TestAtomCount:
    """Verify atom count query method."""

    async def test_atom_count_returns_integer(self) -> None:
        """atom_count() must return the total number of atoms in the graph."""
        with patch("evercurrent.graph.client.AsyncGraphDatabase") as mock_agd:
            mock_driver, mock_session = _make_mock_driver_and_session()
            mock_result = AsyncMock()
            mock_record = {"count": 42}
            mock_result.single.return_value = mock_record
            mock_session.run.return_value = mock_result
            mock_agd.driver.return_value = mock_driver
            from evercurrent.graph.client import GraphClient

            client = GraphClient(
                uri="bolt://localhost:7687", user="neo4j", password=_TEST_PASSWORD
            )
            count = await client.atom_count()

            assert count == 42
