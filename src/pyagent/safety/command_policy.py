"""Decides whether a full shell command line may run."""

from __future__ import annotations

import itertools
import os
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

from pyagent.errors import SafetyError
from pyagent.safety.command_rules import ask_rules, block_rules, effective_argv, program_name
from pyagent.safety.shell_parse import ParsedCommand, ShellParseError, parse_command
from pyagent.safety.verdict import Assessment, Verdict, strictest
from pyagent.safety.workspace import Workspace

# Read-only inspection commands that run without approval by default.
DEFAULT_SAFE_PROGRAMS = frozenset(
    {
        "ls",
        "dir",
        "pwd",
        "cat",
        "head",
        "tail",
        "wc",
        "echo",
        "grep",
        "rg",
        "find",
        "sort",
        "uniq",
        "diff",
        "which",
        "where",
        "file",
        "stat",
        "tree",
        "date",
        "true",
        "false",
    }
)
DEFAULT_SAFE_GIT = frozenset(
    {"status", "diff", "log", "show", "branch", "blame", "ls-files", "rev-parse", "grep"}
)
_INTERPRETERS = frozenset(
    {"sh", "bash", "zsh", "dash", "fish", "python", "python3", "perl", "ruby", "node", "pwsh"}
)
_DOWNLOADERS = frozenset({"curl", "wget", "iwr", "invoke-webrequest"})
_GLOB_CHARS = frozenset("*?[")
MAX_GLOB_MATCHES = 1000


@dataclass(frozen=True)
class CommandPolicy:
    """Allow/ask/block decisions for shell commands.

    ``allow_prefixes`` lets users pre-approve commands such as ``pytest`` or
    ``npm test``; a command is auto-allowed only if every segment matches.
    """

    safe_programs: frozenset[str] = DEFAULT_SAFE_PROGRAMS
    safe_git: frozenset[str] = DEFAULT_SAFE_GIT
    allow_prefixes: tuple[str, ...] = field(default=())
    blocked_programs: frozenset[str] = field(default=frozenset())

    def assess(self, command: str, workspace: Workspace) -> Assessment:
        try:
            parsed = parse_command(command)
        except ShellParseError as exc:
            return Assessment.block(f"could not parse command: {exc}")
        if not parsed.segments:
            return Assessment.block("empty command")
        argvs = [effective_argv(seg) for seg in parsed.segments]
        results = [self._assess_segment(argv) for argv in argvs]
        results.extend(_argument_rules(argv, workspace) for argv in argvs if argv)
        results.append(_pipeline_rules(parsed))
        results.append(_redirect_rules(parsed, workspace))
        if parsed.has_substitution:
            results.append(Assessment.ask("command substitution hides what will run"))
        return strictest(results)

    def _assess_segment(self, argv: list[str]) -> Assessment:
        if not argv:
            return Assessment.allow()
        prog = program_name(argv[0])
        if prog in self.blocked_programs:
            return Assessment.block(f"{prog} is blocked by configuration")
        for rule in (block_rules, ask_rules):
            result = rule(argv)
            if result is not None:
                return result
        if self._is_safe(prog, argv) or self._is_preapproved(argv):
            return Assessment.allow()
        return Assessment.ask(f"{prog} is not in the auto-approved command list")

    def _is_safe(self, prog: str, argv: list[str]) -> bool:
        if prog == "git":
            sub = next((a for a in argv[1:] if not a.startswith("-")), None)
            return sub in self.safe_git
        return prog in self.safe_programs

    def _is_preapproved(self, argv: list[str]) -> bool:
        line = " ".join([program_name(argv[0]), *argv[1:]])
        return any(line == p or line.startswith(p + " ") for p in self.allow_prefixes)


def _pipeline_rules(parsed: ParsedCommand) -> Assessment:
    programs = {program_name(p) for p in parsed.programs}
    if programs & _DOWNLOADERS and programs & _INTERPRETERS:
        return Assessment.block("downloading and executing code in one command")
    return Assessment.allow()


def _argument_rules(argv: list[str], workspace: Workspace) -> Assessment:
    """Flag arguments naming protected files or locations outside the workspace.

    Shell globbing and variables can still smuggle paths past this check, which
    is why shell access also relies on approvals and a scrubbed environment.
    """
    for arg in argv[1:]:
        if arg.startswith("-") or "://" in arg or "=" in arg:
            continue
        result = _assess_argument(arg, workspace)
        if result.verdict is not Verdict.ALLOW:
            return result
    return Assessment.allow()


def _protected(rel_path: str, workspace: Workspace) -> str | None:
    try:
        workspace.protected.check_read(rel_path)
    except SafetyError as exc:
        return str(exc)
    return None


def _assess_argument(arg: str, workspace: Workspace) -> Assessment:
    # Match the text itself too, so "~/.ssh/id_rsa" is caught outside the workspace.
    reason = _protected(arg.replace("\\", "/").lstrip("~/"), workspace)
    if reason:
        return Assessment.block(f"argument {arg!r} names a protected file: {reason}")
    if "$" in arg:
        return Assessment.ask(f"argument {arg!r} uses shell variables the policy cannot see")
    if _GLOB_CHARS.intersection(arg):
        return _assess_glob(arg, workspace)
    try:
        resolved = Path(os.path.expanduser(arg))
        if not resolved.is_absolute():
            resolved = workspace.root / resolved
        resolved = resolved.resolve()
    except (OSError, ValueError, RuntimeError):
        return Assessment.allow()
    return _assess_path(arg, resolved, workspace)


def _assess_path(arg: str, resolved: Path, workspace: Workspace) -> Assessment:
    if not workspace.contains(resolved):
        return Assessment.ask(f"argument {arg!r} is outside the workspace")
    reason = _protected(workspace.relative(resolved), workspace)
    if reason:
        return Assessment.block(f"argument {arg!r} names a protected file: {reason}")
    return Assessment.allow()


def _assess_glob(arg: str, workspace: Workspace) -> Assessment:
    """Expand a glob the way the shell will, and judge every match.

    Python's glob also matches dotfiles, which errs on the side of blocking.
    """
    pattern = arg.replace("\\", "/")
    if pattern.startswith(("/", "~")) or ".." in pattern.split("/") or ":" in pattern:
        return Assessment.ask(f"glob {arg!r} may expand outside the workspace")
    try:
        matches = list(itertools.islice(workspace.root.glob(pattern), MAX_GLOB_MATCHES))
    except (OSError, ValueError, NotImplementedError):
        return Assessment.ask(f"glob {arg!r} could not be checked")
    for match in matches:
        result = _assess_path(arg, match.resolve(), workspace)
        if result.verdict is not Verdict.ALLOW:
            return result
    return Assessment.allow()


def _redirect_rules(parsed: ParsedCommand, workspace: Workspace) -> Assessment:
    for target in parsed.redirect_targets:
        if target in {"/dev/null", "NUL", "nul"}:
            continue
        try:
            workspace.resolve_for_write(target)
        except SafetyError as exc:
            return Assessment.block(f"redirect to {target!r} is not allowed: {exc}")
    return Assessment.allow()


def merge_allow_prefixes(policy: CommandPolicy, prefixes: Iterable[str]) -> CommandPolicy:
    """Return a copy of ``policy`` that also pre-approves ``prefixes``."""
    combined = tuple(dict.fromkeys([*policy.allow_prefixes, *prefixes]))
    return CommandPolicy(
        safe_programs=policy.safe_programs,
        safe_git=policy.safe_git,
        allow_prefixes=combined,
        blocked_programs=policy.blocked_programs,
    )
