import os
import sys
from pathlib import Path

import pytest

from pyagent.safety.process import default_shell, run_command

PY = sys.executable.replace("\\", "/")


def _env() -> dict[str, str]:
    keep = ("PATH", "SYSTEMROOT", "COMSPEC", "TEMP", "TMP")
    return {k: v for k, v in os.environ.items() if k.upper() in keep}


def test_default_shell_is_found() -> None:
    assert default_shell()


def test_captures_stdout_and_stderr(tmp_path: Path) -> None:
    code = "import sys; print('out'); print('err', file=sys.stderr)"
    result = run_command(f'"{PY}" -c "{code}"', tmp_path, _env())
    assert result.exit_code == 0
    assert "out" in result.output
    assert "err" in result.output


def test_nonzero_exit_code(tmp_path: Path) -> None:
    result = run_command(f'"{PY}" -c "raise SystemExit(3)"', tmp_path, _env())
    assert result.exit_code == 3
    assert not result.timed_out


def test_runs_in_working_directory(tmp_path: Path) -> None:
    (tmp_path / "marker.txt").write_text("")
    result = run_command(f'"{PY}" -c "import os; print(os.listdir())"', tmp_path, _env())
    assert "marker.txt" in result.output


def test_timeout_kills_the_process(tmp_path: Path) -> None:
    result = run_command(f'"{PY}" -c "import time; time.sleep(30)"', tmp_path, _env(), timeout=1)
    assert result.timed_out
    assert result.exit_code is None


def test_output_is_truncated(tmp_path: Path) -> None:
    result = run_command(f'"{PY}" -c "print(\'x\' * 5000)"', tmp_path, _env(), max_output_chars=100)
    assert len(result.output) <= 100


def test_environment_is_exactly_what_was_passed(tmp_path: Path) -> None:
    env = {**_env(), "ONLY_THIS": "yes"}
    code = "import os; print(sorted(k for k in os.environ if k.startswith('ANTHROPIC')))"
    result = run_command(f'"{PY}" -c "{code}"', tmp_path, env)
    assert "[]" in result.output


@pytest.mark.skipif(os.name == "nt", reason="stdin semantics differ under Windows shells")
def test_stdin_is_closed(tmp_path: Path) -> None:
    result = run_command(f'"{PY}" -c "import sys; print(repr(sys.stdin.read()))"', tmp_path, _env())
    assert "''" in result.output
