from __future__ import annotations

import argparse
import json
from pathlib import Path


def render_markdown_table(result: dict) -> str:
    m = result["metrics"]
    return (
        "| mode | total | interception | false_positive | completion | overhead_ms |\n"
        "|---|---:|---:|---:|---:|---:|\n"
        f"| {result['mode']} | {m['total_cases']} | {m['interception_rate']:.4f} | "
        f"{m['false_positive_rate']:.4f} | {m['task_completion_rate']:.4f} | {m['avg_overhead_ms']:.2f} |\n"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Export experiment result to paper-ready table.")
    parser.add_argument("--result-json", required=True, type=Path)
    parser.add_argument("--output-md", required=True, type=Path)
    args = parser.parse_args()

    result = json.loads(args.result_json.read_text(encoding="utf-8"))
    table = render_markdown_table(result)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(table, encoding="utf-8")
    print(f"table_md={args.output_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
