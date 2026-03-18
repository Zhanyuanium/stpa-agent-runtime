# Code-Domain Experiment Reproduction

## Goal
- Reproduce AgentSpec-style code safety evaluation for risky code execution.

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

## Planned Modes
- Baseline (no rules)
- Manual rules
- Generated rules

## Primary Metrics
- Risk interception rate
- False positive rate
- Task completion rate
- Mean runtime overhead (ms)

## Run Experiments
```bash
uv run python scripts/run_code_experiment.py \
  --mode manual \
  --redcode-root ./benchmarks/RedCode-Exec/py2text_dataset_json \
  --max-cases-per-category 5 \
  --result-json ./artifacts/code_eval/manual_result.json \
  --report-md ./artifacts/code_eval/manual_report.md
```
