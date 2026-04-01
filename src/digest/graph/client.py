"""Neo4j graph client for persistent atom storage.

Provides an async interface for persisting extracted atoms to a Neo4j
knowledge graph and querying them with temporal filters. Uses the
official neo4j async driver over the Bolt protocol.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any, LiteralString

from neo4j import AsyncGraphDatabase

from digest.models.atom import Atom, AtomSource, AtomWorkstreams  # noqa: TC001

if TYPE_CHECKING:
    from neo4j import AsyncDriver

logger = logging.getLogger(__name__)

# Schema DDL executed once on startup.
_SCHEMA_STATEMENTS: list[LiteralString] = [
    "CREATE CONSTRAINT atom_id IF NOT EXISTS FOR (a:Atom) REQUIRE a.atom_id IS UNIQUE",
    "CREATE INDEX atom_type IF NOT EXISTS FOR (a:Atom) ON (a.type)",
    "CREATE INDEX atom_created IF NOT EXISTS FOR (a:Atom) ON (a.created_at)",
]

_PERSIST_ATOM_CYPHER = """\
MERGE (a:Atom {atom_id: $atom_id})
SET a.type = $type,
    a.summary = $summary,
    a.detail = $detail,
    a.urgency = $urgency,
    a.confidence = $confidence,
    a.implicit_decision = $implicit_decision,
    a.phase_relevance = $phase_relevance,
    a.channel = $channel,
    a.thread_ts = $thread_ts,
    a.created_at = coalesce(a.created_at, datetime($created_at))
MERGE (ch:Channel {name: $channel})
MERGE (a)-[:EXTRACTED_FROM {thread_ts: $thread_ts}]->(ch)
MERGE (ws_orig:Workstream {name: $originating})
MERGE (a)-[:ORIGINATES_IN]->(ws_orig)
WITH a
UNWIND $affected AS affected_name
MERGE (ws_aff:Workstream {name: affected_name})
MERGE (a)-[:AFFECTS]->(ws_aff)
WITH a
UNWIND $participants AS handle
MERGE (p:Participant {handle: handle})
MERGE (a)-[:INVOLVES]->(p)
"""

_ATOMS_SINCE_CYPHER = """\
MATCH (a:Atom)
WHERE a.created_at > datetime($since)
RETURN a.type AS type, a.summary AS summary,
       a.urgency AS urgency, a.confidence AS confidence,
       a.created_at AS created_at
ORDER BY a.created_at DESC
"""

_SPEC_CHANGES_CYPHER = """\
MATCH (a:Atom {type: 'SPEC_CHANGE'})-[:EXTRACTED_FROM]->(ch:Channel)
WHERE a.created_at > datetime($since)
RETURN a.summary AS summary, ch.name AS channel,
       a.urgency AS urgency, a.detail AS detail,
       a.created_at AS created_at
ORDER BY a.urgency DESC, a.created_at DESC
"""

_BLOCKER_PATTERNS_CYPHER = """\
MATCH (a:Atom {type: 'BLOCKER'})-[:ORIGINATES_IN]->(ws:Workstream)
OPTIONAL MATCH (a)-[:AFFECTS]->(affected:Workstream)
WITH ws.name AS workstream,
     collect(DISTINCT a.summary) AS summaries,
     collect(DISTINCT affected.name) AS affected_teams,
     count(DISTINCT a) AS blocker_count
RETURN workstream, blocker_count, summaries, affected_teams
ORDER BY blocker_count DESC
"""

_LOAD_ALL_ATOMS_CYPHER = """\
MATCH (a:Atom)
OPTIONAL MATCH (a)-[:ORIGINATES_IN]->(ws_orig:Workstream)
OPTIONAL MATCH (a)-[:AFFECTS]->(ws_aff:Workstream)
OPTIONAL MATCH (a)-[:INVOLVES]->(p:Participant)
RETURN a.atom_id AS atom_id, a.type AS type, a.summary AS summary,
       a.detail AS detail, a.urgency AS urgency, a.confidence AS confidence,
       a.implicit_decision AS implicit_decision, a.phase_relevance AS phase_relevance,
       a.channel AS channel, a.thread_ts AS thread_ts,
       a.created_at AS created_at,
       ws_orig.name AS originating,
       collect(DISTINCT ws_aff.name) AS affected,
       collect(DISTINCT p.handle) AS participants
