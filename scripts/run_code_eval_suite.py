from __future__ import annotations

import argparse
import json
from pathlib import Path

from agentspec_codegen.eval import evaluate_cases, summarize_to_markdown

# Support both invocation styles:
# 1) `uv run python scripts/run_code_eval_suite.py ...`
# 2) `uv run python -m scripts.run_code_eval_suite ...`
try:
    from scripts.export_paper_tables import render_category_table, render_markdown_table, render_owner_harm_table
    from scripts.generate_code_rules import generate_rules
    from scripts.run_code_experiment import run
except ModuleNotFoundError:
    from export_paper_tables import render_category_table, render_markdown_table, render_owner_harm_table
    from generate_code_rules import generate_rules
    from run_code_experiment import run


def _write_mode_outputs(result: dict, output_dir: Path, mode: str) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    result_json = output_dir / f"{mode}_result.json"
    report_md = output_dir / f"{mode}_report.md"
    table_md = output_dir / f"{mode}_table.md"
    table_category_md = output_dir / f"{mode}_table_rq1.md"
    table_owner_harm_md = output_dir / f"{mode}_table_owner_harm.md"

    result_json.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    report_md.write_text(summarize_to_markdown(mode, evaluate_cases(result["cases"])), encoding="utf-8")
    table_md.write_text(render_markdown_table(result), encoding="utf-8")
    category_table = render_category_table(result)
    if category_table:
        table_category_md.write_text(category_table, encoding="utf-8")
    owner_harm_table = render_owner_harm_table(result)
    if owner_harm_table:
        table_owner_harm_md.write_text(owner_harm_table, encoding="utf-8")


def run_suite(
    *,
    redcode_root: Path,
    benign_json: Path | None,
    output_dir: Path,
    max_cases_per_category: int | None,
    code_kb: Path,
    include_generated: bool,
    generated_code_kb: Path | None,
    auto_generate_rules: bool,
    max_gen_categories: int | None,
    gen_samples_per_category: int | None,
    model: str,
    api_base_url: str | None,
    api_key_env: str,
) -> dict[str, dict]:
    results: dict[str, dict] = {}

    baseline = run(
        mode="baseline",
        redcode_root=redcode_root,
        max_cases_per_category=max_cases_per_category,
        benign_json=benign_json,
        code_kb=code_kb,
        artifact_root=output_dir / "baseline",
    )
    _write_mode_outputs(baseline, output_dir, "baseline")
    results["baseline"] = baseline

    manual = run(
        mode="manual",
        redcode_root=redcode_root,
        max_cases_per_category=max_cases_per_category,
        benign_json=benign_json,
        code_kb=code_kb,
        artifact_root=output_dir / "manual",
    )
    _write_mode_outputs(manual, output_dir, "manual")
    results["manual"] = manual

    if include_generated:
        kb_path = generated_code_kb
        if kb_path is None:
            kb_path = output_dir / "generated_code_kb.json"
        if auto_generate_rules:
            generated_kb, manifest = generate_rules(
                redcode_root=redcode_root,
                max_categories=max_gen_categories,
                samples_per_category=gen_samples_per_category,
                model=model,
                api_base_url=api_base_url,
                api_key_env=api_key_env,
            )
            kb_path.parent.mkdir(parents=True, exist_ok=True)
            kb_path.write_text(generated_kb.model_dump_json(indent=2, ensure_ascii=False), encoding="utf-8")
            (output_dir / "split_manifest.json").write_text(
                json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
            )
        generated_result = run(
            mode="generated",
            redcode_root=redcode_root,
            max_cases_per_category=max_cases_per_category,
            benign_json=benign_json,
            code_kb=code_kb,
            generated_code_kb=kb_path,
            artifact_root=output_dir / "generated",
        )
        _write_mode_outputs(generated_result, output_dir, "generated")
        results["generated"] = generated_result

    return results


def main() -> int:
    parser = argparse.ArgumentParser(
        description="One-command runner for code-domain RQ1/RQ2 experiment artifacts."
    )
    parser.add_argument("--redcode-root", type=Path, required=True)
    parser.add_argument("--benign-json", type=Path, required=False)
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts/code_eval"))
    parser.add_argument(
        "--max-cases-per-category",
        type=int,
        default=None,
        help="Optional cap per category. Default runs all available cases.",
    )
    parser.add_argument("--code-kb", type=Path, default=Path("data/uca/code/sample_kb.json"))
    parser.add_argument("--include-generated", action="store_true")
    parser.add_argument("--generated-code-kb", type=Path, default=None)
    parser.add_argument("--auto-generate-rules", action="store_true")
    parser.add_argument(
        "--max-gen-categories",
        type=int,
        default=None,
        help="Optional cap for generated-UCA categories. Default uses all categories.",
    )
    parser.add_argument(
        "--gen-samples-per-category",
        type=int,
        default=None,
        help="Optional cap for generation samples per category. Default uses all samples.",
    )
    parser.add_argument("--model", default="gpt-4o-mini")
    parser.add_argument("--api-base-url", default=None)
    parser.add_argument("--api-key-env", default="OPENAI_API_KEY")
    args = parser.parse_args()

    if args.auto_generate_rules and not args.include_generated:
        raise SystemExit("--auto-generate-rules requires --include-generated")

    results = run_suite(
        redcode_root=args.redcode_root,
        benign_json=args.benign_json,
        output_dir=args.output_dir,
        max_cases_per_category=args.max_cases_per_category,
        code_kb=args.code_kb,
        include_generated=args.include_generated,
        generated_code_kb=args.generated_code_kb,
        auto_generate_rules=args.auto_generate_rules,
        max_gen_categories=args.max_gen_categories,
        gen_samples_per_category=args.gen_samples_per_category,
        model=args.model,
        api_base_url=args.api_base_url,
        api_key_env=args.api_key_env,
    )
    print(f"modes={','.join(sorted(results.keys()))}")
    print(f"output_dir={args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
