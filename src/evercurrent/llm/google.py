"""Google Gemini adapter for the LLM client interface.

Wraps a Google GenerativeModel instance to satisfy the LLMClient
protocol, mapping create_message calls to Gemini's generate_content API.
"""

from __future__ import annotations

from typing import Any

from evercurrent.llm.types import LLMResponse


class GoogleAdapter:
    """Adapter wrapping a Google GenerativeModel instance.

    Translates create_message calls to Gemini's generate_content
    and extracts text from the response.
    """

    def __init__(self, client: Any) -> None:  # noqa: ANN401
        """Initialize with a Google GenerativeModel instance.

        Args:
            client: Google GenerativeModel instance.
        """
        self._client = client

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
