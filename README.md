# pyagent

[![CI](https://github.com/hannnnnnnny/Agent_Pyagent_Harness/actions/workflows/ci.yml/badge.svg)](https://github.com/hannnnnnnny/Agent_Pyagent_Harness/actions/workflows/ci.yml)
[![CodeQL](https://github.com/hannnnnnnny/Agent_Pyagent_Harness/actions/workflows/codeql.yml/badge.svg)](https://github.com/hannnnnnnny/Agent_Pyagent_Harness/actions/workflows/codeql.yml)

A powerful, safety-first agent harness for Claude, written in Python.

pyagent gives Claude real tools (files, search, and a shell) inside a single
workspace directory, and puts a layered safety system between the model and
your machine: a path sandbox, a shell command policy, approval modes, secret
redaction, prompt-injection flagging, budgets, and an audit log.

```text
you ──task──▶ Agent loop ──request──▶ Claude
                 ▲   │
        results  │   ▼ tool calls
                 │  ToolExecutor ──▶ validate ─▶ SafetyGate ─▶ tool ─▶ redact / flag ─▶ result
                 │                                   │
                 └──────── events ──▶ audit log, console
```

## Install

```bash
pip install -e ".[dev]"
```

Python 3.10 or newer. Credentials come from `ANTHROPIC_API_KEY` or an
`ant auth login` profile; pyagent never stores keys.

## Quick start

```bash
pyagent init                                   # optional: write pyagent.toml
pyagent run "add type hints to utils.py and run the tests"
pyagent chat                                   # multi-turn session
pyagent run "continue" --resume 3f2a9c1b7d4e   # pick a session back up
pyagent usage                                  # tokens and cost of recent runs
pyagent policy "rm -rf build"                  # how would this command be treated?
```

When the agent wants to do something risky it asks first:

```text
> write_file {"path": "utils.py", "content": "..."}
[approval needed] write_file: utils.py
  reason: write actions require approval in ask mode
  allow? [y]es once / [a]lways this session / [N]o (optionally: n <why>):
```

## Approval modes

| Mode | Reads | File edits | Shell commands | Network |
|---|---|---|---|---|
| `read-only` | yes | blocked | blocked | blocked |
| `ask` *(default)* | yes | ask | ask | ask |
| `auto-edit` | yes | yes | per command policy | ask |
| `unattended` | yes | yes | per command policy | per policy |

In `unattended` mode nobody is there to answer, so anything that would need
approval is **denied**. Actions the policy blocks (for example `sudo`, `curl … | sh`,
or reading `.env`) can never be approved in any mode.

## Built-in tools

| Tool | Risk | What it does |
|---|---|---|
| `read_file` | read | Line-numbered file view with paging |
| `list_dir` | read | Directory listing (protected entries hidden) |
| `glob` | read | Find files by pattern, e.g. `**/*.py` |
| `grep` | read | Regex or literal search across files |
| `todo` | read | The agent's own task list for multi-step work |
| `write_file` | write | Create or replace a file (atomic, size-limited) |
| `edit_file` | write | Exact, unique string replacement |
| `multi_edit` | write | Several replacements in one file, all or nothing |
| `run_shell` | execute | Policy-checked shell command with a scrubbed environment |
| `web_fetch` | network | Opt-in: fetch a public URL as text (SSRF-protected) |

## Using pyagent from Python

```python
from pyagent import AgentOptions, ApprovalMode, Budget, build_agent
from pyagent.providers.anthropic import AnthropicProvider
from pyagent.safety import ConsoleApprover
import sys

agent = build_agent(
    "path/to/project",
    AnthropicProvider(effort="high"),
    AgentOptions(
        mode=ApprovalMode.AUTO_EDIT,
        approver=ConsoleApprover(sys.stdin, sys.stdout),
        budget=Budget(max_turns=30, max_cost_usd=2.0),
    ),
)
result = agent.run("Fix the failing test in tests/test_parser.py")
print(result.stop, result.text)
```

`result.stop` is one of `completed`, `refused`, `max_tokens`, `budget`,
`stuck`, `cancelled`, or `error`. See [`examples/`](examples/) for custom tools,
project-specific policy gates (`AgentOptions(extra_gates=[...])`), and an
offline demo.

## Documentation

- [Architecture](docs/architecture.md): how a run flows through the system
- [Security model](docs/security-model.md): what is protected, how, and the known limits
- [Configuration](docs/configuration.md): every `pyagent.toml` setting
- [CLI reference](docs/cli.md): every command and flag
- [Changelog](CHANGELOG.md)
- [Contributing](CONTRIBUTING.md) and [Security policy](SECURITY.md)

## License

MIT, see [LICENSE](LICENSE).
