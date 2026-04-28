# 语义映射规范（UCA → 谓词 → 规则）

更多入口见 `docs/index.md`。本文定义从 UCA 条目到可执行 `.spec` 规则的映射契约，用于保证可追溯与确定性。

## 1. 映射契约

- **输入**：UCA 条目（`domain`、`risk_type`、`mitre_tactic`、`trigger_event`、`hazard_ids`、`safety_constraint_ids` 等）
- **中间态**：谓词列表（有序合取）
- **输出**：AgentSpec `.spec` 规则文本

## 2. 不变量（必须满足）

- 每个 UCA 必须映射到**且仅映射到**一个 `trigger_event`
- 每个 UCA 必须映射到**至少一个**谓词
- `risk_type` 必须与 `mitre_tactic` 兼容
- `hazard_ids` 使用 `H{number}` 格式；`safety_constraint_ids` 使用 `SC-{2 digits}` 格式
- 编译得到的 `.spec` 必须能被 `Rule.from_text` 解析

## 3. 域映射约定

- **code**：
  - 触发通常为 `PythonREPL`
  - 谓词实现主要位于 `rules/manual/pythonrepl.py`
- **shell**：
  - 触发通常为 `TerminalExecute`
  - 谓词实现主要位于 `rules/manual/shell.py` 与 OS 检查模块

## 4. enforce 策略（经验规则）

- **高置信度高危**：默认 `stop`
- **业务语义强/不确定性高**：使用 `user_inspection`（要求人工复核）
- **（若启用）生成式 RQ2 双轨**：
  - LLM 给出 `llm_enforcement_suggestion`（如 `skip/stop`）
  - 运行时使用确定性策略得到 `final_enforcement`
  - 冲突写入审计，便于复盘

## 5. 可追溯性

- 审计至少保留 `rule_id`，并尽可能保留/还原 `uca_id`
- 若有生成式 lineage，应记录：
  - `llm_enforcement_suggestion` / `final_enforcement`
  - `decision_reason` / `decision_conflict`
- 每条 UCA 的 `hazard_ids` 与 `safety_constraint_ids` 是论文/审计层面的主锚点

## 6. 确定性规则

- `rule_id` 由 `uca_id` 规范化生成
- 谓词顺序保持 `predicate_hints` 的顺序；缺失时按默认映射表补齐
- 模板输出需 byte-level 稳定（用于 golden 测试）

## 7. Owner-Harm 扩展（若启用）

- `UcaEntry` 可包含 `owner_harm_category`
- 若未显式提供，可按 `risk_type` 做确定性映射，并在评测结果中按 owner-harm 分组输出统计

