import pytest

from pyagent.errors import ToolError
from pyagent.tools.builtin.editing import match_line_endings, replace_exact


def test_lf_fragment_is_converted_for_crlf_text() -> None:
    assert match_line_endings("a\r\nb\r\n", "a\nb") == "a\r\nb"


@pytest.mark.parametrize(
    ("text", "fragment"),
    [("a\nb\n", "a\nb"), ("a\r\nb", "single line"), ("a\r\nb", "a\r\nb")],
)
def test_fragment_left_alone_otherwise(text: str, fragment: str) -> None:
    assert match_line_endings(text, fragment) == fragment


def test_replace_in_crlf_file_keeps_crlf() -> None:
    text, count = replace_exact("x = 1\r\ny = 2\r\n", "x = 1\ny = 2", "x = 3\ny = 4")
    assert (text, count) == ("x = 3\r\ny = 4\r\n", 1)


def test_errors_carry_the_label() -> None:
    with pytest.raises(ToolError, match="edit 3: old_string was not found"):
        replace_exact("abc", "zzz", "y", label="edit 3")


def test_ambiguity_and_replace_all() -> None:
    with pytest.raises(ToolError, match="matches 2 times"):
        replace_exact("aa", "a", "b")
    assert replace_exact("aa", "a", "b", replace_all=True) == ("bb", 2)


def test_identical_strings_rejected() -> None:
    with pytest.raises(ToolError, match="identical"):
        replace_exact("a", "a", "a")
