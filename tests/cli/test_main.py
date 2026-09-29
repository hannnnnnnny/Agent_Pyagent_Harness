import io
from pathlib import Path

import pytest

from pyagent.cli.main import (
    EXIT_INCOMPLETE,
    EXIT_OK,
    EXIT_USAGE,
    IO,
    apply_overrides,
    build_parser,
    main,
)
from pyagent.cli.starter import STARTER_CONFIG
from pyagent.config import CONFIG_FILENAME, Config, parse_config
from pyagent.errors import ConfigError
from pyagent.messages import ModelResponse
from pyagent.providers.scripted import ScriptedProvider, text_turn, tool_turn
from pyagent.safety.modes import ApprovalMode

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10
    import tomli as tomllib  # type: ignore[no-redef]


class Term:
    def __init__(self, stdin: str = "", interactive: bool = False) -> None:
        self.io = IO(io.StringIO(stdin), io.StringIO(), io.StringIO(), interactive)

    @property
    def out(self) -> str:
        return self.io.stdout.getvalue()  # type: ignore[attr-defined, no-any-return]

    @property
    def err(self) -> str:
        return self.io.stderr.getvalue()  # type: ignore[attr-defined, no-any-return]


def factory(*turns: ModelResponse) -> tuple[ScriptedProvider, object]:
    provider = ScriptedProvider(list(turns))
    return provider, lambda config: provider


def test_run_prints_answer_and_summary(tmp_path: Path) -> None:
    _, make = factory(text_turn("Hello there."))
    term = Term()
    code = main(["run", "say hi", "-w", str(tmp_path)], io=term.io, provider_factory=make)
    assert code == EXIT_OK
    assert "Hello there." in term.out
    assert "[completed] 1 turns" in term.out


def test_non_interactive_run_denies_writes(tmp_path: Path) -> None:
    _, make = factory(
        tool_turn(("write_file", {"path": "a.txt", "content": "x"})), text_turn("could not")
    )
    term = Term()
    main(["run", "write", "-w", str(tmp_path)], io=term.io, provider_factory=make)
    assert not (tmp_path / "a.txt").exists()
    assert "declined" in term.out


def test_interactive_run_asks_and_writes(tmp_path: Path) -> None:
    _, make = factory(
        tool_turn(("write_file", {"path": "a.txt", "content": "x"})), text_turn("written")
    )
    term = Term(stdin="y\n", interactive=True)
    main(["run", "write", "-w", str(tmp_path)], io=term.io, provider_factory=make)
    assert (tmp_path / "a.txt").read_text() == "x"
    assert "[approval needed] write_file: a.txt" in term.out


def test_incomplete_run_exit_code(tmp_path: Path) -> None:
    _, make = factory(*[tool_turn(("list_dir", {})) for _ in range(3)])
    term = Term()
    code = main(
        ["run", "loop", "-w", str(tmp_path), "--max-turns", "2"], io=term.io, provider_factory=make
    )
    assert code == EXIT_INCOMPLETE
    assert "[budget]" in term.out


def test_chat_runs_until_exit(tmp_path: Path) -> None:
    provider, make = factory(text_turn("one"), text_turn("two"))
    term = Term(stdin="first\n\nsecond\n/exit\n")
    assert main(["chat", "-w", str(tmp_path)], io=term.io, provider_factory=make) == EXIT_OK
    assert "one" in term.out
    assert "two" in term.out
    assert len(provider.requests) == 2


def test_policy_command(tmp_path: Path) -> None:
    term = Term()
    main(["policy", "sudo rm -rf /", "-w", str(tmp_path)], io=term.io)
    assert term.out.startswith("BLOCK: privilege escalation")


def test_policy_respects_config_allow_list(tmp_path: Path) -> None:
    (tmp_path / CONFIG_FILENAME).write_text('[shell]\nallow = ["make test"]\n')
    term = Term()
    main(["policy", "make test", "-w", str(tmp_path)], io=term.io)
    assert term.out.strip() == "ALLOW"


def test_audit_command(tmp_path: Path) -> None:
    _, make = factory(text_turn("ok"))
    main(["run", "hi", "-w", str(tmp_path)], io=Term().io, provider_factory=make)
    term = Term()
    main(["audit", "-w", str(tmp_path), "-n", "1"], io=term.io)
    assert "run_finished" in term.out
    assert "run_started" not in term.out


def test_audit_command_without_log(tmp_path: Path) -> None:
    term = Term()
    main(["audit", "-w", str(tmp_path)], io=term.io)
    assert "no audit records" in term.out


def test_init_writes_starter_config_once(tmp_path: Path) -> None:
    assert main(["init", "-w", str(tmp_path)], io=Term().io) == EXIT_OK
    assert (tmp_path / CONFIG_FILENAME).read_text() == STARTER_CONFIG
    term = Term()
    assert main(["init", "-w", str(tmp_path)], io=term.io) == EXIT_USAGE
    assert "already exists" in term.err


def test_starter_config_is_valid() -> None:
    assert parse_config(tomllib.loads(STARTER_CONFIG)) == Config()


def test_bad_config_is_a_usage_error(tmp_path: Path) -> None:
    (tmp_path / CONFIG_FILENAME).write_text("[shel]\n")
    term = Term()
    assert main(["run", "x", "-w", str(tmp_path)], io=term.io) == EXIT_USAGE
    assert "unknown config keys" in term.err


def test_missing_workspace_is_a_usage_error(tmp_path: Path) -> None:
    term = Term()
    assert main(["run", "x", "-w", str(tmp_path / "nope")], io=term.io) == EXIT_USAGE


def test_overrides_win_over_config() -> None:
    args = build_parser().parse_args(
        ["run", "t", "--mode", "read-only", "--model", "m", "--max-cost", "2", "--no-audit"]
    )
    config = apply_overrides(Config(), args)
    assert config.mode is ApprovalMode.READ_ONLY
    assert config.model == "m"
    assert config.max_cost_usd == 2
    assert config.audit is False


@pytest.mark.parametrize("flags", [["--max-turns", "0"], ["--max-cost", "-1"]])
def test_non_positive_overrides_rejected(flags: list[str]) -> None:
    args = build_parser().parse_args(["run", "t", *flags])
    with pytest.raises(ConfigError, match="must be positive"):
        apply_overrides(Config(), args)
