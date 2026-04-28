# 运行时守卫与审计口径（Code + Shell）

更多入口见 `docs/index.md`。本文描述“严格 spec-runtime”下的**审计产物口径**与**运行时约束点**，用于复现与论文复核。

## 1. 严格链路回顾

`UCA -> .spec -> Rule.from_text -> RuleInterpreter -> enforce (+ audit)`

其中 `check` 阶段会调用谓词函数；`enforce` 阶段会输出确定性的裁决动作：

- `continue`：放行
- `skip`：跳过/拒绝执行该动作
- `stop`：拦截并终止该动作
- `user_inspection`：要求人工复核

## 2. 审计产物（01~05）

无论 Code 还是 Shell，只要脚本以 strict spec-runtime 运行，`--artifact-root` 目录下应包含：

- `01_uca_loaded.json`：加载后的 UCA KB（含版本、条目、元数据）
- `02_compiled_specs/*.spec`：编译得到的规则文本
- `02_compiled_manifest.json`：规则来源映射（`rule_id/uca_id/predicates/spec_path/...`）
- `03_rules_parsed.json`：`.spec` 解析为运行时 `Rule` 的结果（含解析错误）
- `04_check_traces/{case_id}.json`：按样本记录 trigger/check/enforce 轨迹（用于回放）
- `05_case_audits.jsonl`：按样本输出的紧凑审计流（供统计脚本消费）

> 说明：Shell 模式下，若 shellcheck 可用，`05_case_audits.jsonl` 会包含 shellcheck 摘要与原始诊断；不可用则为空诊断字段。

## 3. 运行时缓存与失败策略

- **谓词缓存**：对同一 action 输入的重复谓词求值可缓存，用于降低开销（具体键策略以实现为准）。
- **未知谓词**：若规则引用了未注册谓词，应明确失败（便于尽早暴露规则/实现不一致）。

