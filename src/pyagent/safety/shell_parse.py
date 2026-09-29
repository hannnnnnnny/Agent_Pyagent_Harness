"""Best-effort structural parsing of shell command lines for policy checks.

This is not a full shell parser. It errs on the side of reporting *more*
structure (substitutions, redirects) so the policy can ask rather than allow
when a command is hard to reason about.
"""

from __future__ import annotations

import re
import shlex
from dataclasses import dataclass, field

_SEPARATORS = frozenset({";", "&&", "||", "|", "&", "|&", ";;"})
_PUNCT = set(";&|<>()")
# $(...), `...`, <(...), >(...) all run nested commands the policy cannot see.
_SUBSTITUTION = re.compile(r"\$\(|`|<\(|>\(")


@dataclass(frozen=True)
class ParsedCommand:
    segments: list[list[str]] = field(default_factory=list)
    redirect_targets: list[str] = field(default_factory=list)
    has_substitution: bool = False

    @property
    def programs(self) -> list[str]:
        return [segment[0] for segment in self.segments if segment]


class ShellParseError(ValueError):
    """Raised for command lines that cannot be tokenized (e.g. unbalanced quotes)."""


def _tokenize(command: str) -> list[str]:
    lexer = shlex.shlex(command.replace("\n", " ; "), posix=True, punctuation_chars=";&|<>()")
    lexer.whitespace_split = True
    lexer.commenters = ""
    try:
        return list(lexer)
    except ValueError as exc:
        raise ShellParseError(str(exc)) from exc


def _is_operator(token: str) -> bool:
    return bool(token) and all(ch in _PUNCT for ch in token)


def parse_command(command: str) -> ParsedCommand:
    """Split ``command`` into simple-command segments and collect redirects."""
    segments: list[list[str]] = [[]]
    redirects: list[str] = []
    expect_target = False
    for token in _tokenize(command):
        if expect_target:
            redirects.append(token)
            expect_target = False
            continue
        if not _is_operator(token):
            segments[-1].append(token)
            continue
        if token in _SEPARATORS:
            segments.append([])
        elif ">" in token or "<" in token:
            # "2>&1" style duplications name a descriptor, not a file.
            expect_target = not token.endswith("&")
            if segments[-1] and segments[-1][-1].isdigit():
                segments[-1].pop()
        # Parentheses (subshells, groups) carry no program name; drop them.
    return ParsedCommand(
        segments=[s for s in segments if s],
        redirect_targets=redirects,
        has_substitution=bool(_SUBSTITUTION.search(command)),
    )
