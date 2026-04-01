"""Async Postgres repository for bundle and atom persistence.

Provides functions to persist ThreadBundles and Atoms to Postgres
via SQLAlchemy async sessions, and to query for existing bundles
to enable delta processing (skip unchanged bundles on re-run).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from sqlalchemy import select

from evercurrent.db.models import (
    Atom as AtomRow,
)
from evercurrent.db.models import (
    BundleMembership,
    BundleRole,
    Message,
    ThreadBundle,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from evercurrent.ingestion.threads import ThreadBundle as ThreadBundleModel
    from evercurrent.models.atom import Atom

logger = logging.getLogger(__name__)


async def persist_bundle(
    session: AsyncSession,
    bundle: ThreadBundleModel,
) -> None:
    """Persist a ThreadBundle with its messages and memberships.

    Uses merge (upsert) so re-runs are idempotent.

    Args:
        session: Active async SQLAlchemy session.
        bundle: ThreadBundle from the ingestion layer.
    """
    root = bundle.root_message
    all_msgs = [root, *bundle.replies]

    # Persist all messages
    for msg in all_msgs:
        await session.merge(
            Message(
                message_ts=msg.message_ts,
                thread_ts=msg.thread_ts,
                channel=msg.channel,
                user_id=msg.user_id,
                raw=msg.model_dump(),
            )
        )

    # Persist the bundle
    await session.merge(
        ThreadBundle(
            root_message_ts=root.message_ts,
            channel=root.channel,
        )
    )

    # Persist memberships
    await session.merge(
        BundleMembership(
            message_ts=root.message_ts,
            bundle_ts=root.message_ts,
            role=BundleRole.root,
            confidence=1.0,
            ordinal=0,
        )
    )
    for i, reply in enumerate(bundle.replies):
        role = BundleRole.reply
        await session.merge(
            BundleMembership(
                message_ts=reply.message_ts,
                bundle_ts=root.message_ts,
                role=role,
                confidence=1.0,
                ordinal=i + 1,
            )
        )

    await session.flush()


async def persist_atoms(
    session: AsyncSession,
    atoms: list[Atom],
) -> None:
    """Persist extracted atoms to Postgres.

    Uses merge (upsert) so re-runs are idempotent.

    Args:
        session: Active async SQLAlchemy session.
        atoms: Atoms from the extraction pipeline.
    """
    for atom in atoms:
        await session.merge(
            AtomRow(
                atom_id=atom.atom_id,
                type=atom.type,
                summary=atom.summary,
                detail=atom.detail,
                urgency=atom.urgency,
                confidence=atom.confidence,
                implicit_decision=atom.implicit_decision,
                source=atom.source.model_dump(),
                source_bundle_ts=atom.source.thread_ts,
            )
        )

    await session.flush()
    logger.info("Persisted %d atoms to Postgres", len(atoms))


async def get_processed_bundle_ts(session: AsyncSession) -> set[str]:
    """Query Postgres for existing bundle root_message_ts values.

    Args:
        session: Active async SQLAlchemy session.

    Returns:
        Set of root_message_ts strings already in the database.
    """
    result = await session.execute(
        select(ThreadBundle.root_message_ts),
    )
    return set(result.scalars().all())
