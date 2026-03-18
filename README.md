# AgentSpec (Code Domain Branch)

本分支是毕业设计实现分支，目标是围绕开题报告完成 **AgentSpec 代码域闭环**：

- 离线分析层：`STPA/UCA -> 结构化知识库`
- 规则生成层：`UCA -> AgentSpec DSL (.spec)`
- 在线执行层：`运行时拦截、缓存、审计`
- 实验评估层：`baseline/manual/generated` 三模式评测

本分支**不包含 OSWorld，不包含 embodied/AV 方向实现**，以代码域（RedCode-Exec 风险类别）为唯一目标。

---

## 1. 项目结构

```text
.
├─ src/
│  ├─ agentspec_codegen/
│  │  ├─ uca/          # UCA 模型、MITRE 映射、读写
│  │  ├─ compiler/     # UCA -> .spec 编译器
│  │  ├─ runtime/      # 运行时缓存与审计
│  │  └─ eval/         # 评估指标计算
│  ├─ controlled_agent_excector.py
│  ├─ interpreter.py
│  ├─ enforcement.py
│  └─ rules/manual/
│     ├─ pythonrepl.py
│     └─ table.py
├─ data/uca/code/
│  └─ sample_kb.json
├─ scripts/
│  ├─ fetch_redcode.ps1
│  ├─ fetch_redcode.sh
│  ├─ verify_dataset.py
│  ├─ run_code_experiment.py
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

### 3.3 运行代码域实验

```bash
uv run python scripts/run_code_experiment.py \
  --mode manual \
  --redcode-root ./benchmarks/RedCode-Exec/py2text_dataset_json \
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

### 5.4 评估层

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
- 实验：`docs/experiments/code-domain.md`
- 发布检查：`docs/release-checklist.md`
- 已知限制：`docs/limitations.md`

---

## 7. 常见问题

### Q1: 为什么不直接提交 RedCode 数据？

A: 分支遵循“仓库轻量与合规”策略，只提交数据脚本和校验逻辑，不提交大体积基准数据与密钥。

### Q2: 为什么只做代码域？

A: 这是本阶段里程碑，先完成“可测、可复现、可写论文”的代码域闭环，再按计划扩展到其它域。

### Q3: 如何新增风险类别？

A:

1. 在 `UcaRiskType` 中增加风险类型  
2. 更新 `ATTACK_TACTIC_TO_RISKS` 映射  
3. 更新编译器默认映射  
4. 新增单元测试、golden 测试和文档说明

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

