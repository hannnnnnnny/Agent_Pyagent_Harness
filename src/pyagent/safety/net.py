"""URL and address checks that keep network tools away from internal systems.

The main risk of letting a model fetch URLs is server-side request forgery:
reaching localhost services, the LAN, or cloud metadata endpoints such as
169.254.169.254. Every URL is checked, every redirect hop is re-checked, and
connections are pinned to the address that passed the check.
"""

from __future__ import annotations

import ipaddress
import socket
from collections.abc import Callable
from dataclasses import dataclass
from urllib.parse import urlsplit

from pyagent.errors import PolicyViolation

ALLOWED_SCHEMES = frozenset({"http", "https"})
DEFAULT_PORTS = {"http": 80, "https": 443}

# host, port -> candidate IP address strings
Resolver = Callable[[str, int], list[str]]


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


def is_public_address(address: str) -> bool:
    """True only for globally routable unicast addresses.

    IPv4-mapped IPv6 addresses (``::ffff:127.0.0.1``) are unwrapped first so
    they cannot smuggle a private IPv4 address past the check.
    """
    try:
        ip = ipaddress.ip_address(address.split("%", 1)[0])
    except ValueError:
        return False
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
        ip = ip.ipv4_mapped
    return ip.is_global and not ip.is_multicast


def system_resolver(host: str, port: int) -> list[str]:
    infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    return [str(info[4][0]) for info in infos]


def resolve_public(
    target: Target, resolver: Resolver = system_resolver, allow_private: bool = False
) -> str:
    """Resolve ``target`` and return an address safe to connect to.

    Every resolved address must be public: a hostname that resolves to both a
    public and a private address is rejected rather than trusting either.
    """
    try:
        addresses = resolver(target.host, target.port)
    except OSError as exc:
        raise PolicyViolation(f"could not resolve {target.host}: {exc}") from exc
    if not addresses:
        raise PolicyViolation(f"{target.host} did not resolve to any address")
    if not allow_private:
        blocked = [a for a in addresses if not is_public_address(a)]
        if blocked:
            raise PolicyViolation(
                f"{target.host} resolves to a non-public address ({blocked[0]}); "
                "local, private, and metadata addresses are not reachable"
            )
    return addresses[0]
