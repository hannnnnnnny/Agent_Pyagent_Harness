"""The template written by ``pyagent init``."""

STARTER_CONFIG = """\
# pyagent configuration. Every key is optional; unknown keys are errors.

# Project-specific guidance appended to the system prompt.
instructions = ""

[model]
name = "claude-opus-5-5"
effort = "high"          # low | medium | high | xhigh | max

[safety]
# read-only | ask | auto-edit | unattended
mode = "ask"
# Extra glob patterns the agent may never read or write.
protect = []
# Patterns to exempt from the built-in secret rules (e.g. ".env.example").
unprotect = []
audit = true

[shell]
# Command prefixes that run without asking, e.g. ["pytest", "npm test"].
allow = []
# Programs that are always blocked.
block = []

[budget]
max_turns = 50
# max_cost_usd = 5.0

[network]
# Enables the web_fetch tool. Private, local, and metadata addresses are never reachable.
enabled = false
# Optional: only these domains (and their subdomains) may be fetched.
allow_domains = []
"""