ORDER BY created_at DESC
"""

_PROCESSED_THREAD_TS_CYPHER = """\
MATCH (a:Atom)
WHERE a.thread_ts IS NOT NULL
RETURN DISTINCT a.thread_ts AS thread_ts
"""

_ATOM_COUNT_CYPHER = "MATCH (a:Atom) RETURN count(a) AS count"


class GraphClient:
    """Async Neo4j client for the EverCurrent knowledge graph.

    Wraps the neo4j AsyncDriver to provide typed methods for
    persisting atoms and running temporal queries.

    Args:
        uri: Bolt connection URI (e.g. ``bolt://localhost:7687``).
        user: Neo4j username.
        password: Neo4j password.
    """

    def __init__(self, uri: str, user: str, password: str) -> None:
        """Initialize the graph client with connection parameters.

        Args:
            uri: Bolt connection URI (e.g. ``bolt://localhost:7687``).
            user: Neo4j username.
            password: Neo4j password.
        """
        self._driver: AsyncDriver = AsyncGraphDatabase.driver(uri, auth=(user, password))

    async def close(self) -> None:
        """Close the underlying driver connection."""
        await self._driver.close()

    async def ensure_schema(self) -> None:
        """Create constraints and indexes if they don't exist.

        Idempotent - safe to call on every startup.
        """
        async with self._driver.session() as session:
            for stmt in _SCHEMA_STATEMENTS:
                await session.run(stmt)
        logger.info("Graph schema ensured (%d statements)", len(_SCHEMA_STATEMENTS))

    async def persist_atoms(self, atoms: list[Atom]) -> None:
        """Persist a list of atoms to the knowledge graph.

        Uses MERGE for idempotent upserts. Creates node and
        relationship structure: Atom -> Channel, Workstream, Participant.

        Args:
            atoms: Atoms to persist. Empty list is a no-op.
        """
        if not atoms:
            return

        now = datetime.now(tz=UTC).isoformat()
        async with self._driver.session() as session:
            for atom in atoms:
                params = _atom_to_params(atom, now)
                await session.run(_PERSIST_ATOM_CYPHER, params)
        logger.info("Persisted %d atoms to graph", len(atoms))

    async def atoms_since(self, since: datetime) -> list[dict[str, Any]]:
        """Return atoms created after a given timestamp.

        Args:
            since: Cutoff datetime (UTC). Only atoms newer are returned.

        Returns:
            List of dicts with type, summary, urgency, confidence, created_at.
        """
        async with self._driver.session() as session:
            result = await session.run(_ATOMS_SINCE_CYPHER, {"since": since.isoformat()})
            return await result.data()

    async def spec_changes_this_week(self) -> list[dict[str, Any]]:
        """Return SPEC_CHANGE atoms from the past 7 days.

        Returns:
            List of dicts with summary, channel, urgency, detail, created_at.
        """
        since = datetime.now(tz=UTC) - timedelta(days=7)
        async with self._driver.session() as session:
            result = await session.run(_SPEC_CHANGES_CYPHER, {"since": since.isoformat()})
            return await result.data()

    async def blocker_patterns(self) -> list[dict[str, Any]]:
        """Return BLOCKER atoms grouped by workstream.

        Returns:
            List of dicts with workstream, blocker_count, summaries,
            affected_teams.
        """
        async with self._driver.session() as session:
            result = await session.run(_BLOCKER_PATTERNS_CYPHER)
            return await result.data()

    async def load_all_atoms(self) -> list[Atom]:
        """Load all atoms from Neo4j as full Atom objects.

        Reconstructs Atom objects with source, workstreams, and
        participant data from graph relationships.

        Returns:
            List of Atom objects from the graph.
        """
        async with self._driver.session() as session:
            result = await session.run(_LOAD_ALL_ATOMS_CYPHER)
            records = await result.data()

        atoms: list[Atom] = []
        for r in records:
            atoms.append(
                Atom(
                    atom_id=r["atom_id"],
                    type=r["type"],
                    summary=r["summary"],
                    detail=r["detail"] or "",
                    source=AtomSource(
                        channel=r["channel"] or "",
                        thread_ts=r["thread_ts"] or "",
                        message_range=[0, 0],
                        key_participants=r["participants"],
                    ),
                    workstreams=AtomWorkstreams(
                        originating=r["originating"] or "",
                        affected=[a for a in r["affected"] if a],
                    ),
                    urgency=r["urgency"],
                    confidence=r["confidence"],
                    implicit_decision=r.get("implicit_decision", False),
                    phase_relevance=r.get("phase_relevance", []),
                ),
            )
        logger.info("Loaded %d atoms from graph", len(atoms))
        return atoms

    async def processed_thread_ts(self) -> set[str]:
        """Return the set of thread_ts values that already have atoms.

        Used for deduplication: threads with existing atoms can be
        skipped on subsequent pipeline runs.

        Returns:
            Set of thread_ts strings already in the graph.
        """
        async with self._driver.session() as session:
            result = await session.run(_PROCESSED_THREAD_TS_CYPHER)
            records = await result.data()
            return {r["thread_ts"] for r in records}

    async def atom_count(self) -> int:
        """Return the total number of atom nodes in the graph.

        Returns:
            Integer count of :Atom nodes.
        """
        async with self._driver.session() as session:
            result = await session.run(_ATOM_COUNT_CYPHER)
            record = await result.single()
            if record is None:
                return 0
            return record["count"]


def _atom_to_params(atom: Atom, created_at: str) -> dict[str, Any]:
    """Convert an Atom to a flat parameter dict for Cypher.

    Args:
        atom: The atom to convert.
        created_at: ISO 8601 timestamp for the created_at property.

    Returns:
        Dict of parameter names to values for the MERGE query.
    """
    return {
        "atom_id": str(atom.atom_id),
        "type": atom.type,
        "summary": atom.summary,
        "detail": atom.detail,
        "urgency": atom.urgency,
        "confidence": atom.confidence,
        "implicit_decision": atom.implicit_decision,
        "phase_relevance": list(atom.phase_relevance),
        "channel": atom.source.channel,
        "thread_ts": atom.source.thread_ts,
        "originating": atom.workstreams.originating,
        "affected": list(atom.workstreams.affected),
        "participants": list(atom.source.key_participants),
        "created_at": created_at,
    }
