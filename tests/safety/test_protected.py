import pytest

from pyagent.errors import SandboxViolation
from pyagent.safety.protected import ProtectedPaths

rules = ProtectedPaths()


@pytest.mark.parametrize(
    "path",
    [
        ".env",
        ".env.production",
        "config/.env",
        "certs/server.pem",
        "deploy/prod.KEY",
        "home/.ssh/id_rsa",
        "id_ed25519.pub",
        ".git/config",
        ".GIT/CONFIG",
        ".aws/credentials",
        ".ssh/known_hosts",
        ".pyagent/audit.jsonl",
        "vendor/lib/.git/config",
        "nested/.aws/config",
    ],
)
def test_secret_files_cannot_be_read(path: str) -> None:
    with pytest.raises(SandboxViolation, match="blocked by rule"):
        rules.check_read(path)


@pytest.mark.parametrize("path", ["src/app.py", "README.md", ".gitignore", "env.py", "keys.py"])
def test_ordinary_files_can_be_read(path: str) -> None:
    rules.check_read(path)


@pytest.mark.parametrize("path", [".git", ".git/hooks/pre-commit", ".git/HEAD", ".env"])
def test_git_internals_and_secrets_cannot_be_written(path: str) -> None:
    with pytest.raises(SandboxViolation):
        rules.check_write(path)


def test_git_metadata_other_than_config_is_readable() -> None:
    rules.check_read(".git/HEAD")


def test_gitignore_is_writable() -> None:
    rules.check_write(".gitignore")


def test_allow_list_overrides_deny_rules() -> None:
    custom = ProtectedPaths(allow=(".env.example",))
    custom.check_read(".env.example")
    with pytest.raises(SandboxViolation):
        custom.check_read(".env")


def test_custom_rules_replace_defaults() -> None:
    custom = ProtectedPaths(no_read=("secrets/**",), no_write=())
    custom.check_read(".env")
    with pytest.raises(SandboxViolation):
        custom.check_read("secrets/token.txt")
