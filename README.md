# AgentSpec (Code + Shell, Strict Spec-Runtime)

本分支聚焦你的开题目标：将实验链路收敛为可审计、可复现、可扩展的严格运行时路径。

核心原则：

- 唯一主链：`UCA -> .spec -> Rule.from_text -> RuleInterpreter -> enforce`
- Code 与 Shell 统一产物契约：每次运行都输出 `01~05` 中间态
- Shell 审计必须并入 `shellcheck` 诊断（含摘要与原始诊断）
- 默认全量规模（不再默认小样本截断），采样参数仅用于调试

---

## 1. 项目目标

本仓库用于复现实验并支撑论文型开发流程，当前阶段覆盖：

- Code 域：RQ1（manual UCA）与 RQ2（generated UCA）
- Shell 域：严格 spec-runtime 防护评估

不在本阶段范围：

- OSWorld / embodied / AV 等其它域（后续阶段再引入）

---

## 2. 严格执行链路

每条规则都必须经过如下四步（Shell 额外第五步）：

1. 读取 UCA 风险条目（`UcaKnowledgeBase`）
2. 编译器将 UCA 生成 `.spec` 文本
3. 解释器解析 `.spec` 并逐条 `check` 求值
4. 根据 `enforce` 执行 `continue/skip/stop/user_inspection`
5. （Shell）收集 `shellcheck` 诊断并并入审计

---

## 3. 目录结构（关键模块）

```text
AgentSpec/
├─ data/
│  └─ uca/
│     ├─ code/sample_kb.json
│     └─ shell/shell_kb.json
├─ src/
│  ├─ agentspec_codegen/
│  │  ├─ compiler/           # UCA -> .spec 编译
│  │  ├─ uca/                # UCA 模型与读写
│  │  ├─ runtime/            # 审计模型与运行时上下文
│  │  ├─ shell_parser/       # shell 特征与 shellcheck 包装
│  │  └─ eval/               # 指标统计与报表
│  ├─ interpreter.py         # RuleInterpreter
│  └─ rules/manual/          # 谓词实现（由 .spec check 调用）
├─ scripts/
│  ├─ run_code_experiment.py
│  ├─ run_agent_experiment.py
│  ├─ run_code_eval_suite.py
│  ├─ generate_code_rules.py
│  ├─ export_paper_tables.py
│  └─ verify_dataset.py
├─ docs/
│  ├─ experiments/code-domain.md
│  ├─ shell-runtime.md
│  └─ limitations.md
└─ tests/
   ├─ unit/
   ├─ integration/
   └─ e2e/
```

---

## 4. 环境准备

### 4.1 Python + uv

建议 Python 3.11+，统一使用 `uv`：

```bash
uv sync
```

### 4.2 数据集准备

仅保留脚本与最小样例，不提交大体积上游基准数据。

- Code 风险样本：`benchmarks/RedCode-Exec/py2text_dataset_json`
- Shell 风险样本：`benchmarks/RedCode-Exec/bash2text_dataset_json`
- 良性样本：`benchmarks/shell/benign_commands.json`

校验命令：

```bash
uv run python scripts/verify_dataset.py --redcode-root ./benchmarks/RedCode-Exec/py2text_dataset_json
uv run python scripts/verify_dataset.py --redcode-root ./benchmarks/RedCode-Exec/py2text_dataset_json --benign-json ./benchmarks/shell/benign_commands.json
```

---

## 5. Code 域实验

### 5.1 RQ1（Manual UCA）

```bash
uv run python scripts/run_code_experiment.py \
  --mode manual \
  --redcode-root ./benchmarks/RedCode-Exec/py2text_dataset_json \
  --benign-json ./benchmarks/shell/benign_commands.json \
  --artifact-root ./artifacts/code_eval/manual \
  --result-json ./artifacts/code_eval/manual_result.json \
  --report-md ./artifacts/code_eval/manual_report.md
```

### 5.2 Baseline（无规则）

```bash
uv run python scripts/run_code_experiment.py \
  --mode baseline \
  --redcode-root ./benchmarks/RedCode-Exec/py2text_dataset_json \
  --benign-json ./benchmarks/shell/benign_commands.json \
  --artifact-root ./artifacts/code_eval/baseline \
  --result-json ./artifacts/code_eval/baseline_result.json \
  --report-md ./artifacts/code_eval/baseline_report.md
```

### 5.3 RQ2（Generated UCA）

