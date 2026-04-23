# Code-Domain Experiment Reproduction

## Goal
- Reproduce AgentSpec code-domain evaluation for RQ1/RQ2 with reproducible scripts.
- Ensure code-domain RQ1/RQ2 use the strict runtime chain: `UCA -> .spec -> RuleInterpreter`.

## Data Policy
- Do not commit large benchmark data.
- Only commit fetch/verify scripts and minimal sample configs.

## Dataset Preparation
1. Run helper:
   - Windows: `pwsh ./scripts/fetch_redcode.ps1`
   - Linux/macOS: `bash ./scripts/fetch_redcode.sh`
2. Place RedCode files under `benchmarks/RedCode-Exec/py2text_dataset_json`.
3. Verify layout:
   - `uv run python scripts/verify_dataset.py --redcode-root ./benchmarks/RedCode-Exec/py2text_dataset_json`
   - With benign set:
     - `uv run python scripts/verify_dataset.py --redcode-root ./benchmarks/RedCode-Exec/py2text_dataset_json --benign-json ./benchmarks/shell/benign_commands.json`

## Evaluation Modes
- Baseline (no rules)
- Manual rules (RedCode-Exec category-covered UCA KB -> compiled `.spec` -> runtime enforcement)
- Generated rules (LLM-generated multi-predicate UCA KB -> compiled `.spec` -> runtime enforcement)
- Generated uses dual-track enforcement lineage:
  - `llm_enforcement_suggestion` from model output
  - deterministic `final_enforcement` from runtime policy
  - conflicts are persisted in artifacts and result summary
- All modes persist staged artifacts for audit:
  - `01_uca_loaded.json`
  - `02_compiled_specs/*.spec`
  - `02_compiled_manifest.json`
  - `03_rules_parsed.json`
  - `04_check_traces/{case_id}.json`
  - `05_case_audits.jsonl`

## Primary Metrics
- Risk interception rate (= enforced rate)
- False positive rate
- Task completion rate
- Mean runtime overhead (ms)
- Category breakdown (Table3-like): `inv/vio/pass`

## Run RQ1 (Manual vs Baseline)
```bash
uv run python scripts/run_code_experiment.py \
  --mode manual \
  --redcode-root ./benchmarks/RedCode-Exec/py2text_dataset_json \
  --benign-json ./benchmarks/shell/benign_commands.json \
  --artifact-root ./artifacts/code_eval/manual \
  --result-json ./artifacts/code_eval/manual_result.json \
  --report-md ./artifacts/code_eval/manual_report.md
```

```bash
uv run python scripts/run_code_experiment.py \
  --mode baseline \
  --redcode-root ./benchmarks/RedCode-Exec/py2text_dataset_json \
  --benign-json ./benchmarks/shell/benign_commands.json \
  --artifact-root ./artifacts/code_eval/baseline \
  --result-json ./artifacts/code_eval/baseline_result.json \
  --report-md ./artifacts/code_eval/baseline_report.md
```

导出总览表 + 分类表：
```bash
uv run python scripts/export_paper_tables.py \
  --result-json ./artifacts/code_eval/manual_result.json \
  --output-md ./artifacts/code_eval/manual_table.md \
  --output-category-md ./artifacts/code_eval/manual_table_rq1.md
```

## Run RQ2 (Generated Rules)

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

再执行 generated 模式评估：
```bash
uv run python scripts/run_code_experiment.py \
  --mode generated \
  --redcode-root ./benchmarks/RedCode-Exec/py2text_dataset_json \
  --generated-code-kb ./artifacts/code_eval/generated_code_kb.json \
  --artifact-root ./artifacts/code_eval/generated \
  --result-json ./artifacts/code_eval/generated_result.json \
  --report-md ./artifacts/code_eval/generated_report.md
```

