import pytest

from pyagent.text import truncate_middle


def test_short_text_is_unchanged() -> None:
    assert truncate_middle("hello", 10) == "hello"


def test_long_text_keeps_both_ends() -> None:
    text = "HEAD" + "x" * 1000 + "TAIL"
    out = truncate_middle(text, 100)
    assert out.startswith("HEAD")
    assert out.endswith("TAIL")
    assert "characters truncated" in out


@pytest.mark.parametrize("limit", [0, 1, 5, 30, 64, 99, 100, 101])
def test_result_never_exceeds_limit(limit: int) -> None:
    assert len(truncate_middle("y" * 5000, limit)) <= limit


def test_reported_omission_count_is_accurate() -> None:
    text = "a" * 50 + "b" * 50
    out = truncate_middle(text, 60)
    kept = len(out) - len(out.split("\n")[1]) - 2
    assert f"[{len(text) - kept} characters truncated]" in out


def test_negative_limit_rejected() -> None:
    with pytest.raises(ValueError):
        truncate_middle("x", -1)
