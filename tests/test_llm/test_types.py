"""Tests for LLM response types and protocol definition."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

from pydantic import BaseModel

from evercurrent.llm.types import AsyncLLMClient, LLMClient, LLMResponse


class _DummyModel(BaseModel):
    """Minimal Pydantic model for protocol testing."""

    value: str


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

    def test_structured_message_returns_pydantic_model(self) -> None:
        """create_structured_message returns a typed Pydantic model."""
        mock = MagicMock()
        expected = _DummyModel(value="structured")
        mock.create_structured_message.return_value = expected
        client: LLMClient = mock
        result = client.create_structured_message(
            model="test",
            max_tokens=100,
            messages=[{"role": "user", "content": "hi"}],
            response_model=_DummyModel,
        )
        assert isinstance(result, _DummyModel)
        assert result.value == "structured"


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

    async def test_async_structured_message_returns_pydantic_model(self) -> None:
        """Async create_structured_message returns a typed Pydantic model."""
        mock = AsyncMock()
        expected = _DummyModel(value="async structured")
        mock.create_structured_message.return_value = expected
        client: AsyncLLMClient = mock
        result = await client.create_structured_message(
            model="test",
            max_tokens=100,
            messages=[{"role": "user", "content": "hi"}],
            response_model=_DummyModel,
        )
        assert isinstance(result, _DummyModel)
        assert result.value == "async structured"
