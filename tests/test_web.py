"""Fetcher tests against a local server, with a test-only address policy."""

from __future__ import annotations

import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from pyagent.errors import PolicyViolation, ToolError
from pyagent.web import Fetcher, domain_allowed

PAGES: dict[str, tuple[int, dict[str, str], bytes]] = {
    "/page": (200, {"Content-Type": "text/html; charset=utf-8"}, b"<title>T</title><p>Hello</p>"),
    "/plain": (200, {"Content-Type": "text/plain; charset=latin-1"}, "caf\xe9".encode("latin-1")),
    "/json": (200, {"Content-Type": "application/json"}, b'{"ok": true}'),
    "/image": (200, {"Content-Type": "image/png"}, b"\x89PNG"),
    "/big": (200, {"Content-Type": "text/plain"}, b"x" * 5000),
    "/to-page": (302, {"Location": "/page"}, b""),
    "/to-evil": (302, {"Location": "http://evil.test/page"}, b""),
    "/loop": (302, {"Location": "/loop"}, b""),
}


class Handler(BaseHTTPRequestHandler):
    seen_hosts: list[str] = []

    def do_GET(self) -> None:
        Handler.seen_hosts.append(self.headers.get("Host", ""))
        status, headers, body = PAGES.get(self.path, (404, {}, b""))
        self.send_response(status)
        for key, value in headers.items():
            self.send_header(key, value)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args: object) -> None:
        return


@pytest.fixture(scope="module")
def server() -> Iterator[int]:
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield httpd.server_address[1]
    httpd.shutdown()


@pytest.fixture
def fetcher(server: int) -> Fetcher:
    names = {"good.test": "127.0.0.1", "evil.test": "10.0.0.1"}

    def resolver(host: str, port: int) -> list[str]:
        return [names[host]] if host in names else []

    return Fetcher(
        resolver=resolver,
        address_allowed=lambda address: address == "127.0.0.1",
        max_bytes=1000,
    )


def url(port: int, path: str, host: str = "good.test") -> str:
    return f"http://{host}:{port}{path}"


def test_html_is_converted_to_text(fetcher: Fetcher, server: int) -> None:
    result = fetcher.fetch(url(server, "/page"))
    assert result.status == 200
    assert result.content_type == "text/html"
    assert result.text == "# T\n\nHello"


def test_connection_is_pinned_but_host_header_is_kept(fetcher: Fetcher, server: int) -> None:
    fetcher.fetch(url(server, "/json"))
    assert Handler.seen_hosts[-1] == f"good.test:{server}"


def test_charset_is_respected(fetcher: Fetcher, server: int) -> None:
    assert fetcher.fetch(url(server, "/plain")).text == "caf\xe9"


def test_redirects_are_followed(fetcher: Fetcher, server: int) -> None:
    result = fetcher.fetch(url(server, "/to-page"))
    assert result.url.endswith("/page")
    assert "Hello" in result.text


def test_redirect_to_private_address_is_blocked(fetcher: Fetcher, server: int) -> None:
    with pytest.raises(PolicyViolation, match="non-public address"):
        fetcher.fetch(url(server, "/to-evil"))


def test_redirect_loops_stop(fetcher: Fetcher, server: int) -> None:
    with pytest.raises(ToolError, match="redirects"):
        fetcher.fetch(url(server, "/loop"))


def test_binary_content_is_refused(fetcher: Fetcher, server: int) -> None:
    with pytest.raises(ToolError, match="unsupported content type"):
        fetcher.fetch(url(server, "/image"))


def test_large_bodies_are_truncated(fetcher: Fetcher, server: int) -> None:
    result = fetcher.fetch(url(server, "/big"))
    assert result.truncated
    assert len(result.text) == 1000


def test_domain_allowlist(fetcher: Fetcher, server: int) -> None:
    fetcher.allowed_domains = ("example.org",)
    with pytest.raises(PolicyViolation, match="allowed domain list"):
        fetcher.fetch(url(server, "/page"))


def test_default_policy_blocks_loopback(server: int) -> None:
    with pytest.raises(PolicyViolation, match="non-public"):
        Fetcher().fetch(f"http://127.0.0.1:{server}/page")


def test_connection_errors_are_tool_errors() -> None:
    fetcher = Fetcher(resolver=lambda h, p: ["127.0.0.1"], address_allowed=lambda a: True)
    with pytest.raises(ToolError, match="failed"):
        fetcher.fetch("http://closed.test:1/")


@pytest.mark.parametrize(
    ("host", "allowed", "expected"),
    [
        ("python.org", ["python.org"], True),
        ("docs.python.org", ["python.org"], True),
        ("evilpython.org", ["python.org"], False),
        ("python.org.evil.com", ["python.org"], False),
        ("example.com", [".Example.com"], True),
    ],
)
def test_domain_allowed(host: str, allowed: list[str], expected: bool) -> None:
    assert domain_allowed(host, allowed) is expected
