from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from adaptive_tutor.schemas import BackendConfig


class LLMBackend(ABC):
    @abstractmethod
    def generate(
        self,
        messages: list[dict[str, str]],
        model: str,
        response_format: dict[str, Any] | None = None,
        seed: int | None = None,
        temperature: float | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        raise NotImplementedError


def create_backend(config: BackendConfig) -> LLMBackend:
    if config.type == "mock":
        from adaptive_tutor.backends.mock_backend import MockBackend

        return MockBackend()
    if config.type == "openai_compatible":
        from adaptive_tutor.backends.openai_backend import OpenAICompatibleBackend

        return OpenAICompatibleBackend(config)
    raise ValueError(f"Unsupported backend type: {config.type}")
