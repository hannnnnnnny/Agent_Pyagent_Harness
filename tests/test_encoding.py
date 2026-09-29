"""Every tracked text file must be clean UTF-8.

Guards against a real regression: editing files with a non-UTF-8 default
encoding (cp1252 on Windows) silently double-encoded box-drawing characters
and punctuation in the docs.
"""

import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
TEXT_SUFFIXES = {".py", ".md", ".toml", ".yml", ".yaml", ".txt", ".cfg", ".json"}
# What common non-ASCII characters look like after UTF-8 bytes are mis-decoded
# as cp1252: e.g. a box-drawing character becomes an "a-circumflex" prefix.
MOJIBAKE_MARKERS = tuple(
    ch.encode("utf-8").decode("cp1252")[:2] for ch in ("\u00e9", "\u2014", "\u2502", "\u25b6")
)


def _tracked_text_files() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files"],  # noqa: S607 - git from PATH is fine in tests
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        pytest.skip("not a git checkout")
    return [
        ROOT / name for name in result.stdout.splitlines() if Path(name).suffix in TEXT_SUFFIXES
    ]


@pytest.mark.parametrize("path", _tracked_text_files(), ids=lambda p: p.name)
def test_file_is_clean_utf8(path: Path) -> None:
    if not path.exists():
        pytest.skip("deleted in the working tree")
    text = path.read_bytes().decode("utf-8")
    found = [marker for marker in MOJIBAKE_MARKERS if marker in text]
    assert not found, f"{path.name} contains double-encoded text: {found}"
