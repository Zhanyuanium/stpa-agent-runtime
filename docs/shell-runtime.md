# Shell 运行时（Strict Spec-Runtime）

更多入口见 `docs/index.md`。本文描述 Shell 域的运行时组件、审计产物与常见故障模式。

## 1. 模块组成

- **Shell 解析与特征提取**：`src/agentspec_codegen/shell_parser/`
  - `ast_extractor.py`：将命令文本解析为 `argv/paths/risk_flags` 等结构化特征
  - `shellcheck_wrapper.py`：可选的 shellcheck 诊断包装（无依赖时自动降级）
- **谓词实现**：
  - OS/路径/权限类检查：`src/agentspec_codegen/predicates/os_checks.py`
  - Shell 域手工谓词：`src/rules/manual/shell.py`

## 2. 输入/输出契约

- **输入**：工具动作 `TerminalExecute` 的命令字符串
- **输出**：
  - 解析特征（`argv`、`paths`、`risk_flags`）
  - 谓词求值结果（布尔值，供 `.spec` 的 `check` 使用）
  - 审计记录（含命令文本、shellcheck 摘要/诊断等字段）
  - 统一的 `01~05` 中间态产物（用于实验可追溯）

## 3. 可审计产物（01~05）

Shell 域严格运行时评测完成后，`--artifact-root` 目录下应包含：

- `01_uca_loaded.json`
- `02_compiled_specs/*.spec` 与 `02_compiled_manifest.json`
- `03_rules_parsed.json`
- `04_check_traces/{case_id}.json`
- `05_case_audits.jsonl`（若 shellcheck 可用则包含诊断字段）

产物字段口径与更多解释见 `docs/runtime-guard.md`。

## 4. 常见故障模式

- **未安装 `shellcheck`**：
  - 包装器返回 `available=false`，诊断为空；其余流程不受影响
- **命令文本非常规/不可解析**：
  - 解析器会退化到更保守的切分策略，保证确定性输出（但语义完备性下降）

## 5. 测试入口

- `tests/unit/test_shell_parser.py`
- `tests/unit/test_shell_predicates.py`
- `tests/unit/test_os_checks.py`
- `tests/integration/test_run_agent_experiment.py`

