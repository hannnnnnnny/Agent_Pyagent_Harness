# Architecture

pyagent is a manual tool-use loop around the Anthropic Messages API, with every
tool call routed through one choke point where safety decisions are made.

## Package layout

| Module | Responsibility |
|---|---|
| `pyagent.agent` | The loop: call the model, run requested tools, repeat |
| `pyagent.factory` | `build_agent`: wires tools, gate, filters, audit into an `Agent` |
| `pyagent.providers` | `Provider` protocol; `AnthropicProvider`; `ScriptedProvider` for tests |
| `pyagent.messages` | Wire-shaped, append-only `Conversation`; `ModelResponse`, `ToolCall`, `ToolResult` |
| `pyagent.tools` | `Tool` base class, schema validation, registry, executor, built-in tools |
| `pyagent.safety` | Workspace sandbox, protected paths, command policy, approvals, redaction, audit |
| `pyagent.budget` | Turn / token / cost limits |
| `pyagent.config` | Strict `pyagent.toml` loader |
| `pyagent.sessions` | Save and resume conversations |
| `pyagent.cli` | The `pyagent` command |

The safety package never imports the agent loop, and only `safety.gate`
depends on the tool framework. A test imports every module in isolation so
import cycles cannot creep back in.

## One run, step by step

1. `Agent.run(task)` appends the task to the `Conversation` and emits `run_started`.
2. The `BudgetTracker` checks turn, token, and cost limits *before* each call.
3. The provider receives the system prompt, the full history, and the tool
   specs (sorted by name so the prompt prefix is stable and cacheable).
4. The assistant turn is appended **verbatim**, including thinking blocks.
   History is never edited, which keeps preserved thinking valid.
5. Depending on `stop_reason`:
   - `refusal`: the run ends with `refused`.
   - `pause_turn`: the loop continues from the appended turn.
   - `max_tokens` with tool calls: the calls may be truncated, so they are
     **not run**; each gets an error result asking the model to re-issue it.
   - no tool calls: the run ends (`completed` or `max_tokens`).
6. The `Dispatcher` runs the turn's tool calls: at most `max_calls_per_turn`
   are executed, an identical call repeated too many times in a row is refused,
   and when every call is read-only and needs no approval they run concurrently.
   Each call goes through the `ToolExecutor` (below), and all results for a
   turn are returned in a single user message, in the original order.
7. Five consecutive turns in which every call failed end the run as `stuck`.

## The tool execution pipeline

```text
ToolCall
  â”‚
  â”œâ”€ unknown tool? â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â–¶ error result
  â”œâ”€ validate input against the tool's JSON schema â–¶ error result on failure
  â”œâ”€ gates (SafetyGate)
  â”‚    strictest(mode Ã— risk, tool.assess(args))
  â”‚      BLOCK â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â–¶ error result (never approvable)
  â”‚      ASK   â”€â–¶ approver â”€ deny â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â–¶ error result (+ user's note)
  â”‚      ALLOW
  â”œâ”€ tool.run(args, ctx)
  â”‚    ToolError â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â–¶ error result (message shown)
  â”‚    unexpected exception â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â–¶ generic error (details logged locally)
  â”œâ”€ output filters: secret redaction, injection flagging
  â””â”€ middle truncation â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â–¶ ToolResult
```

Nothing a tool does can crash the loop: every failure becomes an `is_error`
result that the model can read and react to.

## Events

The loop and the gate emit structured events on an `EventBus`:
`run_started`, `turn_started`, `model_responded`, `tool_started`,
`tool_finished`, `approval_requested`, `approval_decided`, `action_blocked`,
`injection_suspected`, `run_finished`. The console renderer and the audit log
are both plain subscribers; a failing subscriber cannot break a run.

## Providers

`AnthropicProvider` streams every request (so large `max_tokens` values don't
hit HTTP timeouts), uses adaptive thinking with a configurable effort level,
enables prompt caching, turns on server-side refusal fallbacks, and maps SDK
errors to `ProviderError` with actionable messages. `ScriptedProvider` replays
canned turns and records requests, which is how the whole system is tested
without network access.
