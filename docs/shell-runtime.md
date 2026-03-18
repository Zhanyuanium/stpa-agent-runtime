# Shell Runtime Guide

## Modules
- Parser: `src/agentspec_codegen/shell_parser/`
  - `ast_extractor.py`: tokenization and risk-flag extraction.
  - `shellcheck_wrapper.py`: optional shellcheck diagnostics with graceful fallback.
- Predicates:
  - `src/agentspec_codegen/predicates/os_checks.py`
  - `src/rules/manual/shell.py`

## Input / Output
- Input: shell command string proposed by agent tools (`TerminalExecute`).
- Output:
  - parser features (`argv`, `paths`, `risk_flags`).
  - boolean predicate decisions used by AgentSpec checks.
  - audit records via runtime context.

## Failure Modes
- `shellcheck` not installed:
  - wrapper returns `available=False`, diagnostics empty.
- malformed command text:
  - parser falls back to whitespace split; still returns deterministic output.

## Test Entrypoints
- `tests/unit/test_shell_parser.py`
- `tests/unit/test_shell_predicates.py`
- `tests/unit/test_os_checks.py`
- `tests/integration/test_run_agent_experiment.py`
