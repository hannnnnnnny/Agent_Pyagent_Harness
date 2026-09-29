import pytest

from pyagent.messages import ToolCall
from pyagent.safety.gate import SafetyGate
from pyagent.safety.modes import ApprovalMode
from pyagent.safety.verdict import Verdict
from pyagent.tools.base import Risk
from pyagent.tools.builtin.web_fetch import WebFetch
from pyagent.tools.executor import ToolExecutor
from pyagent.tools.registry import ToolRegistry
from pyagent.web import Fetcher, FetchResult
from tests.tools.conftest import Runner


class FakeFetcher(Fetcher):
    def __init__(self, result: FetchResult, allowed: tuple[str, ...] = ()) -> None:
        super().__init__(allowed_domains=allowed, max_bytes=10)
        self.result = result
        self.urls: list[str] = []

    def fetch(self, url: str) -> FetchResult:
        self.urls.append(url)
        return self.result


PAGE = FetchResult("https://example.org/", 200, "text/html", "# Example\n\nHello")


def test_is_a_network_risk() -> None:
    assert WebFetch.risk is Risk.NETWORK


def test_output_includes_url_and_status(run: Runner) -> None:
    tool = WebFetch(FakeFetcher(PAGE))
    result = run(tool, url="https://example.org")
    assert result.content == "URL: https://example.org/\nStatus: 200\n\n# Example\n\nHello"


def test_truncation_is_reported(run: Runner) -> None:
    page = FetchResult("https://example.org/", 200, "text/plain", "x" * 10, truncated=True)
    assert (
        "(truncated to 10 bytes)" in run(WebFetch(FakeFetcher(page)), url="https://e.org").content
    )


@pytest.mark.parametrize(
    ("url", "verdict"),
    [
        ("https://docs.python.org/3/", Verdict.ALLOW),
        ("https://example.com/", Verdict.BLOCK),
        ("file:///etc/passwd", Verdict.BLOCK),
        ("https://user:pw@python.org", Verdict.BLOCK),
    ],
)
def test_assess_checks_url_and_allowlist(run: Runner, url: str, verdict: Verdict) -> None:
    tool = WebFetch(FakeFetcher(PAGE, allowed=("python.org",)))
    assert tool.assess({"url": url}, run.ctx).verdict is verdict


def test_blocked_urls_never_reach_the_network(run: Runner) -> None:
    fetcher = FakeFetcher(PAGE, allowed=("python.org",))
    tool = WebFetch(fetcher)
    gate = SafetyGate(run.ctx, ApprovalMode.UNATTENDED)
    executor = ToolExecutor(ToolRegistry([tool]), run.ctx, gates=[gate])
    result = executor.execute(ToolCall("1", "web_fetch", {"url": "https://example.com"}))
    assert result.is_error
    assert fetcher.urls == []


def test_without_an_allowlist_every_fetch_needs_approval(run: Runner) -> None:
    tool = WebFetch(FakeFetcher(PAGE))
    assessment = tool.assess({"url": "https://example.org"}, run.ctx)
    assert assessment.verdict is Verdict.ASK
    assert "allow_domains" in assessment.reason


def test_unattended_runs_cannot_fetch_arbitrary_urls(run: Runner) -> None:
    fetcher = FakeFetcher(PAGE)
    gate = SafetyGate(run.ctx, ApprovalMode.UNATTENDED)
    executor = ToolExecutor(ToolRegistry([WebFetch(fetcher)]), run.ctx, gates=[gate])
    result = executor.execute(ToolCall("1", "web_fetch", {"url": "https://example.org"}))
    assert result.is_error
    assert fetcher.urls == []


def test_unattended_runs_can_fetch_allowlisted_domains(run: Runner) -> None:
    fetcher = FakeFetcher(PAGE, allowed=("example.org",))
    gate = SafetyGate(run.ctx, ApprovalMode.UNATTENDED)
    executor = ToolExecutor(ToolRegistry([WebFetch(fetcher)]), run.ctx, gates=[gate])
    result = executor.execute(ToolCall("1", "web_fetch", {"url": "https://example.org"}))
    assert not result.is_error
