from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import httpx
from httpx import Response

from agent_smith.config import Config
from agent_smith.data import (
    API_RETRY_DELAY,
    API_RETRY_MAX,
    API_RETRY_STATUS,
    API_TIMEOUT,
    STOP_SEQUENCES,
)


class LLMClientError(Exception):
    pass


@dataclass
class LLMResponse:
    """The LLM's answer to one ask() call."""

    text: str
    input_tokens: int
    output_tokens: int
    retries: int = 0  # failed attempts before this answer (0 = first try)
    request_time_ms: float = 0.0  # wall-clock time, retries included


class LLMClient:
    """Send messages to an OpenAI-compatible LLM API and return its answer.

    - Use ask(messages, max_tokens) to return an LLMResponse
    - Any failure (network, HTTP status, answer format) raises LLMClientError.
    """

    def __init__(self, config: Config) -> None:
        self.config = config

    # ---------------------------------------------------------------- ASK ----
    def ask(
        self, messages: list[dict[str, str]], max_tokens: int
    ) -> LLMResponse:
        """Send the whole conversation and return the LLM's next answer.

        messages: [{"role": "system" | "user" | "assistant", "content": ...}]
        max_tokens: the server stops the answer after this many tokens.
        The client keeps no history: the caller sends the full list each time.
        """
        body = self._new_body(messages, max_tokens)
        start = time.perf_counter()
        response, retries = self._send_with_retries(body)
        request_time_ms = (time.perf_counter() - start) * 1000
        data = self._read_json(response)

        return LLMResponse(
            text=self._extract_message(data),
            input_tokens=self._extract_usage(data, "prompt_tokens"),
            output_tokens=self._extract_usage(data, "completion_tokens"),
            retries=retries,
            request_time_ms=request_time_ms,
        )

    # -------------------------------------------------------------- BUILD ----
    def _new_body(
        self, messages: list[dict[str, str]], max_tokens: int
    ) -> dict:
        return {
            "model": self.config.model_name,
            "messages": messages,
            "stop": STOP_SEQUENCES,
            "max_tokens": max_tokens,
        }

    # --------------------------------------------------------------- SEND ----
    def _send_with_retries(self, body: dict) -> tuple[Response, int]:
        """Send the body, retrying temporary failures.

        Return (response, retries). Raise LLMClientError if it still fails.
        """

        retries: int = 0
        while True:
            try:
                return self._send(body), retries

            except httpx.HTTPStatusError as err:
                status = err.response.status_code
                if status not in API_RETRY_STATUS or retries == API_RETRY_MAX:
                    raise LLMClientError(
                        f"HTTP {status} after {retries} retries: "
                        f"{err.response.text}"
                    ) from err

            except httpx.HTTPError as err:
                raise LLMClientError(f"Request failed: {err}") from err

            # --
            retries += 1
            time.sleep(API_RETRY_DELAY * retries)

    def _send(self, body: dict) -> Response:
        """POST the body to the provider and return a successful response."""

        # TODO: Check httpx stream to see if it's possible to stop before
        response = httpx.post(
            self.config.url,
            headers={"Authorization": f"Bearer {self.config.keys[0]}"},
            json=body,  # converted to JSON automatically
            timeout=API_TIMEOUT,
        )

        response.raise_for_status()
        return response

    # ----------------------------------------------------- READ & EXTRACT ----
    def _read_json(self, response: Response) -> Any:
        """Return the response body converted from JSON."""

        try:
            return response.json()
        except ValueError as err:
            raise LLMClientError(
                f"Answer is not JSON: {response.text}"
            ) from err

    def _extract_message(self, data: Any) -> str:
        """Return the text of the first choice of an OpenAI-style answer."""

        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as err:
            raise LLMClientError(f"Unexpected answer format: {data}") from err

        if not isinstance(content, str):
            raise LLMClientError(f"The answer contains no text: {data}")

        return content

    def _extract_usage(self, data: Any, name: str) -> int:
        """Return one token count from the answer's usage."""

        try:
            value = data["usage"][name]
        except (KeyError, TypeError) as err:
            raise LLMClientError(f"Missing '{name}' in usage: {data}") from err

        if not isinstance(value, int):
            raise LLMClientError(f"'{name}' is not an integer: {value}")

        return value
