"""Environment self-checks behind ``pyagent doctor``.

Checks report whether something is present, never its value: the doctor must
be safe to run and paste into a bug report.
"""

from __future__ import annotations

import os
import shutil
import sys
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path

from pyagent.config import load_config
from pyagent.errors import ConfigError

OK, WARN, FAIL = "ok", "warn", "fail"


@dataclass(frozen=True)
class Check:
    name: str
    status: str
    detail: str


def check_python() -> Check:
    version = ".".join(map(str, sys.version_info[:3]))
    status = OK if sys.version_info >= (3, 10) else FAIL
    return Check("python", status, version)


def check_credentials(environ: Mapping[str, str], home: Path) -> Check:
    for name in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN"):
        if environ.get(name):
            return Check("credentials", OK, f"{name} is set")
    if (home / ".config" / "anthropic").is_dir():
        return Check("credentials", OK, "an `ant auth login` profile directory exists")
    return Check(
        "credentials",
        WARN,
        "no API key or profile found; set ANTHROPIC_API_KEY or run `ant auth login`",
    )


def check_shell(which: Callable[[str], str | None] = shutil.which) -> Check:
    for name in ("bash", "sh"):
        path = which(name)
        if path:
            return Check("shell", OK, f"{name} at {path}")
    return Check(
        "shell",
        WARN,
        "no POSIX shell found; run_shell falls back to cmd.exe, which the policy does not parse",
    )


def check_config(root: Path) -> Check:
    try:
        config = load_config(root)
    except ConfigError as exc:
        return Check("config", FAIL, str(exc))
    source = config.source.name if config.source else "defaults (no pyagent.toml)"
    return Check("config", OK, f"{source}; mode={config.mode.value}")


def check_state_dir(root: Path) -> Check:
    if os.access(root, os.W_OK):
        return Check("workspace", OK, f"{root} is writable")
    return Check("workspace", FAIL, f"{root} is not writable; sessions and audit logs will fail")


def run_checks(root: Path, environ: Mapping[str, str] | None = None) -> list[Check]:
    env = os.environ if environ is None else environ
    return [
        check_python(),
        check_credentials(env, Path.home()),
        check_shell(),
        check_config(root),
        check_state_dir(root),
    ]
