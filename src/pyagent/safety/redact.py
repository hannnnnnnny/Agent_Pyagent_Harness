"""Redaction of secrets from text before it reaches the model or the logs."""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field

from pyagent.safety.env import SECRET_NAME

PLACEHOLDER = "[REDACTED]"

# Well-known credential formats. A pattern either matches only the secret, or
# marks it with a named group "secret", so surrounding text stays readable.
DEFAULT_PATTERNS: dict[str, re.Pattern[str]] = {
    "anthropic_key": re.compile(r"sk-ant-[A-Za-z0-9_\-]{20,}"),
    "openai_key": re.compile(r"sk-(?:proj-)?[A-Za-z0-9]{32,}"),
    "aws_access_key": re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"),
    "github_token": re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{40,})\b"),
    "slack_token": re.compile(r"\bxox[abprs]-[A-Za-z0-9\-]{10,}\b"),
    "google_api_key": re.compile(r"\bAIza[0-9A-Za-z_\-]{35}\b"),
    "stripe_key": re.compile(r"\b[rs]k_(?:live|test)_[A-Za-z0-9]{20,}\b"),
    "jwt": re.compile(r"\beyJ[A-Za-z0-9_\-]{8,}\.eyJ[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,}"),
    "private_key": re.compile(
        r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.DOTALL
    ),
    "bearer": re.compile(r"(?i)(?<=bearer )[A-Za-z0-9_\-.=]{16,}"),
    "url_credentials": re.compile(r"(?<=://)[^/\s:@]+:[^/\s@]+(?=@)"),
    "assignment": re.compile(
        r"(?i)(?:password|passwd|secret|token|api_key|apikey)[\"']?\s*[:=]\s*[\"']?"
        r"(?P<secret>[^\s\"',;]{6,})"
    ),
}

MIN_KNOWN_SECRET_LENGTH = 8


@dataclass
class Redactor:
    """Replaces known secret values and secret-shaped strings with a placeholder."""

    patterns: dict[str, re.Pattern[str]] = field(default_factory=lambda: dict(DEFAULT_PATTERNS))
    known_secrets: set[str] = field(default_factory=set)

    @classmethod
    def from_environment(cls, environ: Mapping[str, str]) -> Redactor:
        """Treat the values of secret-looking environment variables as known secrets."""
        return cls(known_secrets=secrets_from_env(environ))

    def add_secrets(self, values: Iterable[str]) -> None:
        self.known_secrets.update(v for v in values if len(v) >= MIN_KNOWN_SECRET_LENGTH)

    def redact(self, text: str) -> str:
        # Longest first so a secret containing another secret is fully removed.
        for secret in sorted(self.known_secrets, key=len, reverse=True):
            text = text.replace(secret, PLACEHOLDER)
        for pattern in self.patterns.values():
            text = pattern.sub(_replace_secret, text)
        return text


def _replace_secret(match: re.Match[str]) -> str:
    if "secret" not in match.re.groupindex:
        return PLACEHOLDER
    start, end = match.span("secret")
    offset = match.start()
    whole = match.group(0)
    return whole[: start - offset] + PLACEHOLDER + whole[end - offset :]


def secrets_from_env(environ: Mapping[str, str]) -> set[str]:
    return {
        value
        for name, value in environ.items()
        if SECRET_NAME.search(name) and len(value) >= MIN_KNOWN_SECRET_LENGTH
    }
