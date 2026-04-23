# AgentSpec (Code + Shell, Strict Spec-Runtime)

本分支聚焦你的开题目标：将实验链路收敛为可审计、可复现、可扩展的严格运行时路径。

核心原则：

- 唯一主链：`UCA -> .spec -> Rule.from_text -> RuleInterpreter -> enforce`
- Code 与 Shell 统一产物契约：每次运行都输出 `01~05` 中间态
- Shell 审计必须并入 `shellcheck` 诊断（含摘要与原始诊断）
- 默认全量规模（不再默认小样本截断），采样参数仅用于调试
- Manual KB 默认覆盖 RedCode-Exec 风险类别（index1~index25）
- Generated 采用“多谓词组 + 双轨 enforcement（LLM建议 + 规则裁决）”

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

默认使用 `data/uca/code/sample_kb.json`（已覆盖 RedCode-Exec `index1~index25` 风险类别）。

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

Generated 规则具备以下特征：

- 每个类别可生成多个谓词组（对应多个 UCA 条目）
- 输出 `llm_enforcement_suggestion`（`skip/stop`）
- 运行时应用确定性 `final_enforcement` 裁决，并记录冲突审计

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

---

## 13. Owner-Harm 融合实验（新增）

最小流程：

1) 生成 code 域 baseline/manual/generated（含 owner-harm 分组）  
`uv run python scripts/run_code_eval_suite.py --redcode-root ./benchmarks/RedCode-Exec/py2text_dataset_json --benign-json ./benchmarks/shell/benign_commands.json --output-dir ./artifacts/owner_harm_eval/code_baselines --include-generated --generated-code-kb ./data/uca/code/sample_kb.json`

2) 运行 post-audit verifier（gate+verifier）  
`uv run python scripts/run_post_audit_verifier.py --gate-result-json ./artifacts/owner_harm_eval/code_baselines/manual_result.json --output-json ./artifacts/owner_harm_eval/code_baselines/manual_post_audit_result.json --output-md ./artifacts/owner_harm_eval/code_baselines/manual_post_audit_report.md --context-mode full`

3) 跑统一入口与 SSDG 消融（full/stripped/structured_goal）  
`uv run python scripts/run_owner_harm_eval.py --code-gate-result-json ./artifacts/owner_harm_eval/code_baselines/manual_result.json --output-dir ./artifacts/owner_harm_eval/unified --run-ssdg-ablation`

4) 导出论文可引用汇总  
`uv run python scripts/export_owner_harm_report.py --baseline-dir ./artifacts/owner_harm_eval/code_baselines --unified-summary-json ./artifacts/owner_harm_eval/unified/owner_harm_eval_summary.json --output-md ./reports/owner-harm-integration-report.md`
