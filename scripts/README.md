# Scripts

- `fetch_redcode.ps1` / `fetch_redcode.sh`: fetch benchmark data (not committed).
- `verify_dataset.py`: validate risky and optional benign datasets.
- `run_code_experiment.py`: run code-domain baseline/manual/generated experiments.
  - `manual`: category-specific predicates (`index1`..`index25`).
  - `generated`: supports external `--generated-rules-json` (category -> predicates).
- `run_code_eval_suite.py`: one-command runner for code-domain outputs.
  - produces `baseline/manual/(optional generated)` result + report + table + category table.
  - optional `--include-generated` + `--generated-rules-json`, or `--auto-generate-rules`.
- `generate_code_rules.py`: generate low-cost category rules for RQ2-style evaluation.
  - 1:9 split per category; outputs `generated_rules.json` and `split_manifest.json`.
  - supports OpenAI-compatible endpoint via `--api-base-url` and API key env via `--api-key-env`.
- `run_agent_experiment.py`: run model-in-loop shell enforcement experiments.
  - `--backend heuristic`: deterministic rule-based enforcement (default).
  - `--backend model`: LLM-based risk judgment; supports custom OpenAI-compatible endpoint via `--api-base-url`, model via `--model`, and key env via `--api-key-env` (default `OPENAI_API_KEY`).
- `export_paper_tables.py`: export overview markdown table and optional Table3-like category table from result json.
