# Development Guide

## Environment
- Python >= 3.10
- Use `uv` for dependency management.

## Setup
```bash
uv venv
uv sync --extra dev
```

## Local Commands
```bash
uv run pytest
uv run pytest --cov=src --cov-report=term-missing
```

## Branch and Commit
- Work in local feature branches.
- Commit in small increments with conventional prefixes:
  - `feat(scope): ...`
  - `test(scope): ...`
  - `docs(scope): ...`
  - `chore(scope): ...`
