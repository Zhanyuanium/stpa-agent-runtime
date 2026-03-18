# AgentSpec Architecture (Code + Shell)

## Scope
- This branch targets code-domain and shell-domain runtime enforcement.
- Pipeline: STPA/UCA knowledge -> DSL compilation -> runtime guard -> experiment report.

## Control-Loop View
- Controller: LLM/agent planner.
- Actuator: PythonREPL and shell execution tools.
- Controlled process: Linux OS runtime state.
- Monitor/enforcer: AgentSpec interpreter + predicate checks + enforcement actions.

## Layered Modules
- `src/agentspec_codegen/uca/`: UCA schema, ATT&CK tactic mapping, knowledge-base I/O.
- `src/agentspec_codegen/shell_parser/`: command parsing and risk feature extraction.
- `src/agentspec_codegen/compiler/`: UCA to AgentSpec rule compiler (Jinja2 template based).
- `src/agentspec_codegen/predicates/`: OS context-aware checks (path, permissions, backup, network).
- `src/agentspec_codegen/runtime/`: runtime cache and audit records.
- `src/rules/manual/`: code and shell predicates registered into interpreter.
- `scripts/`: dataset validation, experiments, report export.
- `docker/`: reproducible sandbox for isolated experiments.

## Runtime Integration Points
- Executor: `src/controlled_agent_excector.py`
- Interpreter: `src/interpreter.py`
- Enforcement: `src/enforcement.py`
- Predicate registry: `src/rules/manual/table.py`
- Rule parser/model: `src/rule.py`, `src/spec_lang/AgentSpec.g4`

## Experiment Modes
- Heuristic mode: fast regression for development.
- Model-in-loop mode: run full decision loop and enforce rules online.
- Both modes report interception rate, false-positive rate, completion rate, and latency.