先生成结构化 UCA KB：

```bash
uv run python scripts/generate_code_rules.py \
  --redcode-root ./benchmarks/RedCode-Exec/py2text_dataset_json \
  --model gpt-4o-mini \
  --api-base-url https://your-provider.example/v1 \
  --api-key-env OPENAI_API_KEY \
  --generated-code-kb-json ./artifacts/code_eval/generated_code_kb.json \
  --split-manifest-json ./artifacts/code_eval/split_manifest.json
```

再执行 generated 评估：

```bash
uv run python scripts/run_code_experiment.py \
  --mode generated \
  --redcode-root ./benchmarks/RedCode-Exec/py2text_dataset_json \
  --generated-code-kb ./artifacts/code_eval/generated_code_kb.json \
  --artifact-root ./artifacts/code_eval/generated \
  --result-json ./artifacts/code_eval/generated_result.json \
  --report-md ./artifacts/code_eval/generated_report.md
```

### 5.4 一键运行 RQ1/RQ2

```bash
uv run python scripts/run_code_eval_suite.py \
  --redcode-root ./benchmarks/RedCode-Exec/py2text_dataset_json \
  --benign-json ./benchmarks/shell/benign_commands.json \
  --output-dir ./artifacts/code_eval \
  --include-generated \
  --generated-code-kb ./artifacts/code_eval/generated_code_kb.json
```

---

## 6. Shell 域实验（Strict Spec-Runtime）

```bash
uv run python scripts/run_agent_experiment.py \
  --shell-kb ./data/uca/shell/shell_kb.json \
  --risky-json ./benchmarks/RedCode-Exec/bash2text_dataset_json \
  --benign-json ./benchmarks/shell/benign_commands.json \
  --artifact-root ./artifacts/shell_eval/spec_runtime \
  --result-json ./artifacts/shell_eval/spec_runtime_result.json \
  --report-md ./artifacts/shell_eval/spec_runtime_report.md
```

说明：

- 本分支 Shell 路径仅保留 strict spec-runtime，不提供 LLM 直判后端。
- shellcheck 诊断将并入 `05_case_audits.jsonl`。

---

## 7. 可审计产物契约（01~05）

无论 Code 或 Shell，实验运行后都应出现：

- `01_uca_loaded.json`：UCA 读入结果
- `02_compiled_specs/*.spec`：编译出的规则文本
- `02_compiled_manifest.json`：`rule_id/uca_id/predicates/spec_path` 映射
- `03_rules_parsed.json`：`Rule.from_text` 解析结果
- `04_check_traces/{case_id}.json`：逐规则 trigger/check/enforce 轨迹
- `05_case_audits.jsonl`：按 case 的审计流（Shell 含 shellcheck 字段）

结果文件至少包含：

- `runtime_source`
- `rule_source`
- `compiled_rule_count`
- `artifact_root`

---

## 8. 指标说明

常用指标：

- `interception_rate`：风险样本被拦截比例
- `false_positive_rate`：良性样本误拦截比例
- `task_completion_rate`：任务完成率
- `avg_overhead_ms`：平均运行时开销
- `enforced_rate`：被 enforce（通常是 skip/stop）的样本占比（可按总体或分类统计）

---

## 9. 测试

全量：

```bash
uv run pytest
```

按层级：

```bash
uv run pytest tests/unit
uv run pytest tests/integration
uv run pytest tests/e2e
```

---

## 10. 参数约束与默认行为

- 默认全量：不传采样参数即跑全量可用样本/类别。
- 可选采样参数（仅调试用）：
  - `run_code_experiment.py`: `--max-cases-per-category`
  - `generate_code_rules.py`: `--max-categories`、`--samples-per-category`
  - `run_code_eval_suite.py`: `--max-cases-per-category`、`--max-gen-categories`、`--gen-samples-per-category`
- `generated` 模式强约束：必须提供 `--generated-code-kb`。

---

## 11. 已知限制

详见 `docs/limitations.md`。当前关键点：

- Shell 仅 strict spec-runtime，不提供 LLM 直判路径。
- shell parser 对非常规语法有降级解析路径（保证稳定，不保证语义完备）。

---

## 12. 参考文献

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
  --artifact-root ./artifacts/code_eval/manual \
  --result-json ./artifacts/code_eval/manual_result.json \
  --report-md ./artifacts/code_eval/manual_report.md
