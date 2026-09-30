from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import anthropic
import httpx2
import pytest

from pyagent.errors import ProviderError
from pyagent.providers.base import ModelRequest
from pyagent.providers.deepseek import (
    API_KEY_ENV,
    DEEPSEEK_BASE_URL,
    DEFAULT_DEEPSEEK_MODEL,
    DeepSeekProvider,
)
from tests.providers.test_anthropic import MESSAGE, REQUEST, FakeStream


class FakeClient:
    """Only exposes the non-beta namespace, like DeepSeek's endpoint needs."""

    def __init__(self, outcome: Any) -> None:
        self.calls: list[dict[str, Any]] = []

        def stream(**params: Any) -> FakeStream:
            self.calls.append(params)
            return FakeStream(outcome)

        self.messages = SimpleNamespace(stream=stream)


def test_sends_only_supported_fields() -> None:
    client = FakeClient(MESSAGE)
    DeepSeekProvider(client=client, effort="max").complete(REQUEST)
    params = client.calls[0]
    assert params["model"] == DEFAULT_DEEPSEEK_MODEL
    assert params["output_config"] == {"effort": "max"}
    assert set(params) == {"model", "max_tokens", "system", "messages", "output_config", "tools"}
    assert "eager_input_streaming" not in params["tools"][0]


def test_response_is_converted_like_anthropic() -> None:
    response = DeepSeekProvider(client=FakeClient(MESSAGE)).complete(REQUEST)
    assert response.tool_calls[0].name == "read_file"
    assert response.content[0]["type"] == "thinking"


def test_missing_key_is_a_clear_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(API_KEY_ENV, raising=False)
    with pytest.raises(ProviderError, match=API_KEY_ENV):
        DeepSeekProvider()


def test_client_uses_deepseek_endpoint_and_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(API_KEY_ENV, "sk-test-not-a-real-key")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-must-not-be-used")
    provider = DeepSeekProvider()
    assert str(provider.client.base_url).rstrip("/") == DEEPSEEK_BASE_URL
    assert provider.client.api_key == "sk-test-not-a-real-key"


def test_auth_errors_mention_the_deepseek_key() -> None:
    request = httpx2.Request("POST", DEEPSEEK_BASE_URL)
    error = anthropic.AuthenticationError(
        "bad key", response=httpx2.Response(401, request=request), body=None
    )
    with pytest.raises(ProviderError, match=API_KEY_ENV):
        DeepSeekProvider(client=FakeClient(error)).complete(ModelRequest(system="s", messages=[]))
