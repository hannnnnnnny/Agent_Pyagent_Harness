from pyagent.safety.verdict import Assessment, Verdict, strictest


def test_verdicts_are_ordered_by_strictness() -> None:
    assert Verdict.ALLOW < Verdict.ASK < Verdict.BLOCK


def test_strictest_picks_block_over_ask() -> None:
    result = strictest([Assessment.allow(), Assessment.block("rm -rf /"), Assessment.ask("net")])
    assert result == Assessment.block("rm -rf /")


def test_strictest_of_nothing_is_allow() -> None:
    assert strictest([]).verdict is Verdict.ALLOW


def test_first_of_equal_verdicts_wins() -> None:
    assert strictest([Assessment.ask("a"), Assessment.ask("b")]).reason == "a"
