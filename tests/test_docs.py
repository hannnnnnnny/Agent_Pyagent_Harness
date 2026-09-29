"""Keep code in the documentation in sync with the code base."""

import re
from pathlib import Path

import pytest

from pyagent.config import parse_config

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10
    import tomli as tomllib  # type: ignore[no-redef]

ROOT = Path(__file__).resolve().parent.parent
DOCS = [ROOT / "README.md", *sorted((ROOT / "docs").glob("*.md"))]


def _blocks(language: str) -> list[tuple[str, str]]:
    found = []
    for doc in DOCS:
        for block in re.findall(rf"```{language}\n(.*?)```", doc.read_text(encoding="utf-8"), re.S):
            found.append((doc.name, block))
    return found


@pytest.mark.parametrize(("doc", "block"), _blocks("toml"))
def test_toml_examples_are_valid_config(doc: str, block: str) -> None:
    parse_config(tomllib.loads(block))


@pytest.mark.parametrize(("doc", "block"), _blocks("python"))
def test_python_examples_compile(doc: str, block: str) -> None:
    compile(block, doc, "exec")


def test_docs_have_examples() -> None:
    assert _blocks("toml")
    assert _blocks("python")
