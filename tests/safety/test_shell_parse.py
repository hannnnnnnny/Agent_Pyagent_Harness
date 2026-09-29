import pytest

from pyagent.safety.shell_parse import ShellParseError, parse_command


def test_simple_command() -> None:
    parsed = parse_command("git status --short")
    assert parsed.segments == [["git", "status", "--short"]]
    assert parsed.programs == ["git"]
    assert not parsed.has_substitution


@pytest.mark.parametrize(
    ("command", "programs"),
    [
        ("ls; pwd", ["ls", "pwd"]),
        ("make && make test || echo fail", ["make", "make", "echo"]),
        ("cat a | grep x | wc -l", ["cat", "grep", "wc"]),
        ("sleep 1 & echo hi", ["sleep", "echo"]),
        ("(cd src && ls)", ["cd", "ls"]),
        ("echo one\nrm x", ["echo", "rm"]),
    ],
)
def test_segments_split_on_control_operators(command: str, programs: list[str]) -> None:
    assert parse_command(command).programs == programs


def test_quoted_operators_are_not_split() -> None:
    parsed = parse_command("echo 'a; rm -rf /' \"b && c\"")
    assert parsed.segments == [["echo", "a; rm -rf /", "b && c"]]


def test_redirect_targets_are_collected() -> None:
    parsed = parse_command("python gen.py > out.txt 2>&1 >> /etc/passwd")
    assert parsed.redirect_targets == ["out.txt", "/etc/passwd"]
    assert parsed.segments == [["python", "gen.py"]]


def test_input_redirect_target_is_collected() -> None:
    assert parse_command("wc -l < data.txt").redirect_targets == ["data.txt"]


@pytest.mark.parametrize(
    "command",
    ["echo $(whoami)", "echo `id`", "diff <(ls a) <(ls b)", 'echo "$(cat /etc/shadow)"'],
)
def test_substitutions_are_flagged(command: str) -> None:
    assert parse_command(command).has_substitution


def test_unbalanced_quotes_raise() -> None:
    with pytest.raises(ShellParseError):
        parse_command("echo 'oops")


def test_empty_command_has_no_segments() -> None:
    assert parse_command("   ").segments == []
