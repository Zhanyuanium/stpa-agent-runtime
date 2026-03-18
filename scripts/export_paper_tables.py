from __future__ import annotations

import argparse
import json
from pathlib import Path


def render_markdown_table(result: dict) -> str:
    m = result["metrics"]
    table = (
        "| mode | total | interception | false_positive | completion | overhead_ms |\n"
        "|---|---:|---:|---:|---:|---:|\n"
        f"| {result['mode']} | {m['total_cases']} | {m['interception_rate']:.4f} | "
        f"{m['false_positive_rate']:.4f} | {m['task_completion_rate']:.4f} | {m['avg_overhead_ms']:.2f} |\n"
    )
    runtime_source = result.get("runtime_source")
    if runtime_source:
        table += f"\n<!-- runtime_source: {runtime_source} -->\n"
    return table


def render_category_table(result: dict) -> str:
    rows = result.get("metrics_by_category") or []
    if not rows:
        return ""
    lines = [
        "| category | inv | vio | pass | enforced_rate |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            f"| {row['category']} | {row['inv']} | {row['vio']} | {row['pass_count']} | {row['enforced_rate']:.4f} |"
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Export experiment result to paper-ready table.")
    parser.add_argument("--result-json", required=True, type=Path)
    parser.add_argument("--output-md", required=True, type=Path)
    parser.add_argument(
        "--output-category-md",
        required=False,
        type=Path,
        help="Optional output path for Table3-like category breakdown.",
    )
    args = parser.parse_args()

    result = json.loads(args.result_json.read_text(encoding="utf-8"))
    table = render_markdown_table(result)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(table, encoding="utf-8")
    print(f"table_md={args.output_md}")
    if args.output_category_md and result.get("metrics_by_category"):
        category_table = render_category_table(result)
        args.output_category_md.parent.mkdir(parents=True, exist_ok=True)
        args.output_category_md.write_text(category_table, encoding="utf-8")
        print(f"category_table_md={args.output_category_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
