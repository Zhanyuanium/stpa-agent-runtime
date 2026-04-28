# 规则编译器（UCA → AgentSpec DSL）

更多入口见 `docs/index.md`。

## 1. 目标

- 将已校验的 UCA 条目编译为**确定性**的 `.spec` 规则文本
- 保证生成结果稳定，便于回归测试与审计复核
- 通过模板（如 Jinja2）集中管理规则骨架，降低手工维护成本

## 2. 输入/输出

- **输入**：`UcaKnowledgeBase`（见 `src/agentspec_codegen/uca/models.py`）
- **输出**：`CompilationArtifact` 列表，包含：
  - `rule_id`：运行时规则 ID（由 `uca_id` 规范化得到）
  - `uca_id`：来源 UCA
  - `predicates`：谓词合取列表（有序）
  - `spec_text`：生成的 `.spec` 文本

## 3. 映射策略（优先级）

1) 优先使用 UCA 条目中的 `predicate_hints`  
2) 若缺失则回退到风险类别默认映射（如 `DEFAULT_PREDICATE_BY_RISK`）  
3) 规则 ID 规范化示例：`UCA-CODE-001` → `uca_code_001`

## 4. 回归安全

- Golden 快照位于 `tests/golden/`
- 生成的 `.spec` 必须能被现有 `Rule.from_text` 正确解析
- Shell UCA KB 的全量条目应能稳定编译并产出确定性文本

