# Current Limitations (Code + Shell Phase)

- Shell experiment path is intentionally strict spec-runtime only; LLM direct-judgment backend is not provided in this branch.
- Shell grammar compatibility still relies on parser-known predicate names; fully dynamic predicate token extension is a future task.
- Runtime cache key is action-name scoped and does not yet include full tool-input hashing.
- Docker compose is designed for reproducible sandboxing, but resource-intensive services may require host-specific tuning.
- AV and embodied domains remain intentionally deferred.
- Owner-Harm 的 post-audit verifier 当前为 deterministic 规则集，对隐式语义攻击与跨轮长程依赖仍有漏检边界。
- `structured_goal` 条件目前采用模板化 owner goal，不等同于真实产品中的授权工单/业务流程上下文。
- AgentHarm 适配器采用宽松字段兼容策略，遇到非标准 schema 时可能退化到 `unknown` category，需要按数据版本补充映射。
