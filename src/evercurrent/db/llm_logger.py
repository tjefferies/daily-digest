"""Async LLM request/response logger for Postgres.

Logs the full JSON request and response bodies for every LLM call
(batch or individual async) to the batch_log table. Enables
debugging, cost tracking, and replay. Graceful degradation —
logging failures never crash the pipeline.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from evercurrent.db.models import BatchLog
from evercurrent.db.session import get_session_factory

logger = logging.getLogger(__name__)


async def log_llm_request(
    *,
    batch_id: str,
    stage: str,
    request_count: int,
    request_body: dict[str, Any] | list[dict[str, Any]],
) -> None:
    """Log the full LLM request body to Postgres.

    Args:
        batch_id: Anthropic batch ID or unique request ID.
        stage: Pipeline stage (extraction_stage1, validation, etc.).
        request_count: Number of requests in the batch/call.
        request_body: Full JSON request body sent to Anthropic.
    """
    try:
        factory = get_session_factory()
        async with factory() as session:
            await session.merge(BatchLog(
                batch_id=batch_id,
                stage=stage,
                request_count=request_count,
                status="submitted",
                request_body=(
                    request_body if isinstance(request_body, dict)
                    else {"requests": request_body}
                ),
            ))
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
        status: Final status (ended, canceled, succeeded, failed).
        response_body: Full JSON response body from Anthropic.
    """
    try:
        factory = get_session_factory()
        async with factory() as session:
            from sqlalchemy import update

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
