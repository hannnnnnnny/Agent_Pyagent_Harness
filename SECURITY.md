# Security Policy

pyagent executes model-chosen actions on your machine, so its safety layer is
part of the product, not an add-on.

## Reporting a vulnerability

Please report sandbox escapes, policy bypasses, or secret leaks privately via
GitHub Security Advisories on this repository rather than a public issue.

## Scope

- Escaping the workspace root through paths, symlinks, or shell commands
- Running a command the configured policy should have blocked
- Secrets from the environment or files reaching the model or logs unredacted
