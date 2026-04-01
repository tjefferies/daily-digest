"""Integration test: LLM request/response logging to Postgres.

Proves that:
1. log_llm_request writes a row with the full request body
2. log_llm_response updates that row with the full response body
3. The same batch_id does NOT create duplicate rows
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from digest.db.models import Base, BatchLog


@pytest.mark.integration
class TestLLMRequestResponseLogging:
    """Verify LLM request/response bodies are logged to Postgres."""

    @pytest.fixture(autouse=True)
    async def db(self):
        """Create in-memory SQLite with schema, patch session factory."""
        from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

        engine = create_async_engine("sqlite+aiosqlite://", echo=False)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        # Patch get_session_factory to return our test factory
        with patch("digest.db.llm_logger.get_session_factory", return_value=factory):
            self._factory = factory
            yield factory

        await engine.dispose()

    async def test_request_logged_with_full_body(self) -> None:
        """log_llm_request writes a row with the complete request JSONB."""
        from sqlalchemy import select

        from digest.db.llm_logger import log_llm_request

        request_body = {
            "requests": [
                {
                    "custom_id": "stage1-0",
                    "params": {
                        "model": "claude-haiku-4-5",
                        "max_tokens": 4096,
                        "messages": [{"role": "user", "content": "Extract atoms"}],
                        "tools": [{"name": "extract_atoms"}],
                    },
                },
                {
                    "custom_id": "stage1-1",
                    "params": {
                        "model": "claude-haiku-4-5",
                        "max_tokens": 4096,
                        "messages": [{"role": "user", "content": "Another thread"}],
                        "tools": [{"name": "extract_atoms"}],
                    },
                },
            ],
        }

        await log_llm_request(
            batch_id="msgbatch_test_001",
            stage="extraction_stage1",
            request_count=2,
            request_body=request_body,
        )

        async with self._factory() as session:
            result = await session.execute(select(BatchLog))
            rows = result.scalars().all()

        assert len(rows) == 1
        row = rows[0]
        assert row.batch_id == "msgbatch_test_001"
        assert row.stage == "extraction_stage1"
        assert row.request_count == 2
        assert row.status == "submitted"
        assert row.request_body == request_body
        assert row.response_body is None
        assert row.completed_at is None

    async def test_response_logged_with_full_body(self) -> None:
        """log_llm_response updates the row with the complete response JSONB."""
        from sqlalchemy import select

        from digest.db.llm_logger import log_llm_request, log_llm_response

        await log_llm_request(
            batch_id="msgbatch_test_002",
            stage="extraction_stage2",
            request_count=5,
            request_body={"requests": ["...truncated..."]},
        )

        response_body = {
            "succeeded": 4,
            "failed": 1,
            "total": 5,
            "results": {
                "stage2-0-0": {"workstreams": {"originating": "chassis", "affected": ["thermal"]}},
                "stage2-0-1": {"workstreams": {"originating": "drivetrain", "affected": []}},
            },
        }

        await log_llm_response(
            batch_id="msgbatch_test_002",
            status="ended",
            response_body=response_body,
        )

        async with self._factory() as session:
            result = await session.execute(select(BatchLog))
            rows = result.scalars().all()

        assert len(rows) == 1
        row = rows[0]
        assert row.status == "ended"
        assert row.response_body == response_body
        assert row.completed_at is not None

    async def test_no_duplicate_rows_for_same_batch_id(self) -> None:
        """Logging the same batch_id twice does NOT create duplicate rows."""
        from sqlalchemy import select

        from digest.db.llm_logger import log_llm_request

        # Log the same batch_id twice
        await log_llm_request(
            batch_id="msgbatch_test_003",
            stage="extraction_stage1",
            request_count=10,
            request_body={"first": True},
        )

        await log_llm_request(
            batch_id="msgbatch_test_003",
            stage="extraction_stage1",
            request_count=10,
            request_body={"second": True},
        )

        async with self._factory() as session:
            result = await session.execute(
                select(BatchLog).where(BatchLog.batch_id == "msgbatch_test_003"),
            )
            rows = result.scalars().all()

        # merge is idempotent - should be 1 row, not 2
        assert len(rows) == 1, (
            f"Expected 1 row for batch_id=msgbatch_test_003, got {len(rows)}. "
            f"Duplicate logging detected!"
        )

    async def test_request_and_response_on_same_row(self) -> None:
        """Request body and response body end up on the same row."""
        from sqlalchemy import select

        from digest.db.llm_logger import log_llm_request, log_llm_response

        batch_id = "msgbatch_test_004"
        req = {"messages": [{"content": "hello"}]}
        resp = {"succeeded": 1, "results": {"id-0": {"summary": "test"}}}

        await log_llm_request(
            batch_id=batch_id,
            stage="validation",
            request_count=1,
            request_body=req,
        )
        await log_llm_response(
            batch_id=batch_id,
            status="completed",
            response_body=resp,
        )

        async with self._factory() as session:
            result = await session.execute(
                select(BatchLog).where(BatchLog.batch_id == batch_id),
            )
            rows = result.scalars().all()

        assert len(rows) == 1
        row = rows[0]
        assert row.request_body == req
        assert row.response_body == resp
        assert row.status == "completed"
