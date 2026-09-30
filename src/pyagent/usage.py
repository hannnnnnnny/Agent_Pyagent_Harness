"""Token usage accounting."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Usage:
    """Token counts for one or more model calls."""

    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_input_tokens: int = 0
    cache_creation_input_tokens: int = 0

    def __add__(self, other: Usage) -> Usage:
        return Usage(
            input_tokens=self.input_tokens + other.input_tokens,
            output_tokens=self.output_tokens + other.output_tokens,
            cache_read_input_tokens=self.cache_read_input_tokens + other.cache_read_input_tokens,
            cache_creation_input_tokens=(
                self.cache_creation_input_tokens + other.cache_creation_input_tokens
            ),
        )

    @property
    def total_tokens(self) -> int:
        return (
            self.input_tokens
            + self.output_tokens
            + self.cache_read_input_tokens
            + self.cache_creation_input_tokens
        )


@dataclass(frozen=True)
class Pricing:
    """USD price per million tokens for a model."""

    input: float
    output: float
    cache_read: float
    cache_write: float

    def cost(self, usage: Usage) -> float:
        per_token = 1_000_000
        return (
            usage.input_tokens * self.input
            + usage.output_tokens * self.output
            + usage.cache_read_input_tokens * self.cache_read
            + usage.cache_creation_input_tokens * self.cache_write
        ) / per_token


# Cache writes are billed at 1.25x input for the default 5-minute TTL.
PRICING: dict[str, Pricing] = {
    "claude-opus-5-5": Pricing(input=4.0, output=20.0, cache_read=0.20, cache_write=5.0),
    "claude-sonnet-5-5": Pricing(input=2.0, output=10.0, cache_read=0.20, cache_write=2.5),
    "claude-haiku-4-5": Pricing(input=1.0, output=5.0, cache_read=0.10, cache_write=1.25),
    "claude-fable-5-1": Pricing(input=10.0, output=50.0, cache_read=0.25, cache_write=12.5),
    # DeepSeek charges less off-peak; peak rates are used so cost budgets
    # stop a run early rather than late. There is no separate cache-write fee.
    "deepseek-v4-pro": Pricing(input=1.32, output=3.96, cache_read=0.044, cache_write=1.32),
    "deepseek-flash": Pricing(input=0.30, output=1.20, cache_read=0.006, cache_write=0.30),
}


def estimate_cost(model: str, usage: Usage) -> float | None:
    """Return the USD cost of ``usage`` on ``model``, or None if the model is unknown."""
    pricing = PRICING.get(model)
    return pricing.cost(usage) if pricing else None
