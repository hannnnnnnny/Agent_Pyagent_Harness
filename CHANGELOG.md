# Changelog

All notable changes to pyagent are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.1.0]

First release: a safety-first agent harness for Claude.

### Agent
- Manual tool-use loop over the Anthropic Messages API with adaptive thinking,
  configurable effort, streaming, prompt caching, and server-side refusal fallbacks.
- Append-only conversation history that preserves thinking blocks verbatim.
- Handling for every stop reason, including not running tool calls truncated by
  `max_tokens`.
- Turn, token, and cost budgets; a `stuck` guard; cancellation.
- Per-turn tool call limit, identical-call loop guard, and concurrent execution
  of read-only, approval-free calls.
- Sessions that can be saved and resumed.

### Tools
- `read_file`, `list_dir`, `glob`, `grep`, `write_file`, `edit_file`,
  `multi_edit`, `todo`, `run_shell`, and the opt-in `web_fetch`.
- Every input validated against its JSON schema; every failure returned to the
  model as an error result rather than crashing the loop.
- Edits report unified diffs and respect CRLF line endings.

### Safety
- Workspace sandbox with symlink-aware containment and Windows path hardening.
- Protected paths for credentials, `.git/`, and pyagent's own state.
- Shell command policy (allow / ask / block) with wrapper unwrapping, glob and
  variable handling, and paths hidden in flags and `@file` references.
- Approval modes (`read-only`, `ask`, `auto-edit`, `unattended`) with a safety
  gate that never lets a block be approved.
- Allowlisted subprocess environments, secret redaction, prompt-injection
  flagging, and a redacted JSONL audit log.
- SSRF-protected `web_fetch`: public addresses only, pinned connections,
  per-hop redirect checks, and rejection of ambiguous numeric hosts.
- An adversarial test suite of known escape and bypass attempts.

### Tooling
- `pyagent` CLI: `run`, `chat`, `policy`, `audit`, `usage`, `sessions`, `init`.
- Strict `pyagent.toml` configuration.
- CI on Linux, macOS, and Windows for Python 3.10 to 3.14, a 95% coverage floor,
  CodeQL, and Dependabot.

[Unreleased]: https://github.com/hannnnnnnny/Agent_Pyagent_Harness/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/hannnnnnnny/Agent_Pyagent_Harness/releases/tag/v0.1.0
