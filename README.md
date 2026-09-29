# pyagent

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
