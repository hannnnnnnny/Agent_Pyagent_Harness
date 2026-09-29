from pathlib import Path

import pytest

from pyagent import instructions
from pyagent.errors import ConfigError
from pyagent.instructions import combine_instructions, load_instructions_file


def test_loads_file_contents(tmp_path: Path) -> None:
    (tmp_path / "AGENTS.md").write_text("\n  Use tabs.  \n")
    assert load_instructions_file(tmp_path, "AGENTS.md") == "Use tabs."


@pytest.mark.parametrize("name", ["../outside.md", ".env", "missing.md"])
def test_sandbox_rules_apply(tmp_path: Path, name: str) -> None:
    (tmp_path / ".env").write_text("SECRET=1")
    with pytest.raises(ConfigError, match="cannot use instructions_file"):
        load_instructions_file(tmp_path, name)


def test_size_is_capped(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(instructions, "MAX_INSTRUCTIONS_BYTES", 10)
    (tmp_path / "AGENTS.md").write_text("x" * 100)
    with pytest.raises(ConfigError, match="read limit"):
        load_instructions_file(tmp_path, "AGENTS.md")


@pytest.mark.parametrize(
    ("inline", "from_file", "expected"),
    [("A", "B", "A\n\nB"), ("", "B", "B"), ("A", "  ", "A"), ("", "", "")],
)
def test_combine(inline: str, from_file: str, expected: str) -> None:
    assert combine_instructions(inline, from_file) == expected
