"""Async LLM request/response logger for Postgres.

Logs the full JSON request and response bodies for LLM batch calls
to the batch_log table. Enables debugging, cost tracking, and
replay. Graceful degradation - logging failures never crash the
pipeline.

Deduplication: a batch_id is logged once. Duplicate submissions
are silently ignored.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select, update

from digest.db.models import BatchLog
from digest.db.session import get_session_factory

logger = logging.getLogger(__name__)


async def log_llm_request(
    *,
    batch_id: str,
    stage: str,
    request_count: int,
    request_body: dict[str, Any] | list[dict[str, Any]],
) -> None:
    """Log the full LLM request body to Postgres (idempotent).

    If a row with this batch_id already exists, skip the insert.

    Args:
        batch_id: Anthropic batch ID or unique request ID.
        stage: Pipeline stage (extraction_stage1, validation, etc.).
        request_count: Number of requests in the batch/call.
        request_body: Full JSON request body sent to Anthropic.
    """
    try:
        factory = get_session_factory()
        body = request_body if isinstance(request_body, dict) else {"requests": request_body}
        async with factory() as session:
            existing = await session.execute(
                select(BatchLog.id).where(BatchLog.batch_id == batch_id),
            )
            if existing.scalar_one_or_none() is not None:
                return  # Already logged - skip
            session.add(
                BatchLog(
                    batch_id=batch_id,
                    stage=stage,
                    request_count=request_count,
                    status="submitted",
                    request_body=body,
                )
            )
            await session.commit()
    except Exception:
        logger.debug("Failed to log LLM request to Postgres", exc_info=True)


async def log_llm_response(
    *,
    batch_id: str,
    status: str,
    response_body: dict[str, Any],
) -> None:
    """Log the full LLM response body to Postgres.

    Updates the existing batch_log row with the response data.

    Args:
        batch_id: Anthropic batch ID or unique request ID.
        status: Final status (ended, completed, canceled, etc.).
        response_body: Full JSON response body from Anthropic.
    """
    try:
        factory = get_session_factory()
        async with factory() as session:
            await session.execute(
                update(BatchLog)
                .where(BatchLog.batch_id == batch_id)
                .values(
                    status=status,
                    response_body=response_body,
                    completed_at=datetime.now(tz=UTC),
                ),
            )
            await session.commit()
    except Exception:
        logger.debug("Failed to log LLM response to Postgres", exc_info=True)
