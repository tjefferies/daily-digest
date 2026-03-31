"""Tests for LLM response types and protocol definition."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

from evercurrent.llm.types import AsyncLLMClient, LLMClient, LLMResponse


class TestLLMResponse:
    """Tests for LLMResponse dataclass."""

    def test_response_stores_text(self) -> None:
        """LLMResponse stores the text content."""
        resp = LLMResponse(text="Hello world")
        assert resp.text == "Hello world"

    def test_response_empty_text(self) -> None:
        """LLMResponse can hold empty text."""
        resp = LLMResponse(text="")
        assert resp.text == ""

    def test_response_preserves_json(self) -> None:
        """LLMResponse preserves JSON string content."""
        json_text = '{"atoms": [{"type": "DECISION"}]}'
        resp = LLMResponse(text=json_text)
        assert resp.text == json_text


class TestLLMClientProtocol:
    """Tests that the LLMClient protocol is satisfiable."""

    def test_mock_satisfies_protocol(self) -> None:
        """A mock with create_message satisfies LLMClient."""
        mock = MagicMock(spec=["create_message"])
        mock.create_message.return_value = LLMResponse(text="mock response")
        client: LLMClient = mock
        resp = client.create_message(
            model="test",
            max_tokens=100,
            messages=[{"role": "user", "content": "hi"}],
        )
        assert resp.text == "mock response"


class TestAsyncLLMClientProtocol:
    """Tests that the AsyncLLMClient protocol is satisfiable."""

    async def test_async_mock_satisfies_protocol(self) -> None:
        """An async mock with create_message satisfies AsyncLLMClient."""
        mock = AsyncMock()
        mock.create_message.return_value = LLMResponse(text="async response")
        client: AsyncLLMClient = mock
        resp = await client.create_message(
            model="test",
            max_tokens=100,
            messages=[{"role": "user", "content": "hi"}],
        )
        assert resp.text == "async response"
