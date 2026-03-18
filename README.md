# AgentSpec (Code + Shell Branch)

本分支是毕业设计实现分支，目标是围绕开题报告完成 **AgentSpec 代码域 + Shell 域闭环**：

- 离线分析层：`STPA/UCA -> 结构化知识库`
- 规则生成层：`UCA -> AgentSpec DSL (.spec)`
- 在线执行层：`运行时拦截、缓存、审计`（含 shellcheck 诊断并入审计）
- 实验评估层：`baseline/manual/generated` 与 `model-in-loop` 评测

本分支**不包含 OSWorld，不包含 embodied/AV 方向实现**，重点是代码域与 Shell 域安全治理。

---

## 1. 项目结构

```text
.
├─ src/
│  ├─ agentspec_codegen/
│  │  ├─ uca/          # UCA 模型、MITRE 映射、读写
│  │  ├─ shell_parser/ # Shell 命令结构化解析与 shellcheck 封装
│  │  ├─ compiler/     # UCA -> .spec 编译器
│  │  ├─ predicates/   # OS 上下文感知检查
│  │  ├─ runtime/      # 运行时缓存与审计
│  │  └─ eval/         # 评估指标计算
│  ├─ controlled_agent_excector.py
│  ├─ interpreter.py
│  ├─ enforcement.py
│  └─ rules/manual/
│     ├─ pythonrepl.py
│     ├─ shell.py
│     └─ table.py
├─ data/uca/
│  ├─ code/sample_kb.json
│  └─ shell/shell_kb.json
├─ benchmarks/
│  ├─ shell/risky_commands.json
│  └─ shell/benign_commands.json
├─ scripts/
│  ├─ fetch_redcode.ps1
│  ├─ fetch_redcode.sh
│  ├─ verify_dataset.py
│  ├─ run_code_experiment.py
│  ├─ run_agent_experiment.py
│  └─ export_paper_tables.py
├─ tests/
│  ├─ unit/
│  ├─ integration/
│  ├─ e2e/
│  └─ golden/
└─ docs/
   ├─ architecture.md
   ├─ development.md
   ├─ testing.md
   ├─ uca-model.md
   ├─ rule-compiler.md
   ├─ runtime-guard.md
   ├─ shell-runtime.md
   ├─ stpa-analysis.md
   ├─ stpa/cua-control-loop.md
   ├─ semantic-mapping.md
   ├─ experiments/code-domain.md
   ├─ release-checklist.md
   └─ limitations.md
```

---

## 2. 环境准备（uv）

### 2.1 前置条件

- Python `>= 3.10`
- 安装 `uv`

### 2.2 安装依赖

```bash
uv venv
uv sync --extra dev
```

---

## 3. 快速开始

### 3.1 跑测试（推荐先执行）

```bash
uv run pytest
```

覆盖率（核心检查）：

```bash
uv run pytest --cov=src/agentspec_codegen --cov-report=term-missing
```

### 3.2 准备数据集路径

本仓库不提交 RedCode 原始数据。执行：

- Windows:

```powershell
pwsh ./scripts/fetch_redcode.ps1
```

- Linux/macOS:

```bash
bash ./scripts/fetch_redcode.sh
```

然后将数据放到：

`./benchmarks/RedCode-Exec/py2text_dataset_json`

校验：

```bash
uv run python scripts/verify_dataset.py --redcode-root ./benchmarks/RedCode-Exec/py2text_dataset_json
```

### 3.3 运行代码域实验（heuristic）

```bash
uv run python scripts/run_code_experiment.py \
  --mode manual \
  --redcode-root ./benchmarks/RedCode-Exec/py2text_dataset_json \
  --benign-json ./benchmarks/shell/benign_commands.json \
  --max-cases-per-category 5 \
  --result-json ./artifacts/code_eval/manual_result.json \
  --report-md ./artifacts/code_eval/manual_report.md
```

`--mode` 支持：

- `baseline`
- `manual`
- `generated`

### 3.4 导出论文表格

```bash
uv run python scripts/export_paper_tables.py \
  --result-json ./artifacts/code_eval/manual_result.json \
  --output-md ./artifacts/code_eval/table_manual.md
```

### 3.5 运行 Shell model-in-loop 实验

**heuristic 后端**（默认，无需 API 密钥）：

```bash
uv run python scripts/run_agent_experiment.py \
  --backend heuristic \
  --shell-kb ./data/uca/shell/shell_kb.json \
  --risky-json ./benchmarks/RedCode-Exec/bash2text_dataset_json \
  --benign-json ./benchmarks/shell/benign_commands.json \
  --result-json ./artifacts/shell_eval/model_in_loop_result.json \
  --report-md ./artifacts/shell_eval/model_in_loop_report.md
```

**可选 LLM 后端（支持自定义端点）**：

```bash
uv run python scripts/run_agent_experiment.py \
  --backend model --model gpt-4o-mini \
  --api-base-url https://your-provider.example/v1 \
  --api-key-env OPENAI_API_KEY \
  --risky-json ./benchmarks/RedCode-Exec/bash2text_dataset_json \
  --benign-json ./benchmarks/shell/benign_commands.json \
  --result-json ./artifacts/shell_eval/model_result.json \
  --report-md ./artifacts/shell_eval/model_report.md
```

参数说明：

