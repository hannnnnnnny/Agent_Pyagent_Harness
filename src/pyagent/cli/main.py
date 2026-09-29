"""The ``pyagent`` command."""

from __future__ import annotations

import argparse
import dataclasses
import json
import sys
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any, TextIO

from pyagent import __version__
from pyagent.agent import Agent, RunResult
from pyagent.cli.render import ConsoleRenderer, format_result
from pyagent.cli.starter import STARTER_CONFIG
from pyagent.config import CONFIG_FILENAME, Config, load_config
from pyagent.errors import ConfigError, PyAgentError
from pyagent.factory import STATE_DIR, build_agent, options_from_config
from pyagent.providers.anthropic import EFFORT_LEVELS
from pyagent.providers.base import Provider
from pyagent.safety.approval import ConsoleApprover, deny_all
from pyagent.safety.audit import read_audit
from pyagent.safety.command_policy import CommandPolicy
from pyagent.safety.modes import ApprovalMode
from pyagent.safety.workspace import Workspace
from pyagent.usage import Usage

EXIT_OK = 0
EXIT_INCOMPLETE = 1
EXIT_USAGE = 2

ProviderFactory = Callable[[Config], Provider]


@dataclasses.dataclass
class IO:
    stdin: TextIO
    stdout: TextIO
    stderr: TextIO
    interactive: bool


def _add_run_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("-w", "--workspace", type=Path, default=Path.cwd(), help="workspace root")
    parser.add_argument("--mode", choices=[m.value for m in ApprovalMode], help="approval mode")
    parser.add_argument("--model", help="model id (default from config)")
    parser.add_argument("--effort", choices=EFFORT_LEVELS, help="reasoning effort")
    parser.add_argument("--max-turns", type=int, help="stop after this many model turns")
    parser.add_argument("--max-cost", type=float, help="stop after this many US dollars")
    parser.add_argument("--no-audit", action="store_true", help="do not write the audit log")
    parser.add_argument("-v", "--verbose", action="store_true", help="show more tool output")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pyagent", description="A safety-first Claude agent.")
    parser.add_argument("--version", action="version", version=f"pyagent {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run", help="run one task and exit")
    run.add_argument("task", help="what the agent should do")
    _add_run_options(run)
    chat = sub.add_parser("chat", help="interactive multi-turn session")
    _add_run_options(chat)
    policy = sub.add_parser("policy", help="show how a shell command would be treated")
    policy.add_argument("shell_command")
    policy.add_argument("-w", "--workspace", type=Path, default=Path.cwd())
    audit = sub.add_parser("audit", help="print recent audit log entries")
    audit.add_argument("-n", "--tail", type=int, default=20)
    audit.add_argument("-w", "--workspace", type=Path, default=Path.cwd())
    init = sub.add_parser("init", help="write a starter pyagent.toml")
    init.add_argument("-w", "--workspace", type=Path, default=Path.cwd())
    return parser


def apply_overrides(config: Config, args: argparse.Namespace) -> Config:
    """Command-line flags win over the config file."""
    changes: dict[str, Any] = {}
    for flag, field in (("model", "model"), ("effort", "effort"), ("max_turns", "max_turns")):
        if getattr(args, flag, None) is not None:
            changes[field] = getattr(args, flag)
    if getattr(args, "mode", None):
        changes["mode"] = ApprovalMode(args.mode)
    if getattr(args, "max_cost", None) is not None:
        changes["max_cost_usd"] = args.max_cost
    if getattr(args, "no_audit", False):
        changes["audit"] = False
    for key in ("max_turns", "max_cost_usd"):
        value = changes.get(key)
        if isinstance(value, (int, float)) and value <= 0:
            raise ConfigError(f"--{key.replace('_usd', '').replace('_', '-')} must be positive")
    return dataclasses.replace(config, **changes)


def default_provider(config: Config) -> Provider:
    from pyagent.providers.anthropic import AnthropicProvider  # noqa: PLC0415 - defer SDK import

    return AnthropicProvider(config.model, max_tokens=config.max_tokens, effort=config.effort)


