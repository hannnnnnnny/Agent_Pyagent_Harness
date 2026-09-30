"""DeepSeek via its Anthropic-compatible Messages endpoint.

DeepSeek accepts the same wire format pyagent already stores (``tool_use``,
``tool_result``, and ``thinking`` blocks), so the Anthropic SDK is reused with a
different base URL and key. Only fields DeepSeek documents as supported are
sent; Anthropic-only features (betas, fallbacks, cache_control) are left out.
"""

from __future__ import annotations

import os
from typing import Any

import anthropic

from pyagent.errors import ProviderError
from pyagent.providers.anthropic import DEFAULT_EFFORT, AnthropicProvider
from pyagent.providers.base import ModelRequest

DEEPSEEK_BASE_URL = "https://api.deepseek.com/anthropic"
DEEPSEEK_MODELS = ("deepseek-v4-pro", "deepseek-flash")
DEFAULT_DEEPSEEK_MODEL = "deepseek-v4-pro"
API_KEY_ENV = "DEEPSEEK_API_KEY"
# DeepSeek allows far more, but 64K keeps a single turn bounded in time and cost.
DEFAULT_DEEPSEEK_MAX_TOKENS = 64_000


class DeepSeekProvider(AnthropicProvider):
    service_name = "DeepSeek"
    auth_hint = f"set {API_KEY_ENV} to a key from platform.deepseek.com"

    def __init__(
        self,
        model: str = DEFAULT_DEEPSEEK_MODEL,
        *,
        max_tokens: int = DEFAULT_DEEPSEEK_MAX_TOKENS,
        effort: str = DEFAULT_EFFORT,
        base_url: str = DEEPSEEK_BASE_URL,
        client: Any = None,
    ) -> None:
        if client is None:
            # The key is read from the environment only; it is never stored in config.
            api_key = os.environ.get(API_KEY_ENV, "")
            if not api_key:
                raise ProviderError(f"{API_KEY_ENV} is not set; {self.auth_hint}")
            client = anthropic.Anthropic(api_key=api_key, base_url=base_url)
        super().__init__(
            model, max_tokens=max_tokens, effort=effort, fallbacks=False, client=client
        )

    def build_params(self, request: ModelRequest) -> dict[str, Any]:
        params: dict[str, Any] = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "system": request.system,
            "messages": request.messages,
            "output_config": {"effort": self.effort},
        }
        if request.tools:
            params["tools"] = list(request.tools)
        return params

    def _stream(self, params: dict[str, Any]) -> Any:
        return self.client.messages.stream(**params)
