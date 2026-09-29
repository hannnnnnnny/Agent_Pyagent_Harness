import pytest

from pyagent.errors import PolicyViolation
from pyagent.safety.net import Target, parse_target


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