def _make_agent(
    args: argparse.Namespace, config: Config, io: IO, provider_factory: ProviderFactory
) -> Agent:
    approver = ConsoleApprover(io.stdin, io.stdout) if io.interactive else deny_all
    options = options_from_config(config, approver)
    options.events.subscribe(ConsoleRenderer(io.stdout, verbose=args.verbose))
    return build_agent(args.workspace, provider_factory(config), options)


def _run_once(agent: Agent, task: str, io: IO) -> RunResult:
    try:
        result = agent.run(task)
    except KeyboardInterrupt:
        agent.cancel()
        result = RunResult("", "cancelled", 0, Usage(), detail="interrupted by user")
    io.stdout.write(format_result(result) + "\n")
    return result


def cmd_run(args: argparse.Namespace, config: Config, io: IO, factory: ProviderFactory) -> int:
    result = _run_once(_make_agent(args, config, io, factory), args.task, io)
    return EXIT_OK if result.ok else EXIT_INCOMPLETE


def cmd_chat(args: argparse.Namespace, config: Config, io: IO, factory: ProviderFactory) -> int:
    agent = _make_agent(args, config, io, factory)
    io.stdout.write("pyagent chat - type /exit to quit\n")
    while True:
        io.stdout.write("you> ")
        io.stdout.flush()
        line = io.stdin.readline()
        if not line or line.strip() in {"/exit", "/quit"}:
            return EXIT_OK
        if line.strip():
            _run_once(agent, line.strip(), io)


def cmd_policy(args: argparse.Namespace, config: Config, io: IO) -> int:
    policy = CommandPolicy(
        allow_prefixes=config.shell_allow, blocked_programs=frozenset(config.shell_block)
    )
    assessment = policy.assess(args.shell_command, Workspace(args.workspace))
    reason = f": {assessment.reason}" if assessment.reason else ""
    io.stdout.write(f"{assessment.verdict.name}{reason}\n")
    return EXIT_OK


def cmd_audit(args: argparse.Namespace, io: IO) -> int:
    records = read_audit(args.workspace / STATE_DIR / "audit.jsonl")
    if not records:
        io.stdout.write("no audit records yet\n")
    for record in records[-args.tail :] if args.tail > 0 else []:
        data = json.dumps(record.get("data", {}), ensure_ascii=False)
        io.stdout.write(f"{record.get('ts', '')} {record.get('kind', '')} {data[:200]}\n")
    return EXIT_OK


def cmd_init(args: argparse.Namespace, io: IO) -> int:
    path = args.workspace / CONFIG_FILENAME
    if path.exists():
        io.stderr.write(f"{path} already exists; not overwriting\n")
        return EXIT_USAGE
    path.write_text(STARTER_CONFIG, encoding="utf-8")
    io.stdout.write(f"wrote {path}\n")
    return EXIT_OK


def _dispatch(args: argparse.Namespace, io: IO, factory: ProviderFactory) -> int:
    if args.command == "init":
        return cmd_init(args, io)
    if args.command == "audit":
        return cmd_audit(args, io)
    config = apply_overrides(load_config(args.workspace), args)
    if args.command == "policy":
        return cmd_policy(args, config, io)
    if args.command == "chat":
        return cmd_chat(args, config, io, factory)
    return cmd_run(args, config, io, factory)


def main(
    argv: Sequence[str] | None = None,
    *,
    io: IO | None = None,
    provider_factory: ProviderFactory = default_provider,
) -> int:
    io = io or IO(sys.stdin, sys.stdout, sys.stderr, interactive=sys.stdin.isatty())
    args = build_parser().parse_args(argv)
    args.workspace = args.workspace.resolve()
    if not args.workspace.is_dir():
        io.stderr.write(f"pyagent: workspace {args.workspace} is not a directory\n")
        return EXIT_USAGE
    try:
        return _dispatch(args, io, provider_factory)
    except (ConfigError, PyAgentError) as exc:
        io.stderr.write(f"pyagent: {exc}\n")
        return EXIT_USAGE


if __name__ == "__main__":
    raise SystemExit(main())
