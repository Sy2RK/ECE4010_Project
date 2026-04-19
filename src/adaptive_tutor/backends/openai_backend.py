from __future__ import annotations

import time
from typing import Any

from adaptive_tutor.backends.base import LLMBackend
from adaptive_tutor.schemas import BackendConfig


class OpenAICompatibleBackend(LLMBackend):
    def __init__(self, config: BackendConfig) -> None:
        if not config.api_key or not config.base_url:
            raise ValueError("openai_compatible backend requires base_url and api_key")
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise ImportError(
                "openai package is not installed. Run `pip install -e .[dev]`."
            ) from exc
        self.client = OpenAI(
            api_key=config.api_key,
            base_url=config.base_url,
            timeout=config.timeout_seconds,
        )
        self.retry_attempts = config.retry_attempts
        self.retry_backoff_seconds = config.retry_backoff_seconds

    def _create_completion(self, request: dict[str, Any]):
        try:
            return self.client.chat.completions.create(**request)
        except TypeError:
            if "response_format" not in request:
                raise
            fallback_request = dict(request)
            fallback_request.pop("response_format", None)
            return self.client.chat.completions.create(**fallback_request)

    def generate(
        self,
        messages: list[dict[str, str]],
        model: str,
        response_format: dict[str, Any] | None = None,
        seed: int | None = None,
        temperature: float | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        role = (metadata or {}).get("role")
        if temperature is None:
            temperature = 0.0 if role == "judge" else 0.2
        request: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "extra_body": {"enable_thinking": False},
        }
        if seed is not None:
            request["seed"] = seed
        if response_format:
            request["response_format"] = {"type": "json_object"}
        last_error: Exception | None = None
        for attempt_index in range(self.retry_attempts):
            try:
                response = self._create_completion(dict(request))
                message = response.choices[0].message.content or ""
                return message.strip()
            except Exception as exc:
                last_error = exc
                if attempt_index >= self.retry_attempts - 1:
                    break
                delay = self.retry_backoff_seconds * (2 ** attempt_index)
                if delay > 0:
                    time.sleep(delay)
        raise RuntimeError(
            f"OpenAI-compatible API call failed after {self.retry_attempts} attempt(s)."
        ) from last_error