## Run Strict Spec-Runtime Shell Experiment
```bash
uv run python scripts/run_agent_experiment.py \
  --shell-kb ./data/uca/shell/shell_kb.json \
  --risky-json ./benchmarks/RedCode-Exec/bash2text_dataset_json \
  --benign-json ./benchmarks/shell/benign_commands.json \
  --artifact-root ./artifacts/shell_eval/spec_runtime \
  --result-json ./artifacts/shell_eval/spec_runtime_result.json \
  --report-md ./artifacts/shell_eval/spec_runtime_report.md
```

## Docker Sandbox
```bash
docker compose -f docker/docker-compose.yml build
docker compose -f docker/docker-compose.yml run --rm agentspec
```

## Owner-Harm 融合实验（新增）

### 1) 生成 code 域 gate-only 基线（含 owner-harm 分组）
```bash
uv run python scripts/run_code_eval_suite.py \
  --redcode-root ./benchmarks/RedCode-Exec/py2text_dataset_json \
  --benign-json ./benchmarks/shell/benign_commands.json \
  --output-dir ./artifacts/owner_harm_eval/code_baselines \
  --include-generated \
  --generated-code-kb ./data/uca/code/sample_kb.json
```

### 2) 在 gate 结果上运行 deterministic post-audit verifier
```bash
uv run python scripts/run_post_audit_verifier.py \
  --gate-result-json ./artifacts/owner_harm_eval/code_baselines/manual_result.json \
  --output-json ./artifacts/owner_harm_eval/code_baselines/manual_post_audit_result.json \
  --output-md ./artifacts/owner_harm_eval/code_baselines/manual_post_audit_report.md \
  --context-mode full
```

### 3) 统一入口：current dataset + AgentHarm(可选) + SSDG 三条件
```bash
uv run python scripts/run_owner_harm_eval.py \
  --code-gate-result-json ./artifacts/owner_harm_eval/code_baselines/manual_result.json \
  --output-dir ./artifacts/owner_harm_eval/unified \
  --run-ssdg-ablation
```

若本地提供 AgentHarm 数据，可附加：
```bash
--run-agentharm --agentharm-root <path-to-agentharm-json-or-dir>
```

### 4) 导出论文汇总报告（含预估表）
```bash
uv run python scripts/export_owner_harm_report.py \
  --baseline-dir ./artifacts/owner_harm_eval/code_baselines \
  --unified-summary-json ./artifacts/owner_harm_eval/unified/owner_harm_eval_summary.json \
  --output-md ./reports/owner-harm-integration-report.md
```

## Current 测试集重建（MBPP + ShellBench）

### 1) 拉取外部数据（MBPP/ShellBench/AgentHarm）
```bash
uv run python scripts/fetch_external_benchmarks.py \
  --output-root ./benchmarks \
  --retries 3 \
  --sleep-seconds 3
```

### 2) 构建与 RedCode risky 等量的 safe 样本
```bash
uv run python scripts/build_current_eval_dataset.py \
  --redcode-code-root ./benchmarks/RedCode-Exec/py2text_dataset_json \
  --redcode-shell-root ./benchmarks/RedCode-Exec/bash2text_dataset_json \
  --mbpp-json ./benchmarks/MBPP/mbpp_code_samples.json \
  --shellbench-json ./benchmarks/ShellBench/shellbench_safe_commands.json \
  --output-dir ./benchmarks/current_eval
```

### 3) 运行 current 测试集实验（code + shell）
```bash
uv run python scripts/run_current_eval_experiments.py \
  --code-benign-json ./benchmarks/current_eval/code_safe_equal_mbpp.json \
  --shell-benign-json ./benchmarks/current_eval/shell_safe_equal_shellbench.json \
  --output-dir ./artifacts/current_eval \
  --include-generated \
  --generated-code-kb ./data/uca/code/sample_kb.json
```

### 4) 运行 current + AgentHarm 双测试集对比
```bash
uv run python scripts/run_owner_harm_eval.py \
  --code-gate-result-json ./artifacts/current_eval/code/manual_result.json \
  --output-dir ./artifacts/owner_harm_eval/dual_bench \
  --run-agentharm \
  --agentharm-root ./benchmarks/AgentHarm \
  --code-kb ./data/uca/code/sample_kb.json
```
