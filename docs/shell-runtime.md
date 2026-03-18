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
  - audit records via runtime context (`command_text`, `shellcheck_summary`, `shellcheck_diagnostics`).
  - staged artifacts (`01~05`) for experiment traceability.

## Auditable Pipeline Outputs
- `01_uca_loaded.json`: loaded shell UCA KB (strict spec-runtime).
- `02_compiled_specs/*.spec` + `02_compiled_manifest.json`: compiled runtime rules and mapping.
- `03_rules_parsed.json`: parsed `Rule` objects from `.spec`.
- `04_check_traces/{case_id}.json`: per-rule trigger/check/enforce traces.
- `05_case_audits.jsonl`: per-case compact audit stream (includes shellcheck diagnostics).

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
