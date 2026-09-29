import pytest

from pyagent.budget import Budget, BudgetTracker
from pyagent.errors import BudgetExceeded
from pyagent.usage import Usage


def test_turn_limit() -> None:
    tracker = BudgetTracker(Budget(max_turns=2), "claude-opus-5-5")
    tracker.check()
    tracker.record(Usage())
    tracker.check()
    tracker.record(Usage())
    with pytest.raises(BudgetExceeded, match="2 turns"):
        tracker.check()


def test_token_limit() -> None:
    tracker = BudgetTracker(Budget(max_turns=None, max_total_tokens=100), "m")
    tracker.record(Usage(input_tokens=60, output_tokens=40))
    with pytest.raises(BudgetExceeded, match="100 tokens"):
        tracker.check()


def test_cost_limit_uses_model_pricing() -> None:
    tracker = BudgetTracker(Budget(max_turns=None, max_cost_usd=1.0), "claude-opus-5-5")
    tracker.record(Usage(output_tokens=40_000))
    assert tracker.cost_usd == pytest.approx(0.8)
    tracker.check()
    tracker.record(Usage(output_tokens=10_000))
    with pytest.raises(BudgetExceeded, match=r"\$1.00"):
        tracker.check()


def test_cost_limit_ignored_for_unknown_models() -> None:
    tracker = BudgetTracker(Budget(max_turns=None, max_cost_usd=0.01), "custom-model")
    tracker.record(Usage(output_tokens=10**9))
    tracker.check()
    assert tracker.cost_usd is None


def test_unlimited_budget() -> None:
    tracker = BudgetTracker(Budget(max_turns=None), "m")
    for _ in range(1000):
        tracker.record(Usage(1, 1))
    tracker.check()


@pytest.mark.parametrize("field", ["max_turns", "max_total_tokens", "max_cost_usd"])
def test_non_positive_limits_rejected(field: str) -> None:
    with pytest.raises(ValueError):
        Budget(**{field: 0})
