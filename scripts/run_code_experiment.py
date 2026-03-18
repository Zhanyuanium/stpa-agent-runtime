from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from agentspec_codegen.eval import evaluate_cases, evaluate_cases_by_category, summarize_to_markdown
from rules.manual.pythonrepl import (
    checks as category_checks,
    involve_bash_rc,
    request_untrusted_source,
    submit_post_request,
    write_to_io,
)

CODE_PREDICATE_TABLE = {
    fn.__name__: fn for funcs in category_checks.values() for fn in funcs
}


def _extract_category_from_file(file: Path) -> str:
    return file.stem.split("_")[0]


def _load_generated_rules(path: Path | None) -> dict[str, list[str]]:
    if not path or not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("generated rules json must be an object: {category: [predicate_names...]}")
    normalized: dict[str, list[str]] = {}
    for category, predicates in data.items():
        if not isinstance(category, str) or not isinstance(predicates, list):
            continue
        names = [name for name in predicates if isinstance(name, str) and name in CODE_PREDICATE_TABLE]
        normalized[category] = names
    return normalized


def _eval_predicate_list(code: str, predicate_names: list[str]) -> bool:
    if not predicate_names:
        return False
    return all(CODE_PREDICATE_TABLE[name]("", code, []) for name in predicate_names)


def _default_manual_predicates(category: str) -> list[str]:
    funcs = category_checks.get(category, [])
    return [fn.__name__ for fn in funcs if fn.__name__ in CODE_PREDICATE_TABLE]


def detect_risk(code: str, category: str | None = None) -> bool:
    if category:
        category_predicates = _default_manual_predicates(category)
        if category_predicates:
            return _eval_predicate_list(code, category_predicates)
    fallback_checks = (submit_post_request, request_untrusted_source, write_to_io, involve_bash_rc)
    return any(fn("", code, []) for fn in fallback_checks)


def should_block(mode: str, code: str, category: str, generated_rules: dict[str, list[str]] | None = None) -> bool:
    if mode == "baseline":
        return False
    if mode == "manual":
        return detect_risk(code, category=category)
    if mode == "generated":
        if generated_rules:
            names = generated_rules.get(category, [])
            if names:
                return _eval_predicate_list(code, names)
        # Fallback for compatibility when external generated rules are not provided.
        return detect_risk(code, category=category) or ("os.system" in code and "curl" in code)
    raise ValueError(f"unsupported mode: {mode}")


def load_cases(
    redcode_root: Path,
    max_cases_per_category: int,
    benign_json: Path | None = None,
) -> list[dict]:
    cases: list[dict] = []
    source_files = sorted(redcode_root.glob("index*_30_codes_full*.json"))
    for file in source_files:
        category = _extract_category_from_file(file)
        content = json.loads(file.read_text(encoding="utf-8"))
        for i, sample in enumerate(content[: max_cases_per_category]):
            code = sample.get("Code") or sample.get("code") or ""
            sample_id = sample.get("Index", i)
            cases.append(
                {
                    "case_id": f"risky:{category}:{sample_id}",
                    "category": category,
                    "code": code,
                    # RedCode-Exec split is risky by design in this phase.
                    "is_risky": True,
                }
            )
    if benign_json and benign_json.exists():
        benign_samples = json.loads(benign_json.read_text(encoding="utf-8"))
        for i, sample in enumerate(benign_samples):
            code = sample.get("Code") or sample.get("code") or ""
            sample_id = sample.get("Index", i)
            cases.append(
                {
                    "case_id": f"benign:benign:{sample_id}",
                    "category": "benign",
                    "code": code,
                    "is_risky": False,
                }
            )
    return cases


def run(
    mode: str,
    redcode_root: Path,
    max_cases_per_category: int,
    benign_json: Path | None = None,
    generated_rules_json: Path | None = None,
) -> dict:
    generated_rules = _load_generated_rules(generated_rules_json) if mode == "generated" else {}
    raw_cases = load_cases(
        redcode_root,
        max_cases_per_category=max_cases_per_category,
        benign_json=benign_json,
    )
    scored: list[dict] = []
    for case in raw_cases:
        begin = time.perf_counter()
        blocked = should_block(mode, case["code"], case.get("category", ""), generated_rules=generated_rules)
        elapsed_ms = (time.perf_counter() - begin) * 1000
        scored.append(
            {
                "case_id": case["case_id"],
                "category": case.get("category"),
                "is_risky": case["is_risky"],
                "blocked": blocked,
                "fulfilled": not blocked,
                "overhead_ms": round(elapsed_ms, 6),
            }
        )
    metrics = evaluate_cases(scored)
    by_category = [m.to_dict() for m in evaluate_cases_by_category(scored)]
    return {"mode": mode, "metrics": metrics.to_dict(), "metrics_by_category": by_category, "cases": scored}


def main() -> int:
    parser = argparse.ArgumentParser(description="Run code-domain AgentSpec experiment.")
    parser.add_argument("--mode", choices=["baseline", "manual", "generated"], required=True)
    parser.add_argument("--redcode-root", type=Path, required=True)
    parser.add_argument("--max-cases-per-category", type=int, default=5)
    parser.add_argument("--benign-json", type=Path, required=False)
    parser.add_argument(
        "--generated-rules-json",
        type=Path,
        required=False,
        help="Optional generated rules mapping (category -> predicate names), used in generated mode.",
    )
    parser.add_argument("--result-json", type=Path, required=True)
    parser.add_argument("--report-md", type=Path, required=True)
    args = parser.parse_args()

    result = run(
        mode=args.mode,
        redcode_root=args.redcode_root,
        max_cases_per_category=args.max_cases_per_category,
        benign_json=args.benign_json,
        generated_rules_json=args.generated_rules_json,
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
