"""Integration test: bundle+atom round-trip using in-memory SQLite.

Verifies persist and query operations for bundles and atoms
without requiring a running Postgres instance.
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from digest.dataset.schema import SlackMessage
from digest.db.models import Base
from digest.db.repository import get_processed_bundle_ts, persist_atoms, persist_bundle
from digest.ingestion.threads import ThreadBundle
from digest.models.atom import Atom, AtomSource, AtomWorkstreams


def _msg(ts: str, text: str = "test", thread_ts: str | None = None) -> SlackMessage:
    """Create a minimal SlackMessage."""
    return SlackMessage(
        message_ts=ts,
        thread_ts=thread_ts,
        channel="#test",
        user_id="U001",
        text=text,
    )


@pytest.mark.integration
class TestPostgresRoundTrip:
    """Write bundles and atoms to in-memory SQLite, read back."""

    @pytest.fixture
    async def session(self):
        """Create an in-memory SQLite session for testing.

        Uses SQLite to avoid requiring a running Postgres instance
        for unit-level integration tests. Full Postgres tests require
        docker compose up postgres.
        """
        from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

        engine = create_async_engine("sqlite+aiosqlite://", echo=False)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as session:
            yield session

        await engine.dispose()

    async def test_persist_and_query_bundle(self, session) -> None:  # noqa: ANN001
        """Bundle persisted to SQLite is found by get_processed_bundle_ts."""
        root = _msg("1000.001", "root message")
        reply = _msg("1000.002", "reply", thread_ts="1000.001")
        bundle = ThreadBundle(root_message=root, replies=[reply])

        await persist_bundle(session, bundle)
        await session.commit()

        processed = await get_processed_bundle_ts(session)
        assert "1000.001" in processed

    async def test_persist_atom_with_bundle_fk(self, session) -> None:  # noqa: ANN001
        """Atom persisted with source_bundle_ts FK matches the bundle."""
        root = _msg("2000.001", "root")
        bundle = ThreadBundle(root_message=root, replies=[])
        await persist_bundle(session, bundle)

        atom = Atom(
            atom_id=uuid4(),
            type="DECISION",
            summary="Test decision",
            detail="Detail",
            source=AtomSource(
                channel="#test",
                thread_ts="2000.001",
                message_range=[0, 0],
                key_participants=["U001"],
            ),
            workstreams=AtomWorkstreams(originating="chassis"),
            urgency="medium",
            confidence=0.9,
        )
        await persist_atoms(session, [atom])
        await session.commit()

        # Verify atom is queryable
        from sqlalchemy import select

        from digest.db.models import Atom as AtomRow

        result = await session.execute(select(AtomRow))
        rows = result.scalars().all()
        assert len(rows) == 1
        assert rows[0].summary == "Test decision"
        assert rows[0].source_bundle_ts == "2000.001"
