import pytest

from pyagent.usage import PRICING, Usage, estimate_cost


def test_usage_addition_sums_every_field() -> None:
    total = Usage(1, 2, 3, 4) + Usage(10, 20, 30, 40)
    assert total == Usage(11, 22, 33, 44)
    assert total.total_tokens == 110


def test_default_usage_is_zero() -> None:
    assert Usage().total_tokens == 0


def test_cost_for_known_model() -> None:
    usage = Usage(input_tokens=1_000_000, output_tokens=1_000_000)
    assert estimate_cost("claude-opus-5-5", usage) == pytest.approx(24.0)


def test_cost_for_unknown_model_is_none() -> None:
    assert estimate_cost("not-a-model", Usage(1, 1)) is None


def test_cache_reads_are_cheaper_than_input() -> None:
    for pricing in PRICING.values():
        assert pricing.cache_read < pricing.input
