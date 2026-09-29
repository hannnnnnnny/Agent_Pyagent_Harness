import pyagent


def test_version_is_exposed() -> None:
    assert pyagent.__version__ == "0.1.0"


def test_top_level_api() -> None:
    for name in ("Agent", "AgentOptions", "ApprovalMode", "Budget", "RunResult", "build_agent"):
        assert hasattr(pyagent, name)
