from collections.abc import Callable

import pytest

from pyagent.errors import PolicyViolation
from pyagent.safety.net import Target, is_public_address, parse_target, resolve_public


@pytest.mark.parametrize(
    ("url", "target"),
    [
        ("https://Example.com", Target("https", "example.com", 443, "/")),
        ("http://example.com:8080/a/b?x=1", Target("http", "example.com", 8080, "/a/b?x=1")),
        ("https://example.com./docs", Target("https", "example.com", 443, "/docs")),
        ("https://[2001:db8::1]/", Target("https", "2001:db8::1", 443, "/")),
    ],
)
def test_valid_urls(url: str, target: Target) -> None:
    assert parse_target(url) == target


def test_fragment_is_dropped() -> None:
    assert parse_target("https://example.com/page#section").path == "/page"


def test_netloc_omits_default_port() -> None:
    assert parse_target("https://example.com").netloc == "example.com"
    assert parse_target("http://example.com:81").netloc == "example.com:81"


@pytest.mark.parametrize(
    ("url", "reason"),
    [
        ("file:///etc/passwd", "only http and https"),
        ("ftp://example.com", "only http and https"),
        ("gopher://127.0.0.1:6379/_", "only http and https"),
        ("example.com/path", "only http and https"),
        ("https://user:pass@example.com", "embedded credentials"),
        ("https://token@example.com", "embedded credentials"),
        ("https:///path", "no host"),
        ("http://example.com:99999", "malformed"),
    ],
)
def test_rejected_urls(url: str, reason: str) -> None:
    with pytest.raises(PolicyViolation, match=reason):
        parse_target(url)


@pytest.mark.parametrize(
    "address",
    ["93.184.216.34", "8.8.8.8", "2606:4700:4700::1111"],
)
def test_public_addresses(address: str) -> None:
    assert is_public_address(address)


@pytest.mark.parametrize(
    "address",
    [
        "127.0.0.1",
        "10.1.2.3",
        "172.16.0.1",
        "192.168.1.1",
        "169.254.169.254",
        "100.64.0.1",
        "0.0.0.0",  # noqa: S104 - an address under test, not a bind
        "224.0.0.1",
        "255.255.255.255",
        "::1",
        "fe80::1%eth0",
        "fc00::1",
        "::ffff:127.0.0.1",
        "::ffff:169.254.169.254",
        "not-an-ip",
    ],
)
def test_non_public_addresses(address: str) -> None:
    assert not is_public_address(address)


def _resolver(*addresses: str) -> Callable[[str, int], list[str]]:
    return lambda host, port: list(addresses)


def test_resolve_public_returns_first_address() -> None:
    target = parse_target("https://example.com")
    assert resolve_public(target, _resolver("93.184.216.34", "93.184.216.35")) == "93.184.216.34"


@pytest.mark.parametrize(
    "addresses",
    [("127.0.0.1",), ("93.184.216.34", "10.0.0.5"), ("169.254.169.254",)],
)
def test_resolve_public_rejects_any_private_answer(addresses: tuple[str, ...]) -> None:
    with pytest.raises(PolicyViolation, match="non-public address"):
        resolve_public(parse_target("http://rebind.example"), _resolver(*addresses))


def test_resolve_public_can_allow_private_for_tests() -> None:
    target = parse_target("http://localhost:8000")
    assert resolve_public(target, _resolver("127.0.0.1"), allow_private=True) == "127.0.0.1"


def test_resolution_failures_are_policy_errors() -> None:
    def broken(host: str, port: int) -> list[str]:
        raise OSError("no such host")

    with pytest.raises(PolicyViolation, match="could not resolve"):
        resolve_public(parse_target("https://nope.invalid"), broken)
    with pytest.raises(PolicyViolation, match="did not resolve"):
        resolve_public(parse_target("https://empty.example"), _resolver())
