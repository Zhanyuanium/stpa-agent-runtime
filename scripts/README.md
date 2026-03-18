# Scripts

- `fetch_redcode.ps1` / `fetch_redcode.sh`: fetch benchmark data (not committed).
- `verify_dataset.py`: validate risky and optional benign datasets.
- `run_code_experiment.py`: run baseline/manual/generated heuristic experiments.
- `run_agent_experiment.py`: run model-in-loop shell enforcement experiments.
  - `--backend heuristic`: deterministic rule-based enforcement (default).
  - `--backend model`: LLM-based risk judgment; requires `OPENAI_API_KEY`; use `--provider` and `--model` to configure.
- `export_paper_tables.py`: export markdown table from result json.
