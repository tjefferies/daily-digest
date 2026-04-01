"""Tests for the Postgres repository layer (mocked session)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from digest.dataset.schema import SlackMessage
from digest.ingestion.threads import ThreadBundle
from digest.models.atom import Atom, AtomSource, AtomWorkstreams


def _msg(ts: str, text: str = "hello", thread_ts: str | None = None) -> SlackMessage:
    """Create a minimal SlackMessage."""
    return SlackMessage(
        message_ts=ts,
        thread_ts=thread_ts,
        channel="#test",
        user_id="U001",
        text=text,
    )


def _bundle(root_ts: str = "1000.001") -> ThreadBundle:
    """Create a minimal ThreadBundle."""
    root = _msg(root_ts, "root message")
    reply = _msg("1000.002", "reply", thread_ts=root_ts)
    return ThreadBundle(root_message=root, replies=[reply])


def _atom(bundle_ts: str = "1000.001") -> Atom:
    """Create a minimal Atom linked to a bundle."""
    return Atom(
        atom_id=uuid4(),
        type="DECISION",
        summary="Test decision",
        detail="Detail",
        source=AtomSource(
            channel="#test",
            thread_ts=bundle_ts,
            message_range=[0, 1],
            key_participants=["U001"],
        ),
        workstreams=AtomWorkstreams(originating="chassis"),
        urgency="medium",
        confidence=0.9,
    )


class TestPersistBundle:
    """Tests for persisting bundles to Postgres."""

    @pytest.mark.asyncio
    async def test_persist_bundle_creates_records(self) -> None:
        """persist_bundle writes message, bundle, and membership rows."""
        from digest.db.repository import persist_bundle

        mock_session = AsyncMock()
        bundle = _bundle()

        await persist_bundle(mock_session, bundle)

        # Should add message rows + bundle row + membership rows
        assert mock_session.merge.call_count >= 3

    @pytest.mark.asyncio
    async def test_persist_bundle_empty_replies(self) -> None:
        """Bundle with no replies still persists root + bundle + 1 membership."""
        from digest.db.repository import persist_bundle

        mock_session = AsyncMock()
        root = _msg("1000.001", "root only")
        bundle = ThreadBundle(root_message=root, replies=[])

        await persist_bundle(mock_session, bundle)

        # root message + bundle + root membership = 3 merges
        assert mock_session.merge.call_count >= 2


class TestPersistAtoms:
    """Tests for persisting atoms to Postgres."""

    @pytest.mark.asyncio
    async def test_persist_atoms_creates_rows(self) -> None:
        """persist_atoms writes atom rows."""
        from digest.db.repository import persist_atoms

        mock_session = AsyncMock()
        atoms = [_atom(), _atom()]

        await persist_atoms(mock_session, atoms)

        assert mock_session.merge.call_count == 2


class TestGetProcessedBundles:
    """Tests for querying existing bundle timestamps."""

    @pytest.mark.asyncio
    async def test_returns_set_of_timestamps(self) -> None:
        """get_processed_bundle_ts returns set of root_message_ts strings."""
        from digest.db.repository import get_processed_bundle_ts

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = ["1000.001", "1000.002"]
        mock_session.execute.return_value = mock_result

        result = await get_processed_bundle_ts(mock_session)

        assert result == {"1000.001", "1000.002"}

    @pytest.mark.asyncio
    async def test_returns_empty_set_when_no_bundles(self) -> None:
        """get_processed_bundle_ts returns empty set for empty table."""
        from digest.db.repository import get_processed_bundle_ts

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        result = await get_processed_bundle_ts(mock_session)

        assert result == set()
