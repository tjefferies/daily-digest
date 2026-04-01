"""Google Gemini adapter for the LLM client interface (sync and async).

Wraps a Google GenerativeModel instance to satisfy the LLMClient
protocol, mapping create_message calls to Gemini's generate_content API.
Supports instructor-based structured output for typed Pydantic responses.
"""

from __future__ import annotations

from typing import Any, TypeVar

import instructor
from pydantic import BaseModel

from evercurrent.llm.types import LLMResponse

T = TypeVar("T", bound=BaseModel)


class GoogleAdapter:
    """Adapter wrapping a Google GenerativeModel instance.

    Translates create_message calls to Gemini's generate_content
    and extracts text from the response. Also supports structured
    output via instructor for typed Pydantic model responses.
    """

    def __init__(self, client: Any) -> None:  # noqa: ANN401
        """Initialize with a Google GenerativeModel instance.

        Args:
            client: Google GenerativeModel instance.
        """
        self._client = client
        self._instructor_client: Any = None  # noqa: ANN401

    def _get_instructor_client(self) -> Any:  # noqa: ANN401
        """Lazily initialize and return the instructor-patched client.

        Returns:
            Instructor-patched Gemini client for structured output.
        """
        if self._instructor_client is None:
            self._instructor_client = instructor.from_gemini(
                client=self._client,
                mode=instructor.Mode.GEMINI_JSON,
            )
        return self._instructor_client

    def create_message(
        self,
        *,
        model: str,  # noqa: ARG002
        max_tokens: int,
        messages: list[dict[str, str]],
        system: str = "",
    ) -> LLMResponse:
        """Send a message via the Google Gemini API.

        Maps the messages list to Gemini's content format and passes
        system as a system instruction via generation config.

        Args:
            model: Gemini model identifier (ignored, set at client init).
            max_tokens: Maximum tokens in the response.
            messages: List of message dicts with 'role' and 'content'.
            system: Optional system instruction.

        Returns:
            LLMResponse with the extracted text content.

        Raises:
            ValueError: If the response text is empty or None.
        """
        contents = [msg["content"] for msg in messages]
        config: dict[str, Any] = {"max_output_tokens": max_tokens}
        if system:
            config["system_instruction"] = system
        response = self._client.generate_content(
            contents,
            generation_config=config,
        )
        if response.text is None:
            msg = "Google Gemini returned empty response text"
            raise ValueError(msg)
        return LLMResponse(text=response.text)

    def create_structured_message(
        self,
        *,
        model: str,  # noqa: ARG002
        max_tokens: int,
        messages: list[dict[str, str]],
        system: str = "",  # noqa: ARG002
        response_model: type[T],
    ) -> T:
        """Send a message and return a typed Pydantic model via instructor.

        Args:
            model: Gemini model identifier (ignored, set at client init).
            max_tokens: Maximum tokens in the response.
            messages: List of message dicts with 'role' and 'content'.
            system: Optional system instruction (unused, for protocol compat).
            response_model: Pydantic model class for structured output.

        Returns:
            Instance of the response_model, validated by instructor.
        """
        contents = [msg["content"] for msg in messages]
        return self._get_instructor_client().messages.create(
            messages=[{"role": "user", "content": c} for c in contents],
            response_model=response_model,
            max_tokens=max_tokens,
        )


class AsyncGoogleAdapter:
    """Async adapter wrapping a Google GenerativeModel instance.

    Translates async create_message calls to Gemini's generate_content_async API.
    Also supports structured output via instructor.
    """

    def __init__(self, client: Any) -> None:  # noqa: ANN401
        """Initialize with a Google GenerativeModel instance.

        Args:
            client: Google GenerativeModel instance.
        """
        self._client = client
        self._instructor_client: Any = None  # noqa: ANN401

    def _get_instructor_client(self) -> Any:  # noqa: ANN401
        """Lazily initialize and return the instructor-patched async client.

        Returns:
            Instructor-patched async Gemini client for structured output.
        """
        if self._instructor_client is None:
            self._instructor_client = instructor.from_gemini(
                client=self._client,
                mode=instructor.Mode.GEMINI_JSON,
                use_async=True,
            )
        return self._instructor_client

    async def create_message(
        self,
        *,
        model: str,  # noqa: ARG002
        max_tokens: int,
        messages: list[dict[str, str]],
        system: str = "",
    ) -> LLMResponse:
        """Send a message via the Google Gemini API asynchronously.

        Args:
            model: Gemini model identifier (ignored, set at client init).
            max_tokens: Maximum tokens in the response.
            messages: List of message dicts with 'role' and 'content'.
            system: Optional system instruction.

        Returns:
            LLMResponse with the extracted text content.

        Raises:
            ValueError: If the response text is empty or None.
        """
        contents = [msg["content"] for msg in messages]
        config: dict[str, Any] = {"max_output_tokens": max_tokens}
        if system:
            config["system_instruction"] = system
        response = await self._client.generate_content_async(
            contents,
            generation_config=config,
        )
        if response.text is None:
            msg = "Google Gemini returned empty response text"
            raise ValueError(msg)
        return LLMResponse(text=response.text)

    async def create_structured_message(
        self,
        *,
        model: str,  # noqa: ARG002
        max_tokens: int,
        messages: list[dict[str, str]],
        system: str = "",  # noqa: ARG002
        response_model: type[T],
    ) -> T:
        """Send a message and return a typed Pydantic model via instructor.

        Args:
            model: Gemini model identifier (ignored, set at client init).
            max_tokens: Maximum tokens in the response.
            messages: List of message dicts with 'role' and 'content'.
            system: Optional system instruction (unused, for protocol compat).
            response_model: Pydantic model class for structured output.

        Returns:
            Instance of the response_model, validated by instructor.
        """
        contents = [msg["content"] for msg in messages]
        return await self._get_instructor_client().messages.create(
            messages=[{"role": "user", "content": c} for c in contents],
            response_model=response_model,
            max_tokens=max_tokens,
        )
