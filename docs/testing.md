# Testing Strategy

## Test Types
- Unit tests: parser, predicates, compiler mapping, runtime actions.
- Integration tests: JSON UCA -> `.spec` generation -> interpreter check.
- E2E smoke tests: minimal code-domain case and metrics output.
- Model-in-loop tests: shell risky/benign cases through runtime interpreter.

## Layout
- `tests/unit/`
- `tests/integration/`
- `tests/e2e/`
- `tests/golden/`

## Baseline Command
```bash
uv run pytest
```

## Coverage Command (Core Modules)
```bash
uv run pytest --cov=src/agentspec_codegen --cov=scripts --cov-report=term-missing
```

## Coverage Goal
- Core modules target >= 85% line coverage.
