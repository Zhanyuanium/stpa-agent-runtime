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

## Safety Constraints
- SC-01: block untrusted outbound transfer for sensitive payloads.
- SC-02: block persistence changes in startup/system profile locations.
- SC-03: deny destructive operations on protected paths.
- SC-04: deny privilege-changing shell operations unless explicit allowlist.

## Traceability
- Each UCA maps to:
  - ATT&CK tactic.
  - Predicate set.
  - Enforcement strategy (`stop`/`user_inspection`).
- Mapping details are specified in `docs/semantic-mapping.md`.
