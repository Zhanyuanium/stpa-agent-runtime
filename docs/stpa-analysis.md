# STPA/UCA 分析摘要（Code + Shell）

更多入口见 `docs/index.md`。本文给出本仓库使用的 STPA→UCA 的**最小摘要**，用于解释 UCA KB 字段（hazard/constraint）从何而来。

## 1. 目标

- 面向智能体的工具调用场景，识别并抽象 Unsafe Control Actions（UCA）
- 将 UCA 以知识库形式固化，并编译为可执行的 `.spec` 规则

## 2. 系统边界（简化）

- **受控系统**：基于 LLM 的工具型智能体
- **环境**：操作系统运行时（可通过容器/沙箱复现）
- **执行器（Actuators）**：
  - `PythonREPL`：代码执行
  - `TerminalExecute`：Shell 命令执行

## 3. 需要避免的损失（Losses）

- 敏感数据外泄（网络出站/工具出站）
- 未授权持久化/后门（启动脚本、profile 等）
- 权限滥用与破坏性变更（rm/chmod/chown/用户管理等）

## 4. 代表性 UCA（示例）

- Code：向不可信端点发送敏感数据
- Code：向启动文件写入持久化后门
- Shell：对敏感路径执行破坏性递归删除
- Shell：无策略护栏的提权/权限修改
- Shell：通过网络工具上传本地机密

## 5. Hazard 与 Safety Constraint

- **Hazard（H\*)**：系统层面的不安全状态（例如“关键目标被破坏”“机密被外泄”等）
- **Safety Constraint（SC-\*)**：对控制动作的约束（例如“禁止向不可信端点传输敏感载荷”等）

UCA 条目在 `data/uca/**/*.json` 中显式携带 `hazard_ids` 与 `safety_constraint_ids`，用于论文与审计的可追溯性锚点。映射与执行策略细节见 `docs/semantic-mapping.md`。

