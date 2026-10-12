"""Each module must import cleanly on its own, without guardrun already loaded.

Import cycles only show up depending on which module is imported first, so
every module is imported with all ``guardrun`` modules purged beforehand.
Third-party packages stay cached, which keeps this fast.
"""

import pkgutil
import subprocess
import sys

import guardrun

# __main__ modules run the CLI on import, so they are exercised by the CLI tests instead.
MODULES = sorted(
    m.name
    for m in pkgutil.walk_packages(guardrun.__path__, prefix="guardrun.")
    if not m.name.endswith(".__main__")
)

SCRIPT = """
import importlib, sys, traceback
failures = []
for name in sys.argv[1:]:
    for loaded in [m for m in sys.modules if m == "guardrun" or m.startswith("guardrun.")]:
        del sys.modules[loaded]
    try:
        importlib.import_module(name)
    except Exception:
        failures.append(name + "\\n" + traceback.format_exc())
print("\\n\\n".join(failures))
sys.exit(1 if failures else 0)
"""


def test_every_module_imports_in_isolation() -> None:
    result = subprocess.run(  # noqa: S603 - fixed interpreter and module names
        [sys.executable, "-c", SCRIPT, *MODULES],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_module_list_is_not_empty() -> None:
    assert "guardrun.agent" in MODULES
