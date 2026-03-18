# Current Limitations (Code + Shell Phase)

- Shell experiment path is intentionally strict spec-runtime only; LLM direct-judgment backend is not provided in this branch.
- Shell grammar compatibility still relies on parser-known predicate names; fully dynamic predicate token extension is a future task.
- Runtime cache key is action-name scoped and does not yet include full tool-input hashing.
- Docker compose is designed for reproducible sandboxing, but resource-intensive services may require host-specific tuning.
- AV and embodied domains remain intentionally deferred.
