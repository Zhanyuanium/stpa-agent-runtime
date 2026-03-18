# STPA Analysis for AgentSpec (Code + Shell)

## Objective
- Derive unsafe control actions (UCA) for code and shell tool use.
- Convert UCA findings into enforceable AgentSpec rules.

## System Boundary
- Controlled system: LLM-based tool-using agent.
- Environment: Linux runtime in Docker sandbox.
- Actuators:
  - `PythonREPL` for code execution.
  - `TerminalExecute` for shell commands.
- Losses to prevent:
  - Data exfiltration.
  - Persistence/backdoor installation.
  - Privilege abuse and destructive system changes.

## Unsafe Control Actions (Representative)
- UCA-CODE-001: sending sensitive data to untrusted endpoint.
- UCA-CODE-002: writing startup backdoor in shell profile files.
- UCA-SHELL-001: recursive destructive deletion on sensitive paths.
- UCA-SHELL-002: privilege escalation command without policy guard.
- UCA-SHELL-003: outbound upload of local secrets using network tools.

## Hazard -> UCA Derivation Map
- H1 (critical system targets corrupted):
  - UCA-SHELL-001
- H2 (sensitive data exfiltrated):
  - UCA-CODE-001
  - UCA-SHELL-003
- H3 (unauthorized persistence established):
  - UCA-CODE-002
  - UCA-SHELL-003
- H4 (unauthorized privilege escalation):
  - UCA-SHELL-002

## Safety Constraints
- SC-01: block untrusted outbound transfer for sensitive payloads.
- SC-02: block persistence changes in startup/system profile locations.
- SC-03: deny destructive operations on protected paths.
- SC-04: deny privilege-changing shell operations unless explicit allowlist.

## UCA -> SC Mapping
- UCA-CODE-001 -> SC-01
- UCA-CODE-002 -> SC-02
- UCA-SHELL-001 -> SC-03
- UCA-SHELL-002 -> SC-04
- UCA-SHELL-003 -> SC-01, SC-02

## Traceability
- Each UCA maps to:
  - ATT&CK tactic.
  - Predicate set.
  - Enforcement strategy (`stop`/`user_inspection`).
- UCA entries in `data/uca/**/*.json` also carry:
  - `hazard_ids` (e.g., `H2`)
  - `safety_constraint_ids` (e.g., `SC-01`)
- Mapping details are specified in `docs/semantic-mapping.md`.
