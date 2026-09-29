"""Server-side request forgery tricks against the URL and address checks.

Numeric host forms are resolved by the real system resolver (no DNS traffic
is needed for literal addresses or localhost), exactly as in production.
"""

from __future__ import annotations

import pytest

from pyagent.errors import PolicyViolation
from pyagent.safety.net import parse_target, resolve_public

LOOPBACK_AND_PRIVATE_FORMS = [
    "http://127.0.0.1/",
    "http://127.1/",
    "http://2130706433/",
    "http://0x7f000001/",
    "http://0177.0.0.1/",
    "http://localhost/",
    "http://LOCALHOST./",
    "http://[::1]/",
    "http://[::ffff:127.0.0.1]/",
    "http://[0:0:0:0:0:ffff:7f00:1]/",
    "http://0.0.0.0/",
    "http://169.254.169.254/latest/meta-data/",
    "http://[fd00:ec2::254]/",
    "http://10.0.0.1/",
    "http://192.168.0.1:8080/admin",
    "http://172.31.255.255/",
    "http://100.100.100.200/",
]


@pytest.mark.parametrize("url", LOOPBACK_AND_PRIVATE_FORMS)
def test_internal_targets_are_unreachable(url: str) -> None:
    with pytest.raises(PolicyViolation):
        resolve_public(parse_target(url))


@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "gopher://127.0.0.1:6379/_FLUSHALL",
        "dict://127.0.0.1:11211/",
        "ftp://example.com/",
        "jar:http://example.com!/",
        "http://user:pass@example.com/",
        "http://example.com@127.0.0.1/",
        "javascript:alert(1)",
        "data:text/plain,hello",
    ],
)
def test_dangerous_url_forms_are_rejected(url: str) -> None:
    with pytest.raises(PolicyViolation):
        resolve_public(parse_target(url))


def test_hostname_that_resolves_to_mixed_addresses_is_rejected() -> None:
    def rebinding(host: str, port: int) -> list[str]:
        return ["93.184.216.34", "127.0.0.1"]

    with pytest.raises(PolicyViolation, match="non-public"):
        resolve_public(parse_target("http://rebind.example/"), rebinding)
