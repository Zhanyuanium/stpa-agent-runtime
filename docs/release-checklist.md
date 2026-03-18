# Release Checklist (Code Domain)

## Quality Gates
- [ ] `uv run pytest` passes.
- [ ] `uv run pytest --cov=src --cov-report=term-missing` runs without failure.
- [ ] E2E pipeline test passes.

## Artifact Validation
- [ ] UCA sample file validates.
- [ ] Shell UCA sample file validates.
- [ ] Compiler emits parsable `.spec` files.
- [ ] Experiment runner emits both `result.json` and `report.md`.
- [ ] Model-in-loop runner emits risky/benign comparative metrics.

## Security and Data
- [ ] No benchmark raw data committed.
- [ ] No API keys or `.env` secrets committed.
- [ ] Dataset path documented with local-only setup.

## Documentation
- [ ] Architecture and runtime docs updated.
- [ ] Shell runtime guide and parser fallback behavior documented.
- [ ] Experiment reproduction steps verified.
- [ ] Limitations document reviewed before report export.
