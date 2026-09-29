"""Running shell commands with timeouts, output caps, and process-tree cleanup."""

from __future__ import annotations

import contextlib
import os
import shutil
import signal
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from pyagent.text import truncate_middle

DEFAULT_TIMEOUT_SECONDS = 120
DEFAULT_MAX_OUTPUT_CHARS = 30_000


@dataclass(frozen=True)
class ProcessResult:
    exit_code: int | None
    output: str
    timed_out: bool = False


def default_shell() -> list[str]:
    """The argv prefix used to run a command string.

    A POSIX shell is preferred everywhere because the command policy parses
    POSIX syntax; cmd.exe is only a last resort on Windows.
    """
    for name in ("bash", "sh"):
        found = shutil.which(name)
        if found:
            return [found, "-c"]
    if os.name == "nt":
        return [os.environ.get("COMSPEC", "cmd.exe"), "/d", "/s", "/c"]
    raise RuntimeError("no shell found on PATH")


def _kill_tree(proc: subprocess.Popen[bytes]) -> None:
    if sys.platform == "win32":
        # taskkill /T also terminates grandchildren that Popen.kill would orphan.
        subprocess.run(  # noqa: S603 - fixed argv, pid is an int we own
            ["taskkill", "/F", "/T", "/PID", str(proc.pid)],  # noqa: S607
            capture_output=True,
            check=False,
        )
    else:
        with contextlib.suppress(ProcessLookupError):
            os.killpg(proc.pid, signal.SIGKILL)
    proc.kill()


def run_command(
    command: str,
    cwd: Path,
    env: dict[str, str],
    *,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    max_output_chars: int = DEFAULT_MAX_OUTPUT_CHARS,
    shell: list[str] | None = None,
) -> ProcessResult:
    """Run ``command`` and return its combined stdout/stderr.

    The command has already been approved by the policy layer; this function
    only bounds its resources. stdin is closed so interactive prompts fail fast.
    """
    argv = [*(shell or default_shell()), command]
    popen_kwargs: dict[str, object] = {}
    if sys.platform == "win32":
        popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        popen_kwargs["start_new_session"] = True
    proc = subprocess.Popen(  # noqa: S603 - command vetted by CommandPolicy
        argv,
        cwd=cwd,
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        **popen_kwargs,  # type: ignore[call-overload]
    )
    try:
        raw, _ = proc.communicate(timeout=timeout)
        timed_out = False
    except subprocess.TimeoutExpired:
        _kill_tree(proc)
        raw, _ = proc.communicate()
        timed_out = True
    output = truncate_middle(raw.decode("utf-8", errors="replace"), max_output_chars)
    return ProcessResult(None if timed_out else proc.returncode, output, timed_out)
