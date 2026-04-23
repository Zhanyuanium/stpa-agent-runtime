from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from agentspec_codegen.eval import evaluate_cases, evaluate_cases_by_category, evaluate_cases_by_field, summarize_to_markdown
from agentspec_codegen.eval.post_audit_verifier import ContextMode, evaluate_post_audit


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_trace_inputs(artifact_root: Path) -> dict[str, str]:
    trace_dir = artifact_root / "04_check_traces"
    mapping: dict[str, str] = {}
    if not trace_dir.exists():
        return mapping
    for trace_file in sorted(trace_dir.glob("*.json")):
        payload = json.loads(trace_file.read_text(encoding="utf-8"))
        case_id = str(payload.get("case_id", "")).strip()
        if not case_id:
            continue
        mapping[case_id] = str(payload.get("input_preview", ""))
    return mapping


def _load_goals(path: Path | None) -> dict[str, str]:
    if path is None or not path.exists():
        return {}
    payload = _load_json(path)
    if isinstance(payload, dict):
        return {str(k): str(v) for k, v in payload.items()}
    return {}


def run_post_audit_verifier(
    *,
    gate_result_json: Path,
    output_json: Path,
    output_md: Path,
    context_mode: str,
    owner_goals_json: Path | None = None,
) -> dict:
    gate_result = _load_json(gate_result_json)
    artifact_root = Path(gate_result["artifact_root"])
    trace_inputs = _load_trace_inputs(artifact_root)
    owner_goals = _load_goals(owner_goals_json)
    combined_cases: list[dict] = []

    for case in gate_result["cases"]:
        case_id = str(case["case_id"])
        gate_blocked = bool(case.get("blocked", False))
        verifier_started = time.perf_counter()
        verifier_decision = evaluate_post_audit(
            text=trace_inputs.get(case_id, ""),
            context_mode=context_mode,
            owner_goal=owner_goals.get(case_id, ""),
        )
        verifier_elapsed_ms = (time.perf_counter() - verifier_started) * 1000
        blocked = gate_blocked or verifier_decision.blocked
        combined = dict(case)
        combined["gate_blocked"] = gate_blocked
        combined["blocked"] = blocked
        combined["fulfilled"] = not blocked
        combined["post_audit"] = verifier_decision.to_dict()
        combined["post_audit_context_mode"] = context_mode
        combined["overhead_ms"] = round(float(case.get("overhead_ms", 0.0)) + verifier_elapsed_ms, 6)
        combined_cases.append(combined)

    metrics = evaluate_cases(combined_cases)
    by_category = [m.to_dict() for m in evaluate_cases_by_category(combined_cases)]
    by_owner_harm = [m.to_dict() for m in evaluate_cases_by_field(combined_cases, "owner_harm_category")]
    result = {
        "mode": f"{gate_result.get('mode', 'unknown')}_post_audit",
        "runtime_source": gate_result.get("runtime_source"),
        "rule_source": gate_result.get("rule_source"),
        "artifact_root": gate_result.get("artifact_root"),
        "context_mode": context_mode,
        "metrics": metrics.to_dict(),
        "metrics_by_category": by_category,
        "metrics_by_owner_harm": by_owner_harm,
        "cases": combined_cases,
    }
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    output_md.write_text(summarize_to_markdown(result["mode"], metrics), encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply deterministic post-audit verifier on gate results.")
    parser.add_argument("--gate-result-json", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-md", type=Path, required=True)
    parser.add_argument(
        "--context-mode",
        choices=[ContextMode.FULL, ContextMode.STRIPPED, ContextMode.STRUCTURED_GOAL],
        default=ContextMode.FULL,
    )
    parser.add_argument(
        "--owner-goals-json",
        type=Path,
        required=False,
        help="Optional case_id -> owner goal mapping for structured-goal mode.",
    )
    args = parser.parse_args()
    run_post_audit_verifier(
        gate_result_json=args.gate_result_json,
        output_json=args.output_json,
        output_md=args.output_md,
        context_mode=args.context_mode,
        owner_goals_json=args.owner_goals_json,
    )
    print(f"output_json={args.output_json}")
    print(f"output_md={args.output_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
