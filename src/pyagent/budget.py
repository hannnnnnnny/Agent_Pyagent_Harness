"""Hard limits on how long and how expensively an agent may run."""

from __future__ import annotations

from dataclasses import dataclass

from pyagent.errors import BudgetExceeded
from pyagent.usage import Usage, estimate_cost


@dataclass(frozen=True)
class Budget:
    """Limits for one run. ``None`` means unlimited for that dimension."""

    max_turns: int | None = 50
    max_total_tokens: int | None = None
    max_cost_usd: float | None = None

    def __post_init__(self) -> None:
        for name in ("max_turns", "max_total_tokens", "max_cost_usd"):
            value = getattr(self, name)
            if value is not None and value <= 0:
                raise ValueError(f"{name} must be positive")


class BudgetTracker:
    """Accumulates usage and enforces a :class:`Budget`.

    Checks happen *before* each model call, so a run stops cleanly between
    turns rather than mid-tool-execution.
    """

    def __init__(self, budget: Budget, model: str) -> None:
        self.budget = budget
        self.model = model
        self.turns = 0
        self.usage = Usage()

    @property
    def cost_usd(self) -> float | None:
        return estimate_cost(self.model, self.usage)

    def record(self, usage: Usage) -> None:
        self.turns += 1
        self.usage = self.usage + usage

    def check(self) -> None:
        b = self.budget
        if b.max_turns is not None and self.turns >= b.max_turns:
            raise BudgetExceeded(f"reached the limit of {b.max_turns} turns")
        if b.max_total_tokens is not None and self.usage.total_tokens >= b.max_total_tokens:
            raise BudgetExceeded(f"reached the limit of {b.max_total_tokens} tokens")
        cost = self.cost_usd
        if b.max_cost_usd is not None and cost is not None and cost >= b.max_cost_usd:
            raise BudgetExceeded(f"reached the cost limit of ${b.max_cost_usd:.2f}")
