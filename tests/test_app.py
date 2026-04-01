"""Tests for the FastAPI application setup."""

import pytest
from httpx import ASGITransport, AsyncClient

from digest.app import app


class TestAppSetup:
    """Tests for FastAPI app configuration."""

    def test_app_exists(self) -> None:
        """Verify the FastAPI app is created with the correct title."""
        assert app is not None
        assert app.title == "EverCurrent"

    @pytest.mark.asyncio
    async def test_health_endpoint(self) -> None:
        """Verify the health endpoint returns 200 with ok status."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestCORS:
    """Tests for CORS configuration."""

    @pytest.mark.asyncio
    async def test_cors_allows_localhost(self) -> None:
        """Verify CORS preflight allows localhost:5173 origin."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.options(
                "/health",
                headers={
                    "Origin": "http://localhost:5173",
                    "Access-Control-Request-Method": "GET",
                },
            )
        assert response.status_code == 200
        assert "access-control-allow-origin" in response.headers
