from __future__ import annotations

from types import SimpleNamespace

from adaptive_tutor.backends.openai_backend import OpenAICompatibleBackend


class _FakeCompletions:
    def __init__(self) -> None:
        self.calls = 0

    def create(self, **_kwargs):
        self.calls += 1
        if self.calls < 3:
            raise TimeoutError("transient")
        message = SimpleNamespace(content="ok")
        choice = SimpleNamespace(message=message)
        return SimpleNamespace(choices=[choice])


def test_openai_backend_retries_transient_errors() -> None:
    backend = OpenAICompatibleBackend.__new__(OpenAICompatibleBackend)
    completions = _FakeCompletions()
    backend.client = SimpleNamespace(
        chat=SimpleNamespace(completions=completions)
    )
    backend.retry_attempts = 3
    backend.retry_backoff_seconds = 0

    result = backend.generate(messages=[], model="test-model")

    assert result == "ok"
    assert completions.calls == 3
