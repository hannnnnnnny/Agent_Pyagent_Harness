"""Each module must import cleanly on its own, in a fresh interpreter."""

import pkgutil
import subprocess
import sys

import pytest

import pyagent

MODULES = sorted(m.name for m in pkgutil.walk_packages(pyagent.__path__, prefix="pyagent."))


@pytest.mark.parametrize("module", MODULES)
def test_module_imports_in_isolation(module: str) -> None:
    result = subprocess.run(  # noqa: S603 - fixed interpreter and module name
        [sys.executable, "-c", f"import {module}"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
