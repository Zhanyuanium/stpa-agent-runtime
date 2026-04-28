# Code 域实验复现（RQ1/RQ2）

更多入口见 `docs/index.md`。本文仅记录**如何跑通**与**如何核对产物口径**。

## 1. 数据政策

- 上游数据不入库：仓库只提交脚本与最小样例配置（详见 `.gitignore`）。
- 你需要把 RedCode-Exec 放置到：
  - `benchmarks/RedCode-Exec/py2text_dataset_json`

校验布局：

```bash
uv run python scripts/verify_dataset.py --redcode-root ./benchmarks/RedCode-Exec/py2text_dataset_json
```

## 2. 运行模式

- **baseline**：不加载规则，作为对照
- **manual**：手工 UCA KB → 编译为 `.spec` → 严格运行时执行
- **generated**：模型生成 UCA KB → 编译为 `.spec` → 严格运行时执行（该模式依赖外部 LLM 配置）

三种模式都会落盘统一的 `01~05` 审计产物（见 `docs/runtime-guard.md`）。

## 3. 运行 RQ1（manual vs baseline）

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

## 4. 运行 RQ2（generated）

先生成结构化 UCA 知识库（默认全量类别/样本；LLM 相关参数以脚本帮助为准）：

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

## 5. 常见核对点

- **是否落盘了 `01~05`**：如果缺失，优先检查 `--artifact-root` 是否可写、以及数据路径是否正确。
- **指标口径**：以 `*_result.json` 为准；汇总表由 `export_paper_tables.py` 从结果 JSON 导出。

