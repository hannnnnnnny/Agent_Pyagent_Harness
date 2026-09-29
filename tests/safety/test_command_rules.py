import pytest

from pyagent.safety.command_rules import ask_rules, block_rules, effective_argv, program_name
from pyagent.safety.verdict import Verdict


@pytest.mark.parametrize(
    ("token", "name"),
    [("ls", "ls"), ("/usr/bin/Python3", "python3"), ("C:\\Tools\\GIT.EXE", "git")],
)
def test_program_name_normalization(token: str, name: str) -> None:
    assert program_name(token) == name


@pytest.mark.parametrize(
    ("segment", "argv"),
    [
        (["FOO=1", "BAR=2", "make"], ["make"]),
        (["env", "-i", "sudo", "id"], ["sudo", "id"]),
        (["timeout", "-s", "KILL", "10", "rm", "x"], ["rm", "x"]),
        (["nohup", "nice", "-n", "5", "python", "a.py"], ["python", "a.py"]),
        (["xargs", "-I", "{}", "rm", "{}"], ["rm", "{}"]),
        (["env", "-u", "HOME", "curl", "x"], ["curl", "x"]),
        (["FOO=1"], []),
    ],
)
def test_effective_argv_unwraps(segment: list[str], argv: list[str]) -> None:
    assert effective_argv(segment) == argv


@pytest.mark.parametrize(
    "argv",
    [
        ["sudo", "ls"],
        ["su", "-"],
        ["mkfs.ext4", "/dev/sda1"],
        ["shutdown", "-h", "now"],
        ["dd", "if=/dev/zero", "of=/dev/sda"],
        ["rm", "-rf", "/"],
        ["rm", "-fr", "~"],
        ["rm", "-r", "--no-preserve-root", "/"],
        ["rm", "--recursive", "."],
        ["rm", "-Rf", "$HOME"],
        ["rm", "-rf", "/*"],
        ["chmod", "-R", "777", "/"],
        ["crontab", "-e"],
    ],
)
def test_catastrophic_commands_are_blocked(argv: list[str]) -> None:
    result = block_rules(argv)
    assert result is not None
    assert result.verdict is Verdict.BLOCK


@pytest.mark.parametrize(
    "argv",
    [["rm", "file.txt"], ["rm", "-rf", "build"], ["dd", "if=a", "of=b"], ["chmod", "+x", "run.sh"]],
)
def test_ordinary_commands_are_not_blocked(argv: list[str]) -> None:
    assert block_rules(argv) is None


@pytest.mark.parametrize(
    ("argv", "reason"),
    [
        (["curl", "https://example.com"], "network"),
        (["ssh", "host"], "network"),
        (["git", "push", "origin", "main"], "remote"),
        (["git", "-C", "repo", "fetch"], "remote"),
        (["git", "-c", "core.pager=sh", "log"], "config overrides"),
        (["git", "reset", "--hard"], "discard"),
        (["git", "checkout", "--", "."], "discard"),
        (["git", "branch", "-D", "feature"], "deletion"),
        (["pip", "install", "requests"], "third-party"),
        (["npm", "install"], "third-party"),
        (["find", ".", "-name", "*.pyc", "-delete"], "deletes"),
        (["rm", "old.txt"], "destroy"),
        (["mv", "a", "b"], "destroy"),
    ],
)
def test_risky_commands_need_approval(argv: list[str], reason: str) -> None:
    result = ask_rules(argv)
    assert result is not None
    assert result.verdict is Verdict.ASK
    assert reason in result.reason


@pytest.mark.parametrize(
    "argv",
    [["git", "status"], ["git", "log", "-5"], ["pip", "list"], ["find", ".", "-name", "x"]],
)
def test_benign_commands_need_no_special_approval(argv: list[str]) -> None:
    assert ask_rules(argv) is None
