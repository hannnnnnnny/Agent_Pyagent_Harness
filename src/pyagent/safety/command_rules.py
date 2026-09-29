"""Individual rules that classify one simple command (a single segment)."""

from __future__ import annotations

import re
from pathlib import PurePath

from pyagent.safety.verdict import Assessment

_ASSIGNMENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
# Wrappers that run another program given as their arguments, mapped to the
# options that consume a following value (so the value isn't mistaken for the program).
_WRAPPERS: dict[str, frozenset[str]] = {
    "env": frozenset({"-u", "--unset", "-C", "--chdir"}),
    "nohup": frozenset(),
    "time": frozenset({"-f", "--format", "-o", "--output"}),
    "timeout": frozenset({"-s", "--signal", "-k", "--kill-after"}),
    "nice": frozenset({"-n", "--adjustment"}),
    "ionice": frozenset({"-c", "--class", "-n", "--classdata"}),
    "command": frozenset(),
    "builtin": frozenset(),
    "xargs": frozenset({"-I", "-n", "-P", "-L", "-d", "-E", "-s", "-a"}),
}


def _skip_wrapper_args(wrapper: str, argv: list[str]) -> None:
    takes_value = _WRAPPERS[wrapper]
    while argv:
        head = argv[0]
        if head in takes_value:
            del argv[:2]
        elif head.startswith("-") or (wrapper == "timeout" and head[:1].isdigit()):
            argv.pop(0)
        else:
            return


def program_name(token: str) -> str:
    """Normalize ``/usr/bin/Python3.EXE`` to ``python3``."""
    name = PurePath(token.replace("\\", "/")).name.lower()
    return name[:-4] if name.endswith(".exe") else name


def effective_argv(segment: list[str]) -> list[str]:
    """Strip ``VAR=value`` prefixes and wrapper programs to find what really runs."""
    argv = list(segment)
    while argv:
        if _ASSIGNMENT.match(argv[0]):
            argv.pop(0)
        elif program_name(argv[0]) in _WRAPPERS:
            _skip_wrapper_args(program_name(argv.pop(0)), argv)
        else:
            break
    return argv


def _flags(argv: list[str]) -> set[str]:
    """Expand combined short flags: ``-rf`` becomes {"-r", "-f"}."""
    flags: set[str] = set()
    for arg in argv[1:]:
        if arg.startswith("--"):
            flags.add(arg)
        elif arg.startswith("-") and len(arg) > 1:
            flags.update(f"-{ch}" for ch in arg[1:])
    return flags


PRIVILEGE = frozenset({"sudo", "su", "doas", "runas", "pkexec"})
SYSTEM = frozenset(
    {
        "shutdown",
        "reboot",
        "halt",
        "poweroff",
        "fdisk",
        "parted",
        "format",
        "diskpart",
        "mount",
        "umount",
        "systemctl",
        "launchctl",
        "crontab",
        "useradd",
        "userdel",
        "passwd",
    }
)
_ROOTISH = frozenset(
    {"/", "/*", "~", "~/", "~/*", "$HOME", "${HOME}", "*", ".", "..", "C:\\", "C:/"}
)


def block_rules(argv: list[str]) -> Assessment | None:
    """Commands that are never acceptable from an agent."""
    prog = program_name(argv[0])
    flags = _flags(argv)
    if prog in PRIVILEGE:
        return Assessment.block(f"privilege escalation via {prog}")
    if prog in SYSTEM or prog.startswith("mkfs"):
        return Assessment.block(f"system administration command {prog}")
    if prog == "dd" and any(a.startswith("of=/dev/") for a in argv):
        return Assessment.block("dd writing to a raw device")
    if prog == "rm" and ("-r" in flags or "-R" in flags or "--recursive" in flags):
        targets = [a for a in argv[1:] if not a.startswith("-")]
        if any(
            t.rstrip("/") in {"", "~", "$HOME", "${HOME}", ".", ".."} or t in _ROOTISH
            for t in targets
        ):
            return Assessment.block("recursive delete of a root, home, or workspace directory")
    recursive = "-R" in flags or "--recursive" in flags
    if prog in {"chmod", "chown"} and recursive and any(a in _ROOTISH for a in argv[1:]):
        return Assessment.block(f"recursive {prog} on a root or home directory")
    return None


NETWORK = frozenset(
    {
        "curl",
        "wget",
        "ssh",
        "scp",
        "sftp",
        "rsync",
        "nc",
        "ncat",
        "netcat",
        "socat",
        "telnet",
        "ftp",
        "invoke-webrequest",
        "iwr",
    }
)
_GIT_NETWORK = frozenset({"push", "pull", "fetch", "clone", "ls-remote", "submodule"})
_GIT_DESTRUCTIVE = frozenset({"reset", "clean", "rebase", "filter-branch", "gc", "prune"})
_INSTALLERS = {"pip": "install", "pip3": "install", "npm": "install", "yarn": "add", "uv": "add"}


# Global git options that consume the next argument.
_GIT_VALUE_OPTIONS = frozenset({"-C", "-c", "--git-dir", "--work-tree", "--namespace"})


def _git_subcommand(argv: list[str]) -> str | None:
    args = iter(argv[1:])
    for arg in args:
        if arg in _GIT_VALUE_OPTIONS:
            next(args, None)
        elif not arg.startswith("-"):
            return arg
    return None


def _git_rule(argv: list[str]) -> Assessment | None:
    if "-c" in argv or any(a.startswith("--config") for a in argv):
        return Assessment.ask("git config overrides can run arbitrary commands")
    sub = _git_subcommand(argv)
    reason = None
    if sub in _GIT_NETWORK:
        reason = f"git {sub} contacts a remote"
    elif sub in _GIT_DESTRUCTIVE or (sub == "checkout" and "--" in argv):
        reason = f"git {sub} can discard work"
    elif sub == "branch" and {"-D", "--delete"} & set(argv):
        reason = "git branch deletion can discard work"
    return Assessment.ask(reason) if reason else None


def _generic_rule(prog: str, argv: list[str]) -> str | None:
    if prog in NETWORK:
        return f"{prog} makes network connections"
    if prog in _INSTALLERS and _INSTALLERS[prog] in argv[1:]:
        return f"{prog} installs third-party code"
    if prog == "find" and {"-exec", "-execdir", "-ok", "-delete"} & set(argv):
        return "find with -exec/-delete runs commands or deletes files"
    if prog in {"rm", "rmdir", "mv", "shred", "truncate"}:
        return f"{prog} can destroy data"
    return None


def ask_rules(argv: list[str]) -> Assessment | None:
    """Commands that may be legitimate but need a human to confirm."""
    prog = program_name(argv[0])
    if prog == "git":
        return _git_rule(argv)
    reason = _generic_rule(prog, argv)
    return Assessment.ask(reason) if reason else None
