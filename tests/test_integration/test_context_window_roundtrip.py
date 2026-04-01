"""Integration test: context_window table stores what the LLM saw.

Proves the full path: message → bundle → context_window → atom.
Uses in-memory SQLite.
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from digest.dataset.schema import SlackMessage
from digest.db.models import Atom as AtomRow
from digest.db.models import Base
from digest.db.repository import (
    persist_atoms,
    persist_bundle,
    persist_context_windows,
)
from digest.ingestion.context_window import assemble_context_windows
from digest.ingestion.threads import ThreadBundle
from digest.models.atom import Atom, AtomSource, AtomWorkstreams


def _msg(ts: str, text: str, thread_ts: str | None = None) -> SlackMessage:
    """Create a minimal SlackMessage."""
    return SlackMessage(
        message_ts=ts,
        thread_ts=thread_ts,
        channel="#test",
        user_id="U001",
        text=text,
    )


@pytest.mark.integration
class TestContextWindowRoundTrip:
    """Verify message → bundle → context_window → atom path in Postgres."""

    @pytest.fixture
    async def session(self):
        """In-memory SQLite with full schema."""
        from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

        engine = create_async_engine("sqlite+aiosqlite://", echo=False)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as session:
            yield session

        await engine.dispose()

    async def test_context_window_stores_raw_jsonb(self, session) -> None:  # noqa: ANN001
        """ContextWindow.raw contains the full thread_text the LLM received."""
        root = _msg("5000.001", "Root message about snap fit")
        reply = _msg("5000.002", "Reply about draft angle", thread_ts="5000.001")
        bundle = ThreadBundle(root_message=root, replies=[reply])

        await persist_bundle(session, bundle)

        windows = assemble_context_windows([bundle])
        assert len(windows) == 1

        await persist_context_windows(session, windows)
        await session.commit()

        # Query back
        from sqlalchemy import select

        from digest.db.models import ContextWindow as CWRow

        result = await session.execute(select(CWRow))
        row = result.scalar_one()

        assert row.bundle_ts == "5000.001"
        assert row.channel == "#test"
        assert "snap fit" in row.raw["thread_text"]
        assert "draft angle" in row.raw["thread_text"]

    async def test_atom_links_to_context_window(self, session) -> None:  # noqa: ANN001
        """Atom.source_bundle_ts FK chains through context_window to bundle."""
        root = _msg("6000.001", "Motor torque discussion")
        bundle = ThreadBundle(root_message=root, replies=[])

        await persist_bundle(session, bundle)

        windows = assemble_context_windows([bundle])
        await persist_context_windows(session, windows)

        atom = Atom(
            atom_id=uuid4(),
            type="DECISION",
            summary="Torque spec updated to 3.1Nm",
            detail="Detail",
            source=AtomSource(
                channel="#test",
                thread_ts="6000.001",
                message_range=[0, 0],
                key_participants=["U001"],
            ),
            workstreams=AtomWorkstreams(originating="drivetrain"),
            urgency="high",
            confidence=0.92,
        )
        await persist_atoms(session, [atom])
        await session.commit()

        # Query: atom → context_window → verify thread_text
        from sqlalchemy import select

        from digest.db.models import ContextWindow as CWRow

        result = await session.execute(
            select(CWRow).where(CWRow.bundle_ts == "6000.001"),
        )
        cw = result.scalar_one()

        result2 = await session.execute(
            select(AtomRow).where(AtomRow.source_bundle_ts == "6000.001"),
        )
        atom_row = result2.scalar_one()

        assert atom_row.summary == "Torque spec updated to 3.1Nm"
        assert atom_row.source_bundle_ts == cw.bundle_ts
        assert "Motor torque" in cw.raw["thread_text"]

    async def test_full_path_message_to_atom(self, session) -> None:  # noqa: ANN001
        """Full chain: message → bundle_membership → bundle → context_window → atom."""
        from sqlalchemy import select

        from digest.db.models import BundleMembership
        from digest.db.models import ContextWindow as CWRow

        root = _msg("7000.001", "Thermal pad spec")
        reply = _msg("7000.002", "Updated to Fujipoly", thread_ts="7000.001")
        bundle = ThreadBundle(root_message=root, replies=[reply])

        await persist_bundle(session, bundle)
        windows = assemble_context_windows([bundle])
        await persist_context_windows(session, windows)

        atom = Atom(
            atom_id=uuid4(),
            type="SPEC_CHANGE",
            summary="TIM changed to Fujipoly",
            detail="Detail",
            source=AtomSource(
                channel="#test",
                thread_ts="7000.001",
                message_range=[0, 1],
                key_participants=["U001"],
            ),
            workstreams=AtomWorkstreams(originating="thermal"),
            urgency="medium",
            confidence=0.88,
        )
        await persist_atoms(session, [atom])
        await session.commit()

        # Trace: message → membership → bundle → context_window → atom
        memberships = await session.execute(
            select(BundleMembership).where(BundleMembership.bundle_ts == "7000.001"),
        )
        members = memberships.scalars().all()
        assert len(members) == 2  # root + reply

        cw = await session.execute(select(CWRow).where(CWRow.bundle_ts == "7000.001"))
        window = cw.scalar_one()
        assert "Fujipoly" in window.raw["thread_text"]

        atoms = await session.execute(
            select(AtomRow).where(AtomRow.source_bundle_ts == "7000.001"),
        )
        atom_row = atoms.scalar_one()
        assert atom_row.summary == "TIM changed to Fujipoly"
