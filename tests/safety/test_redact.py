import pytest

from pyagent.safety.redact import PLACEHOLDER, Redactor, secrets_from_env

redactor = Redactor()

# Test fixtures are assembled at runtime so the repository never contains
# strings that secret scanners would flag as real credentials.
FAKE = {
    "anthropic": "sk-ant-" + "api03-" + "a" * 40,
    "aws": "AKIA" + "ABCDEFGHIJKLMNOP",
    "github": "ghp_" + "b" * 36,
    "slack": "xoxb-" + "123456789012-abcdef",
    "google": "AIza" + "c" * 35,
    "stripe": "sk_live_" + "d" * 24,
    "jwt": "eyJ" + "e" * 10 + ".eyJ" + "f" * 10 + "." + "g" * 10,
}


@pytest.mark.parametrize("secret", list(FAKE.values()), ids=list(FAKE))
def test_known_formats_are_redacted(secret: str) -> None:
    out = redactor.redact(f"value: {secret} end")
    assert secret not in out
    assert out == f"value: {PLACEHOLDER} end"


def test_private_key_block_is_redacted() -> None:
    key = "-----BEGIN RSA PRIVATE KEY-----\nMIIE\nabc\n-----END RSA PRIVATE KEY-----"
    assert redactor.redact(f"x\n{key}\ny") == f"x\n{PLACEHOLDER}\ny"


def test_bearer_token_keeps_scheme() -> None:
    assert redactor.redact("Authorization: Bearer abcdefghijklmnop1234") == (
        f"Authorization: Bearer {PLACEHOLDER}"
    )


def test_url_credentials_are_redacted() -> None:
    assert redactor.redact("postgres://admin:hunter2@db:5432/x") == (
        f"postgres://{PLACEHOLDER}@db:5432/x"
    )


@pytest.mark.parametrize(
    "line",
    ['password = "correcthorse"', "API_KEY: s3cr3tvalue", "token=abcdef123456"],
)
def test_secret_assignments_are_redacted(line: str) -> None:
    out = redactor.redact(line)
    assert PLACEHOLDER in out
    assert out.split(PLACEHOLDER)[0].strip()


def test_ordinary_text_is_untouched() -> None:
    text = "def token_count(text): return len(text.split())  # password policy docs"
    assert redactor.redact(text) == text


def test_known_secrets_are_redacted_longest_first() -> None:
    r = Redactor(patterns={})
    r.add_secrets(["abcdefgh", "abcdefghijkl", "short"])
    assert r.redact("abcdefghijkl and abcdefgh and short") == (
        f"{PLACEHOLDER} and {PLACEHOLDER} and short"
    )


def test_secrets_from_env_only_takes_secret_names() -> None:
    env = {"MY_API_KEY": "value-123456", "HOME": "/home/user-long", "DB_PASSWORD": "tiny"}
    assert secrets_from_env(env) == {"value-123456"}


def test_from_environment() -> None:
    r = Redactor.from_environment({"SERVICE_TOKEN": "unusual-format-value"})
    assert r.redact("got unusual-format-value") == f"got {PLACEHOLDER}"
