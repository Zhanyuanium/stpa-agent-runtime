from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from agentspec_codegen.eval import evaluate_cases, evaluate_cases_by_category, evaluate_cases_by_field
from agentspec_codegen.eval.agentharm_adapter import load_agentharm_cases
from agentspec_codegen.eval.post_audit_verifier import ContextMode, evaluate_post_audit

try:
    from scripts.run_code_experiment import _build_owner_harm_by_category, enforce_code_once, load_rules_from_uca
except ModuleNotFoundError:
    from run_code_experiment import _build_owner_harm_by_category, enforce_code_once, load_rules_from_uca


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_trace_inputs(artifact_root: Path) -> dict[str, str]:
    trace_dir = artifact_root / "04_check_traces"
    mapping: dict[str, str] = {}
    if not trace_dir.exists():
        return mapping
    for trace_file in sorted(trace_dir.glob("*.json")):
        payload = _load_json(trace_file)
        case_id = str(payload.get("case_id", "")).strip()
        if not case_id:
            continue
        mapping[case_id] = str(payload.get("input_preview", ""))
    return mapping


def _default_owner_goal(case: dict) -> str:
    category = str(case.get("category", "")).lower()
    if "benign" in category:
        return "仅执行本地安全分析，不修改系统关键文件，不外发数据。"
    if "privacy" in category or "credential" in category:
        return "在本地完成最小必要处理，不向外部发送任何敏感信息。"
    return "完成用户任务且不越过owner授权边界，不进行破坏性操作。"


def _apply_post_audit(cases: list[dict], context_mode: str) -> list[dict]:
    scored: list[dict] = []
    for case in cases:
        started = time.perf_counter()
        decision = evaluate_post_audit(
            text=str(case.get("input", "")),
            context_mode=context_mode,
            owner_goal=_default_owner_goal(case),
        )
        elapsed_ms = (time.perf_counter() - started) * 1000
        blocked = bool(case.get("blocked", False)) or decision.blocked
        merged = dict(case)
        merged["blocked"] = blocked
        merged["fulfilled"] = not blocked
        merged["post_audit"] = decision.to_dict()
        merged["post_audit_context_mode"] = context_mode
        merged["overhead_ms"] = round(float(case.get("overhead_ms", 0.0)) + elapsed_ms, 6)
        scored.append(merged)
    return scored


def _summarize_cases(cases: list[dict], *, mode: str, dataset: str, context_mode: str) -> dict:
    return {
        "mode": mode,
        "dataset": dataset,
        "context_mode": context_mode,
        "metrics": evaluate_cases(cases).to_dict(),
        "metrics_by_category": [m.to_dict() for m in evaluate_cases_by_category(cases)],
        "metrics_by_owner_harm": [m.to_dict() for m in evaluate_cases_by_field(cases, "owner_harm_category")],
        "cases": cases,
    }


def run_agentharm_with_current_rules(agentharm_root: Path, code_kb: Path) -> dict:
    raw_cases = load_agentharm_cases(agentharm_root)
    kb, _artifacts, rules = load_rules_from_uca(kb_path=code_kb)
    owner_harm_by_category = _build_owner_harm_by_category(kb)
    scored: list[dict] = []
    for case in raw_cases:
        blocked, elapsed_ms, blocked_rule_id, _traces, _audits = enforce_code_once(
            str(case.get("input", "")),
            rules,
            rule_lineage={},
            event="PythonREPL",
        )
        row = {
            "case_id": case["case_id"],
            "category": case["category"],
            "input": case.get("input", ""),
            "is_risky": bool(case.get("is_risky", False)),
            "blocked": blocked,
            "blocked_by_rule_id": blocked_rule_id,
            "fulfilled": not blocked,
            "overhead_ms": round(elapsed_ms, 6),
            "owner_harm_category": owner_harm_by_category.get(str(case["category"]), "unknown"),
        }
        scored.append(row)
    return _summarize_cases(scored, mode="gate_only", dataset="agentharm", context_mode=ContextMode.FULL)


def run_code_gate_result(gate_result_json: Path) -> dict:
    payload = _load_json(gate_result_json)
    trace_inputs = _load_trace_inputs(Path(payload.get("artifact_root", "")))
    cases = []
    for case in payload.get("cases", []):
        copied = dict(case)
        copied["input"] = trace_inputs.get(str(copied.get("case_id", "")), "")
        cases.append(copied)
    return _summarize_cases(cases, mode="gate_only", dataset="current_code", context_mode=ContextMode.FULL)


def run_owner_harm_eval(
    *,
    output_dir: Path,
    code_gate_result_json: Path,
    run_agentharm: bool,
    agentharm_root: Path | None,
    code_kb: Path,
    run_ssdg_ablation: bool,
) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs: dict[str, dict] = {}

    code_gate = run_code_gate_result(code_gate_result_json)
    _write_json(output_dir / "current_code_gate_only.json", code_gate)
    outputs["current_code_gate_only"] = code_gate

    modes = [ContextMode.FULL]
    if run_ssdg_ablation:
        modes = [ContextMode.FULL, ContextMode.STRIPPED, ContextMode.STRUCTURED_GOAL]
    for mode in modes:
        code_post = _apply_post_audit(code_gate["cases"], context_mode=mode)
        code_post_summary = _summarize_cases(
            code_post,
            mode="gate_plus_post_audit",
            dataset="current_code",
            context_mode=mode,
        )
        key = f"current_code_post_audit_{mode}"
        _write_json(output_dir / f"{key}.json", code_post_summary)
        outputs[key] = code_post_summary

    if run_agentharm and agentharm_root is not None:
        agentharm_gate = run_agentharm_with_current_rules(agentharm_root, code_kb)
        _write_json(output_dir / "agentharm_gate_only.json", agentharm_gate)
        outputs["agentharm_gate_only"] = agentharm_gate
        for mode in modes:
            agentharm_post = _apply_post_audit(agentharm_gate["cases"], context_mode=mode)
            agentharm_post_summary = _summarize_cases(
                agentharm_post,
                mode="gate_plus_post_audit",
                dataset="agentharm",
                context_mode=mode,
            )
            key = f"agentharm_post_audit_{mode}"
            _write_json(output_dir / f"{key}.json", agentharm_post_summary)
            outputs[key] = agentharm_post_summary
    _write_json(output_dir / "owner_harm_eval_summary.json", outputs)
    return outputs


def main() -> int:
    parser = argparse.ArgumentParser(description="Unified owner-harm evaluation entrypoint.")
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts/owner_harm_eval/unified"))
    parser.add_argument("--code-gate-result-json", type=Path, required=True)
    parser.add_argument("--run-agentharm", action="store_true")
    parser.add_argument("--agentharm-root", type=Path, required=False)
    parser.add_argument("--code-kb", type=Path, default=Path("data/uca/code/sample_kb.json"))
    parser.add_argument("--run-ssdg-ablation", action="store_true")
    args = parser.parse_args()

    if args.run_agentharm and args.agentharm_root is None:
        raise SystemExit("--run-agentharm requires --agentharm-root")

    result = run_owner_harm_eval(
        output_dir=args.output_dir,
        code_gate_result_json=args.code_gate_result_json,
        run_agentharm=args.run_agentharm,
        agentharm_root=args.agentharm_root,
        code_kb=args.code_kb,
        run_ssdg_ablation=args.run_ssdg_ablation,
    )
    print(f"output_dir={args.output_dir}")
    print(f"result_keys={','.join(sorted(result.keys()))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
