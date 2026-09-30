from pyagent.safety.env import scrub_env

SOURCE = {
    "PATH": "/usr/bin",
    "Path": "C:\\Windows",
    "HOME": "/home/me",
    "ANTHROPIC_API_KEY": "sk-ant-secret",
    "AWS_SECRET_ACCESS_KEY": "aws",
    "GITHUB_TOKEN": "ghp_x",
    "DATABASE_URL": "postgres://u:p@h/db",
    "LANG": "C.UTF-8",
}


def test_only_passthrough_variables_survive() -> None:
    assert scrub_env(SOURCE) == {
        "PATH": "/usr/bin",
        "Path": "C:\\Windows",
        "HOME": "/home/me",
        "LANG": "C.UTF-8",
    }


def test_secret_names_are_dropped_even_if_allowlisted() -> None:
    env = scrub_env(SOURCE, passthrough=["PATH", "GITHUB_TOKEN", "DATABASE_URL"])
    assert "GITHUB_TOKEN" not in env
    assert env["DATABASE_URL"] == "postgres://u:p@h/db"


def test_extra_variables_are_added() -> None:
    env = scrub_env(SOURCE, extra={"PYAGENT": "1"})
    assert env["PYAGENT"] == "1"


def test_source_is_not_mutated() -> None:
    source = dict(SOURCE)
    scrub_env(source)
    assert source == SOURCE


def test_provider_keys_never_reach_subprocesses() -> None:
    source = {"PATH": "/bin", "DEEPSEEK_API_KEY": "sk-ds", "ANTHROPIC_API_KEY": "sk-ant"}
    assert scrub_env(source) == {"PATH": "/bin"}
