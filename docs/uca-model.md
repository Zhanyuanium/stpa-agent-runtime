# UCA 数据模型（Code + Shell）

更多入口见 `docs/index.md`。

## 1. 相关位置

- Code 域样例 KB：`data/uca/code/sample_kb.json`
- Shell 域 KB：`data/uca/shell/shell_kb.json`
- 数据模型：`src/agentspec_codegen/uca/models.py`
- ATT&CK 战术映射：`src/agentspec_codegen/uca/mitre.py`

## 2. 核心字段（概念口径）

- `uca_id`：稳定且全局唯一的条目 ID（同一 KB 文件内不得重复）
- `domain`：`code` / `shell`
- `risk_type`：域内归一化的风险类别
- `mitre_tactic`：ATT&CK 战术标签（用于归类与对齐威胁模型）
- `trigger_event`：触发事件（Code 常为 `PythonREPL`；Shell 常为 `TerminalExecute`）
- `predicate_hints`：编译器优先使用的谓词提示列表（有序合取）
- `enforcement`：期望的裁决策略（如 `stop`、`skip`、`user_inspection` 等）

## 3. 校验与扩展

- `risk_type` 与 `mitre_tactic` 需满足映射约束（否则应在模型/映射表中补齐）
- 扩展新风险类别时：
  - 先在 `UcaRiskType` 中定义
  - 再补齐 ATT&CK 映射（如 `ATTACK_TACTIC_TO_RISKS`）
  - 并添加对应的编译映射与测试后再进入实验

