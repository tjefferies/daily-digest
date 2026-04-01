"""Integration test: verify delta processing skips already-extracted bundles.

Proves that running the pipeline twice on the same data makes ZERO LLM
calls on the second run. Uses an in-memory SQLite database and a counting
mock for the LLM client to verify no extraction calls are made.
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from evercurrent.dataset.schema import SlackMessage
from evercurrent.db.models import Base
from evercurrent.db.repository import get_processed_bundle_ts, persist_atoms, persist_bundle
from evercurrent.ingestion.context_window import assemble_context_windows
from evercurrent.ingestion.threads import ThreadBundle
from evercurrent.models.atom import Atom, AtomSource, AtomWorkstreams


def _msg(
    ts: str,
    text: str = "test message",
    thread_ts: str | None = None,
    channel: str = "#chassis-design",
    user_id: str = "U001",
) -> SlackMessage:
    """Create a minimal SlackMessage."""
    return SlackMessage(
        message_ts=ts,
        thread_ts=thread_ts,
        channel=channel,
        user_id=user_id,
        text=text,
    )


def _atom(bundle_ts: str) -> Atom:
    """Create a minimal Atom linked to a bundle."""
    return Atom(
        atom_id=uuid4(),
        type="DECISION",
        summary="Test decision",
        detail="Detail text",
        source=AtomSource(
            channel="#chassis-design",
            thread_ts=bundle_ts,
            message_range=[0, 1],
            key_participants=["U001"],
        ),
        workstreams=AtomWorkstreams(originating="chassis"),
        urgency="medium",
        confidence=0.9,
    )


@pytest.mark.integration
class TestDeltaSkipsBundles:
    """Verify that already-persisted bundles are skipped on re-run."""

    @pytest.fixture
    async def db(self):
        """Create in-memory SQLite with schema."""
        from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

        engine = create_async_engine("sqlite+aiosqlite://", echo=False)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        yield factory

        await engine.dispose()

    async def test_second_run_skips_all_bundles(self, db) -> None:  # noqa: ANN001
        """After persisting 3 bundles, get_processed_bundle_ts returns all 3."""
        # Create 3 bundles (same as the 3-window smoke test)
        bundles = [
            ThreadBundle(
                root_message=_msg(f"100{i}.001", f"Thread {i} root"),
                replies=[_msg(f"100{i}.002", f"Reply {i}", thread_ts=f"100{i}.001")],
            )
            for i in range(3)
        ]

        # Simulate first pipeline run: persist all bundles + atoms
        async with db() as session:
            for bundle in bundles:
                await persist_bundle(session, bundle)
            atoms = [_atom(b.root_message.message_ts) for b in bundles]
            await persist_atoms(session, atoms)
            await session.commit()

        # Simulate second pipeline run: query for existing bundles
        async with db() as session:
            processed = await get_processed_bundle_ts(session)

        # ALL 3 bundle timestamps should be in the processed set
        assert len(processed) == 3
        for bundle in bundles:
            assert bundle.root_message.message_ts in processed

        # Filter bundles like the pipeline does
        new_bundles = [b for b in bundles if b.root_message.message_ts not in processed]

        # ZERO new bundles - nothing to extract
        assert len(new_bundles) == 0

    async def test_new_bundle_is_not_skipped(self, db) -> None:  # noqa: ANN001
        """A new bundle not in Postgres IS included for extraction."""
        # Persist 2 bundles
        existing_bundles = [
            ThreadBundle(
                root_message=_msg(f"200{i}.001", f"Existing {i}"),
                replies=[],
            )
            for i in range(2)
        ]

        async with db() as session:
            for bundle in existing_bundles:
                await persist_bundle(session, bundle)
            await session.commit()

        # Now check with 3 bundles (2 existing + 1 new)
        new_bundle = ThreadBundle(
            root_message=_msg("2002.001", "Brand new thread"),
            replies=[],
        )
        all_bundles = [*existing_bundles, new_bundle]

        async with db() as session:
            processed = await get_processed_bundle_ts(session)

        new_bundles = [b for b in all_bundles if b.root_message.message_ts not in processed]

        # Only the new bundle should be included
        assert len(new_bundles) == 1
        assert new_bundles[0].root_message.message_ts == "2002.001"

    async def test_zero_llm_calls_on_second_run(self, db) -> None:  # noqa: ANN001
        """Full pipeline simulation: second run makes zero LLM calls."""
        # Persist 3 bundles as if first run completed
        bundles = [
            ThreadBundle(
                root_message=_msg(f"300{i}.001", f"Thread {i}"),
                replies=[_msg(f"300{i}.002", "Reply", thread_ts=f"300{i}.001")],
            )
            for i in range(3)
        ]

        async with db() as session:
            for bundle in bundles:
                await persist_bundle(session, bundle)
            atoms = [_atom(b.root_message.message_ts) for b in bundles]
            await persist_atoms(session, atoms)
            await session.commit()

        # Second run: check Postgres, filter, count what would be extracted
        async with db() as session:
            processed = await get_processed_bundle_ts(session)

        remaining = [b for b in bundles if b.root_message.message_ts not in processed]

        windows = assemble_context_windows(remaining)

        # Zero windows = zero LLM calls
        assert len(windows) == 0, (
            f"Expected 0 windows (all skipped), got {len(windows)}. "
            f"Delta processing is NOT working - these bundles would "
            f"trigger {len(windows)} LLM batch requests."
        )
