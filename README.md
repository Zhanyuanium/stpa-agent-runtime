# AgentSpec：面向 LLM 智能体的可审计运行时规则执行（Code + Shell）

本仓库实现并评测一种**“UCA（STPA）→ DSL 规则 → 运行时拦截”**的安全执行链路，面向 LLM 智能体在调用工具（如 `PythonREPL`、`TerminalExecute`）时的高风险操作进行**确定性**约束与审计留痕。

本分支的核心目标是把实验与运行时收敛成一条**可审计、可复现、可扩展**的严格路径：

- **主链路**：`UCA -> .spec -> Rule.from_text -> RuleInterpreter -> enforce`
- **统一产物契约**：每次运行输出同一套 `01~05` 中间态（便于论文复核与回放）
- **Shell 审计增强**：若环境安装 `shellcheck`，诊断会并入审计记录；未安装则自动降级为空诊断（不影响可复现性）

## 快速开始

### 1) 环境

- Python **3.11+**（建议）
- 依赖管理：`uv`

```bash
uv sync
```

### 2) 数据政策（重要）

本仓库**不提交**大体积上游基准数据与运行产物（见 `.gitignore`），仅保留脚本与最小样例配置。

- 风险样本（需自行准备）：
  - Code：`benchmarks/RedCode-Exec/py2text_dataset_json`
  - Shell：`benchmarks/RedCode-Exec/bash2text_dataset_json`
- 良性样本（示例路径，具体以你的环境为准）：
  - `benchmarks/shell/benign_commands.json`

布局校验：

```bash
uv run python scripts/verify_dataset.py --redcode-root ./benchmarks/RedCode-Exec/py2text_dataset_json
```

## 复现入口（导航）

为了避免 README 冗长，复现实验的完整说明下沉到 `docs/`。你可以从下面几条主线进入：

- **文档总入口**：`docs/index.md`
- **Code 域 RQ1/RQ2（baseline/manual/generated）**：见 `docs/experiments/code-domain.md`
- **Shell 严格运行时评测（spec-runtime）**：见 `docs/shell-runtime.md`
- **产物口径（01~05）与指标定义**：见 `docs/runtime-guard.md`
- **开发/测试**：见 `docs/development.md`、`docs/testing.md`
- **限制与边界**：见 `docs/limitations.md`

## 目录结构（概览）

```text
AgentSpec/
├─ data/uca/                 # UCA 知识库（手工/生成）
├─ src/                      # 解释器、谓词、编译与评测组件
├─ scripts/                  # 数据校验、实验运行、报表导出脚本
├─ docs/                     # 设计与复现文档（README 只做导航）
└─ tests/                    # 单元/集成/E2E
```

## 引用

```bibtex
@misc{wang2025agentspeccustomizableruntimeenforcement,
  title={AgentSpec: Customizable Runtime Enforcement for Safe and Reliable LLM Agents},
  author={Haoyu Wang and Christopher M. Poskitt and Jun Sun},
  year={2025},
  eprint={2503.18666},
  archivePrefix={arXiv},
  primaryClass={cs.AI},
  url={https://arxiv.org/abs/2503.18666}
}
```
