# Security Policy

pyagent executes model-chosen actions on your machine, so its safety layer is
part of the product, not an add-on.

## Reporting a vulnerability

Please report sandbox escapes, policy bypasses, or secret leaks privately via
GitHub Security Advisories on this repository rather than a public issue.

## Supported versions

Security fixes are made on `main` and released in the next version. Only the
latest release is supported.

## Scope

- Escaping the workspace root through paths, symlinks, or shell commands
- Running a command the configured policy should have blocked
- Secrets from the environment or files reaching the model or logs unredacted
- `web_fetch` reaching loopback, private, link-local, or metadata addresses
- Getting an action approved or run that should have been blocked, or tampering
  with the audit log or `.git/`

The shell policy is documented as defence in depth rather than a sandbox (see
[docs/security-model.md](docs/security-model.md)). Reports of new bypasses are
still welcome; please include the exact command and the verdict it received
from `pyagent policy`.

## Handling

Reports are acknowledged within a week. Each confirmed issue gets a failing
test in `tests/adversarial/` before the fix, so it cannot regress.
