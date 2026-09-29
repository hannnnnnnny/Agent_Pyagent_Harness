"""Glob rules for files that stay off-limits even inside the workspace."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from fnmatch import fnmatchcase

from pyagent.errors import SandboxViolation

# Files that commonly hold credentials. Reading them would put secrets into the
# model context, where they can be echoed or exfiltrated.
DEFAULT_NO_READ: tuple[str, ...] = (
    ".env",
    ".env.*",
    "*.pem",
    "*.key",
    "*.p12",
    "*.pfx",
    "id_rsa*",
    "id_ecdsa*",
    "id_ed25519*",
    ".netrc",
    ".pypirc",
    ".npmrc",
    ".git-credentials",
    ".git/config",
    ".aws/**",
    ".ssh/**",
    ".pyagent/**",
)

# Writes here could rewrite history, install hooks, or tamper with audit logs.
DEFAULT_NO_WRITE: tuple[str, ...] = (".git/**", ".git", *DEFAULT_NO_READ)


def _matches(rel_path: str, patterns: Iterable[str]) -> str | None:
    name = rel_path.rsplit("/", 1)[-1]
    lowered = rel_path.lower()
    for pattern in patterns:
        pat = pattern.lower()
        # Directory rules apply at any depth, e.g. vendored repos' .git folders.
        if pat.endswith("/**"):
            if f"/{pat[:-3]}/" in f"/{lowered}/":
                return pattern
            continue
        # Case-folded so rules hold on case-insensitive filesystems.
        if "/" in pat:
            if fnmatchcase(lowered, pat) or fnmatchcase(lowered, "*/" + pat):
                return pattern
        elif fnmatchcase(name.lower(), pat):
            return pattern
    return None


@dataclass(frozen=True)
class ProtectedPaths:
    """Deny rules evaluated against workspace-relative POSIX paths."""

    no_read: tuple[str, ...] = DEFAULT_NO_READ
    no_write: tuple[str, ...] = DEFAULT_NO_WRITE
    allow: tuple[str, ...] = field(default=())

    def check_read(self, rel_path: str) -> None:
        self._check(rel_path, self.no_read, "read")

    def check_write(self, rel_path: str) -> None:
        self._check(rel_path, self.no_write, "write")

    def _check(self, rel_path: str, patterns: tuple[str, ...], action: str) -> None:
        if _matches(rel_path, self.allow):
            return
        rule = _matches(rel_path, patterns)
        if rule is not None:
            raise SandboxViolation(f"{action} of {rel_path!r} is blocked by rule {rule!r}")
