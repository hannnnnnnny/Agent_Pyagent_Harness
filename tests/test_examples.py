"""The examples are documentation; make sure they keep working."""

import subprocess
import sys
from pathlib import Path

import pytest

EXAMPLES = sorted((Path(__file__).resolve().parent.parent / "examples").glob("*.py"))


@pytest.mark.parametrize("example", EXAMPLES, ids=lambda p: p.name)
def test_example_runs_successfully(example: Path) -> None:
    result = subprocess.run(  # noqa: S603 - runs our own example scripts
        [sys.executable, str(example)],
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "[completed]" in result.stdout


def test_examples_exist() -> None:
    assert {p.name for p in EXAMPLES} >= {"offline_demo.py", "custom_tool.py"}
