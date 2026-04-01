"""Async SQLAlchemy session factory.

Creates an async engine and session maker from the Postgres DSN
configured in pipeline.yml (overridable via POSTGRES_DSN env var).
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from evercurrent.config.loader import get_config

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

_engine = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def reset_engine() -> None:
    """Reset the cached engine and session factory.

    Call between tests or when switching event loops.
    """
    global _engine, _session_factory  # noqa: PLW0603
    _engine = None
    _session_factory = None


def _get_dsn() -> str:
    """Get the Postgres DSN from env or config.

    Returns:
        Postgres connection string for asyncpg.
    """
    if dsn := os.environ.get("POSTGRES_DSN"):
        return dsn
    return get_config()["pipeline"]["postgres"]["dsn"]


def _get_engine() -> create_async_engine:
    """Get or create the async SQLAlchemy engine.

    Returns:
        Async engine connected to Postgres.
    """
    global _engine  # noqa: PLW0603
    if _engine is None:
        _engine = create_async_engine(_get_dsn(), echo=False)
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Get or create the async session factory.

    Returns:
        Async session maker bound to the engine.
    """
    global _session_factory  # noqa: PLW0603
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            _get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _session_factory


async def get_session() -> AsyncIterator[AsyncSession]:
    """Yield an async database session.

    Usage::

        async for session in get_session():
            result = await session.execute(...)

    Yields:
        AsyncSession that auto-closes on exit.
    """
    factory = get_session_factory()
    async with factory() as session:
        yield session
