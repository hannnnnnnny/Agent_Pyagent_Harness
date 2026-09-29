"""Decides whether a full shell command line may run."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field

from pyagent.errors import SafetyError
from pyagent.safety.command_rules import ask_rules, block_rules, effective_argv, program_name
from pyagent.safety.shell_parse import ParsedCommand, ShellParseError, parse_command
from pyagent.safety.verdict import Assessment, strictest
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
        results = [self._assess_segment(effective_argv(seg)) for seg in parsed.segments]
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
