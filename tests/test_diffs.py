import pytest

from pyagent import diffs
from pyagent.diffs import unified_diff


def test_diff_shows_changed_lines() -> None:
    out = unified_diff("a\nb\nc\n", "a\nB\nc\n", "f.txt")
    assert out.splitlines() == [
        "--- a/f.txt",
        "+++ b/f.txt",
        "@@ -1,3 +1,3 @@",
        " a",
        "-b",
        "+B",
        " c",
    ]


def test_identical_text_has_empty_diff() -> None:
    assert unified_diff("same", "same", "f") == ""


def test_long_diffs_are_clipped(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(diffs, "MAX_DIFF_LINES", 5)
    out = unified_diff("", "\n".join(str(i) for i in range(50)), "f")
    assert out.splitlines()[-1].startswith("... (")
    assert len(out.splitlines()) == 6
