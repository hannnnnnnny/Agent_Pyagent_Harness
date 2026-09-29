"""URL and address checks that keep network tools away from internal systems.

The main risk of letting a model fetch URLs is server-side request forgery:
reaching localhost services, the LAN, or cloud metadata endpoints such as
169.254.169.254. Every URL is checked, every redirect hop is re-checked, and
connections are pinned to the address that passed the check.
"""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlsplit

from pyagent.errors import PolicyViolation

ALLOWED_SCHEMES = frozenset({"http", "https"})
DEFAULT_PORTS = {"http": 80, "https": 443}


@dataclass(frozen=True)
class Target:
    scheme: str
    host: str
    port: int
    path: str

    @property
    def netloc(self) -> str:
        default = DEFAULT_PORTS[self.scheme]
        return self.host if self.port == default else f"{self.host}:{self.port}"


def parse_target(url: str) -> Target:
    """Validate the shape of ``url`` without touching the network."""
    try:
        parts = urlsplit(url.strip())
        port = parts.port
    except ValueError as exc:
        raise PolicyViolation(f"malformed URL: {exc}") from exc
    scheme = parts.scheme.lower()
    if scheme not in ALLOWED_SCHEMES:
        raise PolicyViolation(f"only http and https URLs are allowed, not {scheme or 'none'!r}")
    if parts.username or parts.password:
        raise PolicyViolation("URLs with embedded credentials are not allowed")
    host = (parts.hostname or "").rstrip(".").lower()
    if not host:
        raise PolicyViolation("URL has no host")
    path = parts.path or "/"
    if parts.query:
        path += "?" + parts.query
    return Target(scheme, host, port or DEFAULT_PORTS[scheme], path)
