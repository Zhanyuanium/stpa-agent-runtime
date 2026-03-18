from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from agentspec_codegen.eval import evaluate_cases, summarize_to_markdown
from rules.manual.pythonrepl import (
    involve_bash_rc,
    request_untrusted_source,
    submit_post_request,
    write_to_io,
)


def detect_risk(code: str) -> bool:
    checks = (submit_post_request, request_untrusted_source, write_to_io, involve_bash_rc)
    return any(fn("", code, []) for fn in checks)


def should_block(mode: str, code: str) -> bool:
    if mode == "baseline":
        return False
    if mode == "manual":
        return detect_risk(code)
    if mode == "generated":
        # Slightly more conservative than manual in this phase.
        return detect_risk(code) or ("os.system" in code and "curl" in code)
    raise ValueError(f"unsupported mode: {mode}")


def load_cases(redcode_root: Path, max_cases_per_category: int) -> list[dict]:
    cases: list[dict] = []
    for file in sorted(redcode_root.glob("index*_30_codes_full.json")):
        content = json.loads(file.read_text(encoding="utf-8"))
        for i, sample in enumerate(content[:max_cases_per_category]):
            code = sample.get("Code") or sample.get("code") or ""
            cases.append(
                {
                    "case_id": f"{file.stem}:{i}",
                    "code": code,
                    # RedCode-Exec split is risky by design in this phase.
                    "is_risky": True,
                }
            )
    return cases


def run(mode: str, redcode_root: Path, max_cases_per_category: int) -> dict:
    raw_cases = load_cases(redcode_root, max_cases_per_category=max_cases_per_category)
    scored: list[dict] = []
    for case in raw_cases:
        begin = time.perf_counter()
        blocked = should_block(mode, case["code"])
        elapsed_ms = (time.perf_counter() - begin) * 1000
        scored.append(
            {
                "case_id": case["case_id"],
                "is_risky": case["is_risky"],
                "blocked": blocked,
                "fulfilled": not blocked,
                "overhead_ms": round(elapsed_ms, 6),
            }
        )
    metrics = evaluate_cases(scored)
    return {"mode": mode, "metrics": metrics.to_dict(), "cases": scored}


def main() -> int:
    parser = argparse.ArgumentParser(description="Run code-domain AgentSpec experiment.")
    parser.add_argument("--mode", choices=["baseline", "manual", "generated"], required=True)
    parser.add_argument("--redcode-root", type=Path, required=True)
    parser.add_argument("--max-cases-per-category", type=int, default=5)
    parser.add_argument("--result-json", type=Path, required=True)
    parser.add_argument("--report-md", type=Path, required=True)
    args = parser.parse_args()

    result = run(
        mode=args.mode,
        redcode_root=args.redcode_root,
        max_cases_per_category=args.max_cases_per_category,
    )
    args.result_json.parent.mkdir(parents=True, exist_ok=True)
    args.report_md.parent.mkdir(parents=True, exist_ok=True)
    args.result_json.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    args.report_md.write_text(
        summarize_to_markdown(args.mode, evaluate_cases(result["cases"])),
        encoding="utf-8",
    )
    print(f"result_json={args.result_json}")
    print(f"report_md={args.report_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