```

`--mode` 支持：

- `baseline`
- `manual`
- `generated`

每次运行都会在 `--artifact-root`（默认 `artifacts/code_eval/<mode>`）写入可审计中间态：

- `01_uca_loaded.json`
- `02_compiled_specs/*.spec`
- `02_compiled_manifest.json`
- `03_rules_parsed.json`
- `04_check_traces/{case_id}.json`
- `05_case_audits.jsonl`

### 3.4 导出论文表格

```bash
uv run python scripts/export_paper_tables.py \
  --result-json ./artifacts/code_eval/manual_result.json \
  --output-md ./artifacts/code_eval/table_manual.md \
  --output-category-md ./artifacts/code_eval/table_manual_rq1.md
```

### 3.4.1 一键运行 code 域 RQ1/RQ2 输出（推荐）

仅跑 RQ1（baseline + manual）：

```bash
uv run python scripts/run_code_eval_suite.py \
  --redcode-root ./benchmarks/RedCode-Exec/py2text_dataset_json \
  --benign-json ./benchmarks/shell/benign_commands.json \
  --output-dir ./artifacts/code_eval
```

包含 RQ2 generated（使用已有规则文件）：

```bash
uv run python scripts/run_code_eval_suite.py \
  --redcode-root ./benchmarks/RedCode-Exec/py2text_dataset_json \
  --benign-json ./benchmarks/shell/benign_commands.json \
  --output-dir ./artifacts/code_eval \
  --include-generated \
  --generated-code-kb ./artifacts/code_eval/generated_code_kb.json
```

### 3.5 RQ2 生成规则实验（code 域）

先生成结构化 UCA 知识库（默认全量类别/样本）：

```bash
uv run python scripts/generate_code_rules.py \
  --redcode-root ./benchmarks/RedCode-Exec/py2text_dataset_json \
  --model gpt-4o-mini \
  --api-base-url https://your-provider.example/v1 \
  --api-key-env OPENAI_API_KEY \
  --generated-code-kb-json ./artifacts/code_eval/generated_code_kb.json \
  --split-manifest-json ./artifacts/code_eval/split_manifest.json
```

再执行 generated 模式：

```bash
uv run python scripts/run_code_experiment.py \
  --mode generated \
  --redcode-root ./benchmarks/RedCode-Exec/py2text_dataset_json \
  --generated-code-kb ./artifacts/code_eval/generated_code_kb.json \
  --artifact-root ./artifacts/code_eval/generated \
  --result-json ./artifacts/code_eval/generated_result.json \
  --report-md ./artifacts/code_eval/generated_report.md
```

### 3.6 运行 Shell 严格 spec-runtime 实验

```bash
uv run python scripts/run_agent_experiment.py \
  --shell-kb ./data/uca/shell/shell_kb.json \
  --risky-json ./benchmarks/RedCode-Exec/bash2text_dataset_json \
  --benign-json ./benchmarks/shell/benign_commands.json \
  --artifact-root ./artifacts/shell_eval/spec_runtime \
  --result-json ./artifacts/shell_eval/spec_runtime_result.json \
  --report-md ./artifacts/shell_eval/spec_runtime_report.md
```

参数说明：

| 参数 | 说明 | 默认 |
|------|------|------|
| `--shell-kb` | UCA 知识库路径（严格 spec-runtime） | `data/uca/shell/shell_kb.json` |
| `--risky-json` | 风险样本路径（JSON 文件或 JSON 目录） | 必填 |
| `--benign-json` | 良性样本路径（JSON 文件或 JSON 目录） | 可选 |
| `--artifact-root` | 01~05 可审计中间态输出根目录 | `artifacts/shell_eval/spec_runtime` |
| `--result-json` | 结果输出路径 | 必填 |
| `--report-md` | 报告输出路径 | 必填 |

**最少可运行示例**（仅 heuristic，无 benign）：

```bash
uv run python scripts/run_agent_experiment.py \
  --risky-json ./benchmarks/RedCode-Exec/bash2text_dataset_json \
  --result-json ./artifacts/shell_eval/out.json \
  --report-md ./artifacts/shell_eval/out.md
```

### 3.7 Docker 沙盒复现实验

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

### Q5: Shell 实验是否支持 LLM 直判后端？

A: 当前不支持。为保证“UCA->.spec->解释执行”主链纯度，Shell 实验仅保留 strict spec-runtime 路径。

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

