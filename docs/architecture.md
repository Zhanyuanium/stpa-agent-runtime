# 架构总览（Code + Shell）

更多入口见 `docs/index.md`。

## 1. 范围与主链路

本阶段聚焦 **Code** 与 **Shell** 两个域的运行时防护评测，目标是把实验与运行时统一到同一条严格链路上：

`UCA 知识库 -> .spec 规则文本 -> 规则解析 -> 解释器逐 check 求值 -> enforce + 审计`

其中：

- **UCA**：来自 STPA/系统安全分析的 Unsafe Control Actions，表达“在何种条件下不应执行某类控制动作”
- **.spec**：AgentSpec DSL 规则文本（由编译器根据 UCA 自动生成）
- **谓词（predicate）**：运行时对工具输入/上下文的确定性检查（如路径、网络、权限、编码/混淆等）

## 2. 控制回路视角（简化）

- **控制器**：LLM/智能体规划器（生成下一步动作）
- **执行器**：工具调用（`PythonREPL`、`TerminalExecute` 等）
- **受控过程**：操作系统/运行时环境状态
- **监控与约束器**：AgentSpec 解释器 + 谓词库 + enforce 动作（继续/跳过/拦截/人工复核）

## 3. 模块分层

- `src/agentspec_codegen/uca/`：UCA 数据模型、读写、（可选）战术标签映射
- `src/agentspec_codegen/compiler/`：UCA -> `.spec` 的编译器（模板生成）
- `src/agentspec_codegen/runtime/`：运行时上下文、缓存与审计记录模型
- `src/agentspec_codegen/shell_parser/`：Shell 命令解析与特征提取、shellcheck 诊断包装
- `src/rules/manual/`：手工谓词实现（Code/Shell），供解释器执行 `check` 时调用
- `src/interpreter.py`、`src/rule.py`、`src/spec_lang/AgentSpec.g4`：DSL 解析与执行核心
- `scripts/`：数据校验、实验运行、报表导出

## 4. 关键集成点（便于排障）

- **规则编译**：`src/agentspec_codegen/compiler/`
- **规则解析/执行**：`src/rule.py`、`src/interpreter.py`
- **谓词注册表**：`src/rules/manual/table.py`
- **Shell 解析/诊断**：`src/agentspec_codegen/shell_parser/`