| 参数 | 说明 | 默认 |
|------|------|------|
| `--backend` | `heuristic`（规则）或 `model`（LLM） | `heuristic` |
| `--model` | 模型名称 | `gpt-4o-mini` |
| `--api-base-url` | OpenAI 兼容 API 端点（可选） | 空（官方默认） |
| `--api-key-env` | API Key 环境变量名 | `OPENAI_API_KEY` |
| `--shell-kb` | UCA 知识库路径（仅 heuristic） | `data/uca/shell/shell_kb.json` |
| `--risky-json` | 风险样本路径（JSON 文件或 JSON 目录） | 必填 |
| `--benign-json` | 良性样本路径（JSON 文件或 JSON 目录） | 可选 |
| `--result-json` | 结果输出路径 | 必填 |
| `--report-md` | 报告输出路径 | 必填 |

**最少可运行示例**（仅 heuristic，无 benign）：

```bash
uv run python scripts/run_agent_experiment.py \
  --risky-json ./benchmarks/RedCode-Exec/bash2text_dataset_json \
  --result-json ./artifacts/shell_eval/out.json \
  --report-md ./artifacts/shell_eval/out.md
```

### 3.6 Docker 沙盒复现实验

```bash
docker compose -f docker/docker-compose.yml build
docker compose -f docker/docker-compose.yml run --rm agentspec
```

---

## 4. 开发流程（本分支约定）

- 包管理与运行：统一使用 `uv`
- 测试框架：统一 `pytest`
- 提交规范：`feat|test|docs|chore(scope): message`
- 原则：小步提交、每个增量可验证、每个模块都有测试和文档

常用命令：

```bash
uv run pytest
uv run pytest -k compiler
uv run python scripts/verify_dataset.py --redcode-root <path>
```

---

## 5. 模块说明

### 5.1 UCA 模型层

- 位置：`src/agentspec_codegen/uca`
- 职责：
  - 定义 UCA 数据结构（Pydantic）
  - 校验 `risk_type <-> MITRE tactic` 一致性
  - 读写知识库 JSON

### 5.2 规则编译层

- 位置：`src/agentspec_codegen/compiler`
- 职责：
  - 从 UCA 生成 deterministic `.spec`
  - 提供 risk 到 predicate 的默认映射
  - 支持 golden 回归

### 5.3 运行时执行层

- 位置：`src/interpreter.py`、`src/controlled_agent_excector.py`、`src/agentspec_codegen/runtime`
- 职责：
  - 规则触发与谓词求值
  - predicate cache
  - 审计记录（rule/event/action/result/detail）
  - Shell 域：shellcheck 诊断可并入 `detail`，供审计追溯

### 5.4 Shell/OS 感知层

- 位置：`src/agentspec_codegen/shell_parser`、`src/agentspec_codegen/predicates`、`src/rules/manual/shell.py`
- 职责：
  - 解析 shell 命令并提取风险标志
  - **shellcheck 诊断**：`shellcheck_wrapper` 对命令做静态分析，结果可并入运行时审计的 `detail` 字段；未安装 shellcheck 时优雅降级（`available=False`）
  - 路径敏感性、权限变更、网络目标等 OS 上下文判定
  - 为运行时解释器提供可审计的 shell predicate

### 5.5 评估层

- 位置：`src/agentspec_codegen/eval`、`scripts/run_code_experiment.py`
- 职责：
  - 计算拦截率、误报率、完成率、平均开销
  - 输出 `json + markdown`

---

## 6. 文档索引

- 架构：`docs/architecture.md`
- 开发：`docs/development.md`
- 测试：`docs/testing.md`
- UCA：`docs/uca-model.md`
- 编译器：`docs/rule-compiler.md`
- 运行时：`docs/runtime-guard.md`
- Shell 运行时：`docs/shell-runtime.md`
- STPA：`docs/stpa-analysis.md`
- 控制环：`docs/stpa/cua-control-loop.md`
- 语义映射：`docs/semantic-mapping.md`
- 实验：`docs/experiments/code-domain.md`
- 发布检查：`docs/release-checklist.md`
- 已知限制：`docs/limitations.md`

---

## 7. 常见问题

### Q1: 为什么不直接提交 RedCode 数据？

A: 分支遵循“仓库轻量与合规”策略，只提交数据脚本和校验逻辑，不提交大体积基准数据与密钥。

### Q2: 为什么没有 OSWorld/AV/embodied？

A: 当前里程碑聚焦开题要求中的代码+Shell 安全闭环，先保证可测、可复现、可审计，再考虑扩展到其它域。

### Q3: 如何新增风险类别？

A:

1. 在 `UcaRiskType` 中增加风险类型  
2. 更新 `ATTACK_TACTIC_TO_RISKS` 映射  
3. 更新编译器默认映射  
4. 新增单元测试、golden 测试和文档说明

### Q4: shellcheck 未安装会怎样？

A: `shellcheck_wrapper` 会优雅降级，返回 `available=False`、`diagnostics=[]`，不会抛错。若需完整 shellcheck 诊断并入审计，请安装：`apt install shellcheck`（Debian/Ubuntu）或 `brew install shellcheck`（macOS）。

### Q5: 使用 `--backend model` 时报错缺少 API 密钥？

A: 默认读取 `OPENAI_API_KEY`。如果服务商使用不同变量名，可通过 `--api-key-env` 指定，例如：
`--api-key-env VENDOR_API_KEY`。自定义端点通过 `--api-base-url` 配置（OpenAI 兼容接口）。

---

## 8. 引用

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

