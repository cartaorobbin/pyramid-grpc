---
description: Enforces uv as the sole dependency manager for this project
alwaysApply: true
---

# Dependency Management — uv

This project uses **uv** for all dependency management. These rules are non-negotiable.

## REQUIRED commands

| Operation | Command |
|---|---|
| Add dependency | `uv add <package>` |
| Add dev dependency | `uv add --dev <package>` |
| Remove dependency | `uv remove <package>` |
| Install/sync from lock | `uv sync` |
| Update a package | `uv lock --upgrade-package <package> && uv sync` |
| Update all packages | `uv lock --upgrade && uv sync` |
| Run a command in venv | `uv run <command>` |
| Show installed packages | `uv pip list` |

## FORBIDDEN — never use these

- `pip install` — MUST NOT be used. uv manages the virtual environment and lock file. Using pip directly will cause inconsistencies.
- `pip freeze` — MUST NOT be used. The lock file is `uv.lock`.
- `poetry add` / `poetry install` / `poetry run` — MUST NOT be used. This is not a Poetry project.
- `python -m pip` — MUST NOT be used. Same as `pip install`.
- Editing `uv.lock` — NEVER. Not in an editor, and not with any file-editing tool. Only uv may rewrite it, by running `uv add`, `uv remove`, `uv lock`, or `uv sync`.

## Virtual environment

- uv manages the `.venv/` directory automatically.
- MUST NOT create virtual environments manually (`python -m venv`, `virtualenv`, etc.).
- MUST NOT activate the venv manually to install packages. Use `uv run` or `uv sync`.

## Lock file

- NEVER edit `uv.lock`. Not in an editor, and not with any file-editing tool.
- The only allowed change is uv rewriting the file when you run `uv add`, `uv remove`, `uv lock`, or `uv sync`.
- If `pyproject.toml` and `uv.lock` disagree, run `uv lock`. Do not reconcile the lock file yourself.
- `uv.lock` MUST be committed to version control.
- In CI, use `uv sync --frozen` to install from the lock file without updating it.

<!-- PRIVATE REGISTRY -->
## Private registry

This project uses a private package registry. When adding private packages:
- The index configuration is in `pyproject.toml` under `[tool.uv.index]` or via the `UV_EXTRA_INDEX_URL` environment variable.
- If installs fail with 401/403 errors, the token has likely expired. Use the `codeartifact-auth` skill to refresh credentials.
- MUST NOT hardcode tokens in `pyproject.toml`. Use environment variables for authentication.
<!-- /PRIVATE REGISTRY -->
