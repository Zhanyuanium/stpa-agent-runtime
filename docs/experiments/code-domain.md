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
- Manual rules (UCA KB -> compiled `.spec` -> runtime enforcement)
- Generated rules (LLM-generated UCA KB -> compiled `.spec` -> runtime enforcement)

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
  --max-cases-per-category 30 \
  --result-json ./artifacts/code_eval/manual_result.json \
  --report-md ./artifacts/code_eval/manual_report.md
```

```bash
uv run python scripts/run_code_experiment.py \
  --mode baseline \
  --redcode-root ./benchmarks/RedCode-Exec/py2text_dataset_json \
  --benign-json ./benchmarks/shell/benign_commands.json \
  --max-cases-per-category 30 \
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

## Run RQ2 (Low-Cost Generated Rules)

先生成结构化 UCA 知识库（1:9 split + 限成本）：
```bash
uv run python scripts/generate_code_rules.py \
  --redcode-root ./benchmarks/RedCode-Exec/py2text_dataset_json \
  --max-categories 5 \
  --samples-per-category 10 \
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
  --max-cases-per-category 10 \
  --result-json ./artifacts/code_eval/generated_result.json \
  --report-md ./artifacts/code_eval/generated_report.md
```

## Run Model-in-Loop Shell Experiment
```bash
uv run python scripts/run_agent_experiment.py \
  --shell-kb ./data/uca/shell/shell_kb.json \
  --risky-json ./benchmarks/RedCode-Exec/bash2text_dataset_json \
  --benign-json ./benchmarks/shell/benign_commands.json \
  --result-json ./artifacts/shell_eval/model_in_loop_result.json \
  --report-md ./artifacts/shell_eval/model_in_loop_report.md
```

## Docker Sandbox
```bash
docker compose -f docker/docker-compose.yml build
docker compose -f docker/docker-compose.yml run --rm agentspec
```
