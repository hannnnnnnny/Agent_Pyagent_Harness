# Contributing

1. Create a virtual environment and install dev dependencies:
   `python -m venv .venv && .venv/bin/pip install -e ".[dev]"`
2. Keep changes small and focused; one logical change per commit.
3. Use Conventional Commit prefixes (`feat:`, `fix:`, `test:`, `docs:` ...).
4. Before opening a PR run `pytest`, `ruff check .`, `ruff format --check .` and `mypy`.
5. Any change to the safety layer needs tests that exercise the bypass it prevents.
