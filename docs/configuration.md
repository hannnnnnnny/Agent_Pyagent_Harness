# Configuration

pyagent reads `pyagent.toml` from the workspace root. Every key is optional.
Unknown keys and wrong types are **errors**, so a typo in a safety setting is
reported instead of silently falling back to a default. Run `pyagent init` to
write a commented starter file.

Command-line flags override the file: `--mode`, `--model`, `--effort`,
`--max-turns`, `--max-cost`, `--no-audit`.

## Top level

| Key | Type | Default | Meaning |
|---|---|---|---|
| `instructions` | string | `""` | Extra guidance appended to the system prompt |
| `instructions_file` | string | `""` | Workspace file (e.g. `AGENTS.md`) whose contents are appended after `instructions` |

`instructions_file` is read through the workspace sandbox: it must be inside the
workspace, cannot be a protected file, and is capped at 32 KiB.

## `[model]`

| Key | Type | Default | Meaning |
|---|---|---|---|
| `name` | string | `claude-opus-5-5` | Model id |
| `effort` | string | `high` | `low`, `medium`, `high`, `xhigh`, or `max` |
| `max_tokens` | integer | `64000` | Output cap per model turn |

## `[safety]`

| Key | Type | Default | Meaning |
|---|---|---|---|
| `mode` | string | `ask` | `read-only`, `ask`, `auto-edit`, or `unattended` |
| `protect` | list of globs | `[]` | Extra paths the agent may never read or write |
| `unprotect` | list of globs | `[]` | Exempt paths from the built-in secret rules |
| `audit` | boolean | `true` | Write `.pyagent/audit.jsonl` |

Glob rules match workspace-relative paths case-insensitively. A pattern ending
in `/**` matches a directory at any depth; a pattern without `/` matches file
names anywhere. `unprotect` cannot cover `.pyagent/` or `.git/`.

## `[shell]`

| Key | Type | Default | Meaning |
|---|---|---|---|
| `allow` | list of strings | `[]` | Command prefixes that run without asking |
| `block` | list of strings | `[]` | Program names that are always blocked |

A command is auto-allowed only if **every** segment of the command line
matches. Block and ask rules are checked first, so `allow = ["git"]` still asks
before `git push`. Pre-approving an interpreter such as `python` effectively
approves arbitrary code; prefer specific commands like `python -m pytest`.

Use `pyagent policy "<command>"` to see how a command would be treated.

## `[budget]`

| Key | Type | Default | Meaning |
|---|---|---|---|
| `max_turns` | integer | `50` | Model turns per run |
| `max_total_tokens` | integer | unlimited | Tokens per run (input, output, and cache) |
| `max_cost_usd` | number | unlimited | Estimated USD per run (known models only) |

## `[limits]`

| Key | Type | Default | Meaning |
|---|---|---|---|
| `max_calls_per_turn` | integer | `25` | Tool calls run per model turn; extra calls get an error result |
| `max_identical_calls` | integer | `3` | The same call this many times in a row is refused as a loop |
| `parallel_reads` | boolean | `true` | Run a turn's read-only, approval-free calls concurrently |
| `max_tool_output_chars` | integer | `50000` | Longest tool result sent to the model; the middle of longer output is elided |

## `[network]`

| Key | Type | Default | Meaning |
|---|---|---|---|
| `enabled` | boolean | `false` | Register the `web_fetch` tool |
| `allow_domains` | list of strings | `[]` | If set, only these domains and their subdomains can be fetched |

Even when enabled, requests to private, loopback, link-local, and cloud
metadata addresses are refused, every redirect is re-checked, and `web_fetch`
is a network-risk tool, so it asks for approval in `ask` and `auto-edit` modes.

## Example

```toml
instructions = "Run `python -m pytest -q` before you finish."

[model]
effort = "xhigh"

[safety]
mode = "auto-edit"
protect = ["customer-data/**"]
unprotect = [".env.example"]

[shell]
allow = ["python -m pytest", "ruff check", "ruff format"]
block = ["docker"]

[budget]
max_turns = 40
max_cost_usd = 5.0

[network]
enabled = true
allow_domains = ["docs.python.org", "pypi.org"]
```
