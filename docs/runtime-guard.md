# Runtime Guard (Code Domain)

## What Was Added
- Runtime context object with:
  - predicate evaluation cache
  - structured audit records
- Audit recording is now attached during rule evaluation in the executor.

## Audit Record Fields
- `timestamp`
- `rule_id`
- `event`
- `action_name`
- `enforce_result`
- `detail` (predicate evaluation history snapshot)

## Execution Notes
- Predicate evaluation uses cache key:
  - `rule_id:predicate_name:action_name`
- Unknown predicates now fail fast with explicit error.
