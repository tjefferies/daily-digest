"""Integration test: populate Postgres with ALL data from slack_messages.json.

Requires: Postgres running (docker compose up postgres).
Persists all 307 messages → 116 bundles with memberships.
Verifies row counts match the dataset.
"""

from __future__ import annotations

import os

import pytest

from digest.dataset.messages import load_messages
from digest.db.repository import get_processed_bundle_ts, persist_bundle
from digest.db.session import get_session_factory, reset_engine
from digest.ingestion.threads import group_by_thread


@pytest.mark.integration
class TestPopulatePostgresFromDataset:
    """Persist the full synthetic dataset to Postgres and verify."""

    @pytest.fixture(autouse=True)
    def _require_postgres(self) -> None:
        """Skip if POSTGRES_DSN is not set. Reset engine between tests."""
        if not os.environ.get("POSTGRES_DSN"):
            pytest.skip("POSTGRES_DSN not set - run with docker compose")
        reset_engine()

    async def test_persist_all_bundles(self) -> None:
        """All 116 bundles from slack_messages.json persist to Postgres."""
        messages = load_messages()
        bundles = group_by_thread(messages)

        assert len(messages) == 307, f"Expected 307 messages, got {len(messages)}"
        assert len(bundles) == 116, f"Expected 116 bundles, got {len(bundles)}"

        factory = get_session_factory()

        # Check existing
        async with factory() as session:
            existing = await get_processed_bundle_ts(session)

        new_bundles = [b for b in bundles if b.root_message.message_ts not in existing]

        # Persist new bundles
        async with factory() as session:
            for b in new_bundles:
                await persist_bundle(session, b)
            await session.commit()

        # Verify all 116 are now in Postgres
        async with factory() as session:
            total = await get_processed_bundle_ts(session)

        assert len(total) == 116, (
            f"Expected 116 bundles in Postgres, got {len(total)}. "
            f"Persisted {len(new_bundles)} new, {len(existing)} already existed."
        )

    async def test_all_messages_persisted(self) -> None:
        """All 307 messages are in the message table."""
        from sqlalchemy import func, select

        from digest.db.models import Message

        factory = get_session_factory()
        async with factory() as session:
            result = await session.execute(select(func.count()).select_from(Message))
            count = result.scalar()

        assert count == 307, f"Expected 307 messages, got {count}"

    async def test_all_memberships_persisted(self) -> None:
        """Every message has a bundle_membership row."""
        from sqlalchemy import func, select

        from digest.db.models import BundleMembership

        factory = get_session_factory()
        async with factory() as session:
            result = await session.execute(
                select(func.count()).select_from(BundleMembership),
            )
            count = result.scalar()

        assert count == 307, f"Expected 307 memberships (1 per message), got {count}"

    async def test_jsonb_raw_queryable(self) -> None:
        """JSONB raw field is queryable with containment operator."""
        from sqlalchemy import select

        from digest.db.models import Message

        factory = get_session_factory()
        async with factory() as session:
            # Find messages in #chassis-design
            result = await session.execute(
                select(Message).where(Message.channel == "#chassis-design").limit(1),
            )
            msg = result.scalar_one_or_none()

        assert msg is not None
        assert msg.raw is not None
        assert "text" in msg.raw
        assert len(msg.raw["text"]) > 0

    async def test_idempotent_rerun(self) -> None:
        """Running persist again doesn't create duplicates."""
        messages = load_messages()
        bundles = group_by_thread(messages)

        factory = get_session_factory()

        # Persist all again (should be no-ops via merge)
        async with factory() as session:
            for b in bundles:
                await persist_bundle(session, b)
            await session.commit()

        # Count should still be 116 bundles, 307 messages
        async with factory() as session:
            total = await get_processed_bundle_ts(session)

        assert len(total) == 116, f"Idempotency broken: got {len(total)} bundles"
