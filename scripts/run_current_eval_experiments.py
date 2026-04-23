from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from scripts.run_agent_experiment import run_model_in_loop
    from scripts.run_code_eval_suite import run_suite
except ModuleNotFoundError:
    from run_agent_experiment import run_model_in_loop
    from run_code_eval_suite import run_suite


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def run_current_eval(
    *,
    redcode_code_root: Path,
    redcode_shell_root: Path,
    code_benign_json: Path,
    shell_benign_json: Path,
    output_dir: Path,
    include_generated: bool,
    generated_code_kb: Path | None,
) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    code_output = output_dir / "code"
    shell_output = output_dir / "shell"
    code_results = run_suite(
        redcode_root=redcode_code_root,
        benign_json=code_benign_json,
        output_dir=code_output,
        max_cases_per_category=None,
        code_kb=Path("data/uca/code/sample_kb.json"),
        include_generated=include_generated,
        generated_code_kb=generated_code_kb,
        auto_generate_rules=False,
        max_gen_categories=None,
        gen_samples_per_category=None,
        model="gpt-4o-mini",
        api_base_url=None,
        api_key_env="OPENAI_API_KEY",
    )
    shell_result = run_model_in_loop(
        shell_kb_path=Path("data/uca/shell/shell_kb.json"),
        risky_json=redcode_shell_root,
        benign_json=shell_benign_json,
        artifact_root=shell_output / "spec_runtime",
    )
    _write_json(shell_output / "spec_runtime_result.json", shell_result)
    summary = {
        "code": code_results,
        "shell": shell_result,
    }
    _write_json(output_dir / "current_eval_summary.json", summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Run current-eval experiments with balanced benign sets.")
    parser.add_argument(
        "--redcode-code-root",
        type=Path,
        default=Path("benchmarks/RedCode-Exec/py2text_dataset_json"),
    )
    parser.add_argument(
        "--redcode-shell-root",
        type=Path,
        default=Path("benchmarks/RedCode-Exec/bash2text_dataset_json"),
    )
    parser.add_argument(
        "--code-benign-json",
        type=Path,
        default=Path("benchmarks/current_eval/code_safe_equal_mbpp.json"),
    )
    parser.add_argument(
        "--shell-benign-json",
        type=Path,
        default=Path("benchmarks/current_eval/shell_safe_equal_shellbench.json"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("artifacts/current_eval"),
    )
    parser.add_argument("--include-generated", action="store_true")
    parser.add_argument("--generated-code-kb", type=Path, required=False, default=None)
    args = parser.parse_args()
    summary = run_current_eval(
        redcode_code_root=args.redcode_code_root,
        redcode_shell_root=args.redcode_shell_root,
        code_benign_json=args.code_benign_json,
        shell_benign_json=args.shell_benign_json,
        output_dir=args.output_dir,
        include_generated=args.include_generated,
        generated_code_kb=args.generated_code_kb,
    )
    print(f"output_dir={args.output_dir}")
    print(f"code_modes={','.join(sorted(summary['code'].keys()))}")
    print(f"shell_total_cases={summary['shell']['metrics']['total_cases']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
