# Current Limitations (Code Domain Phase)

- Evaluation script currently focuses on deterministic heuristic checks, not full model-in-the-loop execution.
- False-positive estimation is limited because RedCode-Exec is risk-oriented; a dedicated benign set is still needed.
- Runtime cache key is action-name scoped and does not yet include full tool-input hashing.
- Existing legacy modules still contain historical grammar/test artifacts and are not fully normalized in this phase.
- AV and embodied domains are intentionally deferred to later phases.
