from pathlib import Path

import pytest

from pyagent.errors import ToolError
from pyagent.safety.fileio import is_binary, read_text, write_text


def test_is_binary_detects_nul_bytes() -> None:
    assert is_binary(b"abc\x00def")
    assert not is_binary("héllo".encode())


def test_read_text_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "a.txt"
    path.write_bytes("héllo\n".encode())
    assert read_text(path) == "héllo\n"


def test_read_text_replaces_invalid_utf8(tmp_path: Path) -> None:
    path = tmp_path / "a.txt"
    path.write_bytes(b"ok \xff")
    assert read_text(path) == "ok �"


def test_read_missing_file(tmp_path: Path) -> None:
    with pytest.raises(ToolError, match="not found"):
        read_text(tmp_path / "nope")


def test_read_directory_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ToolError, match="not a regular file"):
        read_text(tmp_path)


def test_read_limit_enforced(tmp_path: Path) -> None:
    path = tmp_path / "big.txt"
    path.write_text("x" * 100)
    with pytest.raises(ToolError, match="read limit"):
        read_text(path, max_bytes=10)


def test_read_binary_rejected(tmp_path: Path) -> None:
    path = tmp_path / "img.bin"
    path.write_bytes(b"\x89PNG\x00\x00")
    with pytest.raises(ToolError, match="binary"):
        read_text(path)


def test_write_creates_parents_and_reports_size(tmp_path: Path) -> None:
    path = tmp_path / "a" / "b" / "c.txt"
    assert write_text(path, "héllo") == len("héllo".encode())
    assert path.read_text(encoding="utf-8") == "héllo"


def test_write_limit_enforced_without_touching_file(tmp_path: Path) -> None:
    path = tmp_path / "a.txt"
    path.write_text("original")
    with pytest.raises(ToolError, match="write limit"):
        write_text(path, "x" * 100, max_bytes=10)
    assert path.read_text() == "original"


def test_write_leaves_no_temp_files(tmp_path: Path) -> None:
    write_text(tmp_path / "a.txt", "one")
    write_text(tmp_path / "a.txt", "two")
    assert [p.name for p in tmp_path.iterdir()] == ["a.txt"]


def test_write_over_directory_rejected(tmp_path: Path) -> None:
    (tmp_path / "d").mkdir()
    with pytest.raises(ToolError, match="not a regular file"):
        write_text(tmp_path / "d", "x")
