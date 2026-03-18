# Testing Strategy

## Test Types
- Unit tests: parser, predicates, compiler mapping, runtime actions.
- Integration tests: JSON UCA -> `.spec` generation -> interpreter check.
- E2E smoke tests: minimal code-domain case and metrics output.

## Layout
- `tests/unit/`
- `tests/integration/`
- `tests/e2e/`
- `tests/golden/`

## Baseline Command
```bash
uv run pytest
```

## Coverage Goal
- Core modules target >= 85% line coverage.
