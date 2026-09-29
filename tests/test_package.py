import pyagent


def test_version_is_exposed() -> None:
    assert pyagent.__version__ == "0.1.0"
