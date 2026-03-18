# CUA Control Loop Model

## Components
- Controller: LLM planner (chooses next tool action).
- Actuator:
  - Python code executor.
  - Shell command executor.
- Controlled process: OS state transition (files, permissions, network, processes).
- Sensor/feedback:
  - tool observations
  - runtime audits
  - predicate checks on OS context
- Safety controller: AgentSpec rule interpreter and enforcement module.

## Control Flow
1. User requirement enters planner.
2. Planner proposes action (tool + input).
3. AgentSpec evaluates trigger and predicates.
4. Enforcement decision:
   - continue
   - stop
   - user_inspection
   - self_reflect
5. Action executes only if allowed; feedback enters next planning step.

## Main Hazards
- H1: action writes or deletes critical system targets.
- H2: action leaks sensitive data to untrusted endpoints.
- H3: action establishes persistence mechanisms.
- H4: action escalates privileges without authorization.

## Safety Design Hooks
- Event trigger at each planned action.
- Context-aware predicates with cache.
- Auditable enforcement logs with rationale snapshot.
