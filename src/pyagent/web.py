"""Fetching web pages with SSRF protections.

Each hop (the first request and every redirect) is parsed, checked against the
optional domain allowlist, resolved, and address-checked. The TCP connection
is then made to that exact vetted address, so a DNS answer that changes
between the check and the connect (DNS rebinding) cannot redirect it.
"""

from __future__ import annotations

import http.client
import socket
import ssl
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from urllib.parse import urljoin

from pyagent.errors import PolicyViolation, ToolError
from pyagent.htmltext import html_to_text
from pyagent.safety.net import Resolver, Target, is_public_address, parse_target, resolve_public
from pyagent.safety.net import system_resolver as default_resolver

REDIRECT_STATUSES = frozenset({301, 302, 303, 307, 308})
TEXT_TYPES = ("text/", "application/json", "application/xml", "application/xhtml+xml")
USER_AGENT = "pyagent (+https://github.com/hannnnnnnny/Agent_Pyagent_Harness)"


class _PinnedHTTPConnection(http.client.HTTPConnection):
    def __init__(self, target: Target, address: str, timeout: float) -> None:
        super().__init__(target.host, target.port, timeout=timeout)
        self._address = address

    def connect(self) -> None:
        self.sock = socket.create_connection((self._address, self.port), self.timeout)


class _PinnedHTTPSConnection(http.client.HTTPSConnection):
    def __init__(
        self, target: Target, address: str, timeout: float, context: ssl.SSLContext
    ) -> None:
        super().__init__(target.host, target.port, timeout=timeout, context=context)
        self._address = address
        self._tls = context

    def connect(self) -> None:
        # Certificate verification still uses the hostname, not the pinned IP.
        sock = socket.create_connection((self._address, self.port), self.timeout)
        self.sock = self._tls.wrap_socket(sock, server_hostname=self.host)


def domain_allowed(host: str, allowed: Iterable[str]) -> bool:
    """``docs.python.org`` matches an allowlist entry of ``python.org``."""
    return any(host == d or host.endswith("." + d) for d in (a.lower().strip(".") for a in allowed))


@dataclass(frozen=True)
class FetchResult:
    url: str
    status: int
    content_type: str
    text: str
    truncated: bool = False


@dataclass
class Fetcher:
    allowed_domains: tuple[str, ...] = ()
    max_bytes: int = 1_000_000
    timeout: float = 15.0
    max_redirects: int = 5
    resolver: Resolver = field(default=default_resolver)
    address_allowed: Callable[[str], bool] = field(default=is_public_address)
    tls_context: ssl.SSLContext = field(default_factory=ssl.create_default_context)

    def fetch(self, url: str) -> FetchResult:
        for _ in range(self.max_redirects + 1):
            target = self.check_url(url)
            response, conn = self._request(target)
            try:
                location = response.getheader("Location")
                if response.status in REDIRECT_STATUSES and location:
                    url = urljoin(url, location)
                    continue
                return self._read(url, response)
            finally:
                conn.close()
        raise ToolError(f"stopped after {self.max_redirects} redirects")

    def check_url(self, url: str) -> Target:
        """Validate a URL and the domain allowlist without any network access."""
        target = parse_target(url)
        if self.allowed_domains and not domain_allowed(target.host, self.allowed_domains):
            raise PolicyViolation(f"{target.host} is not in the allowed domain list")
        return target

    def _request(
        self, target: Target
    ) -> tuple[http.client.HTTPResponse, http.client.HTTPConnection]:
        address = resolve_public(target, self.resolver, self.address_allowed)
        conn: http.client.HTTPConnection
        if target.scheme == "https":
            conn = _PinnedHTTPSConnection(target, address, self.timeout, self.tls_context)
        else:
            conn = _PinnedHTTPConnection(target, address, self.timeout)
        headers = {
            "Host": target.netloc,
            "User-Agent": USER_AGENT,
            "Accept": "text/html, text/plain, application/json;q=0.9, */*;q=0.1",
            "Accept-Encoding": "identity",
        }
        try:
            conn.request("GET", target.path, headers=headers)
            return conn.getresponse(), conn
        except (OSError, http.client.HTTPException) as exc:
            conn.close()
            raise ToolError(f"request to {target.host} failed: {exc}") from exc

    def _read(self, url: str, response: http.client.HTTPResponse) -> FetchResult:
        content_type = response.getheader("Content-Type", "") or ""
        media_type = content_type.split(";", 1)[0].strip().lower()
        if media_type and not media_type.startswith(TEXT_TYPES):
            raise ToolError(f"unsupported content type {media_type!r}; only text is fetched")
        raw = response.read(self.max_bytes + 1)
        truncated = len(raw) > self.max_bytes
        text = raw[: self.max_bytes].decode(_charset(content_type), errors="replace")
        if media_type in {"text/html", "application/xhtml+xml"}:
            text = html_to_text(text)
        return FetchResult(url, response.status, media_type, text, truncated)


def _charset(content_type: str) -> str:
    for part in content_type.split(";")[1:]:
        key, _, value = part.strip().partition("=")
        if key.lower() == "charset" and value:
            charset = value.strip("\"' ")
            try:
                "".encode(charset)
            except LookupError:
                break
            return charset
    return "utf-8"
