"""Environment scrubbing for subprocesses the agent launches."""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping

# Variables needed for ordinary tools to work. Everything else is dropped by
# default: an allowlist cannot be bypassed by a secret with an unusual name.
DEFAULT_PASSTHROUGH = frozenset(
    {
        "PATH",
        "PATHEXT",
        "HOME",
        "USERPROFILE",
        "LANG",
        "LC_ALL",
        "LC_CTYPE",
        "TERM",
        "TZ",
        "TMP",
        "TEMP",
        "TMPDIR",
        "SYSTEMROOT",
        "SYSTEMDRIVE",
        "WINDIR",
        "COMSPEC",
        "SHELL",
        "PYTHONIOENCODING",
        "VIRTUAL_ENV",
    }
)

# Names that look secret are never passed, even if a user allowlists them by pattern.
SECRET_NAME = re.compile(
    r"(KEY|TOKEN|SECRET|PASSWORD|PASSWD|CREDENTIAL|AUTH|SESSION|COOKIE|PRIVATE)",
    re.IGNORECASE,
)


def scrub_env(
    source: Mapping[str, str],
    passthrough: Iterable[str] = DEFAULT_PASSTHROUGH,
    extra: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Build a subprocess environment containing only safe variables.

    Windows environment names are case-insensitive, so matching is too.
    """
    allowed = {name.upper() for name in passthrough}
    env = {
        name: value
        for name, value in source.items()
        if name.upper() in allowed and not SECRET_NAME.search(name)
    }
    env.update(extra or {})
    return env
