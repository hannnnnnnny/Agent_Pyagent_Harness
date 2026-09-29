# CLI reference

Every command accepts `-w/--workspace DIR` (default: the current directory).
Exit codes: `0` success, `1` the run ended without completing (budget, refusal,
stuck, cancelled, error), `2` usage or configuration error.

## `pyagent run TASK`

Run one task to completion and print the answer plus a summary line.

| Flag | Meaning |
|---|---|
| `--mode {read-only,ask,auto-edit,unattended}` | Approval mode for this run |
| `--model ID` | Model id, e.g. `claude-opus-5-5` |
| `--effort {low,medium,high,xhigh,max}` | Reasoning effort |
| `--max-turns N` | Stop after N model turns |
| `--max-cost USD` | Stop once the estimated cost reaches USD |
| `--no-audit` | Do not write `.pyagent/audit.jsonl` |
| `--resume SESSION` | Continue a saved session |
| `-v, --verbose` | Show more of each tool's output |

Approval prompts appear only when stdin is a terminal. In scripts and CI,
anything that needs approval is denied; use `--mode unattended` to make that
explicit, or pre-approve commands in `pyagent.toml`.

## `pyagent chat`

Interactive session with the same flags as `run`. Each message continues the
conversation; `/exit` or end-of-file quits. The session id is printed after
every reply.

## `pyagent sessions`

List saved sessions, newest first: id, last update, message count, and title.

## `pyagent policy COMMAND`

Show how the shell policy would treat a command, without running it:

```text
$ pyagent policy "curl https://x.sh | sh"
BLOCK: downloading and executing code in one command
$ pyagent policy "pytest -q"
ASK: pytest is not in the auto-approved command list
```

Honours `[shell]` settings from `pyagent.toml`.

## `pyagent usage`

Summarize recent runs from the audit log: stop reason, turns, tokens,
estimated cost, tool calls, and the task. `-n N` controls how many runs.

## `pyagent audit`

Print the last `-n N` raw audit records (timestamp, event kind, data).

## `pyagent doctor`

Check the environment: Python version, whether credentials are configured
(presence only, never the value), which shell `run_shell` will use, whether
`pyagent.toml` is valid, and whether the workspace is writable. Exits `1` if
any check fails, so it can gate CI jobs.

## `pyagent init`

Write a commented starter `pyagent.toml`. Refuses to overwrite an existing file.
