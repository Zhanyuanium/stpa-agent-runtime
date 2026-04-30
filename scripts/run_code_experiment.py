from __future__ import annotations

import argparse
import os
import json
import time
from pathlib import Path

from agentspec_codegen.eval import (
    evaluate_cases,
    evaluate_cases_by_category,
    evaluate_cases_by_field,
    summarize_to_markdown,
)
from agentspec_codegen.compiler.rule_compiler import (
    CompilationArtifact,
    compile_knowledge_base,
    sort_artifacts_and_rules,
    write_compiled_rules,
)
from agentspec_codegen.uca.models import UcaKnowledgeBase
from agentspec_codegen.uca.owner_harm import map_owner_harm_category
from agentspec_codegen.uca.storage import load_uca_knowledge_base
from agent import Action
from enforcement import EnforceResult
from interpreter import RuleInterpreter
from rule import Rule
from state import RuleState

DEFAULT_CODE_KB = Path("data/uca/code/sample_kb.json")


def _extract_category_from_file(file: Path) -> str:
    return file.stem.split("_")[0]


def _safe_case_id(case_id: str) -> str:
    return case_id.replace(":", "_").replace("/", "_").replace("\\", "_")


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = "\n".join(json.dumps(row, ensure_ascii=False) for row in rows)
    path.write_text(content + ("\n" if content else ""), encoding="utf-8")


def _build_rule_lineage(kb_obj: UcaKnowledgeBase) -> dict[str, dict]:
    lineage: dict[str, dict] = {}
    for entry in kb_obj.entries:
        rule_id = entry.uca_id.lower().replace("-", "_")
        lineage[rule_id] = {
            "uca_id": entry.uca_id,
            "category": entry.metadata.get("category"),
            "risk_type": entry.risk_type.value,
            "mitre_tactic": entry.mitre_tactic,
            "llm_enforcement_suggestion": entry.metadata.get("llm_enforcement_suggestion"),
            "final_enforcement": entry.metadata.get("final_enforcement", entry.enforcement),
            "decision_reason": entry.metadata.get("decision_reason"),
            "decision_conflict": bool(entry.metadata.get("decision_conflict", False)),
            "benign_predicate_hints": entry.metadata.get("benign_predicate_hints"),
            "owner_harm_category": entry.owner_harm_category,
        }
    return lineage


def _build_owner_harm_by_category(kb_obj: UcaKnowledgeBase) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for entry in kb_obj.entries:
        category = entry.metadata.get("category")
        if not category:
            continue
        owner_harm = map_owner_harm_category(
            risk_type=entry.risk_type.value,
            explicit=entry.owner_harm_category or entry.metadata.get("owner_harm_category"),
        )
        if owner_harm is not None:
            mapping[str(category)] = owner_harm.value
    return mapping


def load_rules_from_uca(
    *,
    kb_path: Path | None = None,
    kb_obj: UcaKnowledgeBase | None = None,
    compiled_spec_dir: Path | None = None,
) -> tuple[UcaKnowledgeBase, list[CompilationArtifact], list[Rule]]:
    if kb_obj is None:
        if kb_path is None:
            raise ValueError("either kb_path or kb_obj must be provided")
        kb_obj = load_uca_knowledge_base(kb_path)
    artifacts = compile_knowledge_base(kb_obj)
    rules = [Rule.from_text(item.spec_text) for item in artifacts]
    artifacts, rules = sort_artifacts_and_rules(artifacts, rules)
    if compiled_spec_dir:
        write_compiled_rules(artifacts, compiled_spec_dir)
    return kb_obj, artifacts, rules


def enforce_code_once(
    code: str,
    rules: list[Rule],
    rule_lineage: dict[str, dict],
    *,
    event: str = "PythonREPL",
) -> tuple[bool, float, str | None, list[dict], list[dict]]:
    started = time.perf_counter()
    action = Action(name=event, input=code, action=None)
    state = RuleState(action=action, intermediate_steps=[], user_input=code)
    blocked = False
    blocked_rule_id: str | None = None
    traces: list[dict] = []
    audits: list[dict] = []
    for rule in rules:
        triggered = rule.triggered(action.name, str(action.input))
        if not triggered:
            lineage = rule_lineage.get(rule.id, {})
            traces.append(
                {
                    "rule_id": rule.id,
                    "event": rule.event,
                    "triggered": False,
                    "check_history": {},
                    "enforce_result": "not_triggered",
                    "lineage": lineage,
                }
            )
            continue
        interpreter = RuleInterpreter(rule, state)
        res, _next_action = interpreter.verify_and_enforce(action)
        lineage = rule_lineage.get(rule.id, {})
        trace = {
            "rule_id": rule.id,
            "event": rule.event,
            "triggered": True,
            "check_history": interpreter.cond_eval_history,
            "enforce_result": res.name.lower(),
            "lineage": lineage,
        }
        traces.append(trace)
        audits.append(
            {
                "rule_id": rule.id,
                "event": rule.event,
                "enforce_result": res.name.lower(),
                "check_history": interpreter.cond_eval_history,
                "lineage": lineage,
            }
        )
        if res in (EnforceResult.SKIP, EnforceResult.STOP):
            blocked = True
            blocked_rule_id = rule.id
            break
    elapsed_ms = (time.perf_counter() - started) * 1000
    return blocked, elapsed_ms, blocked_rule_id, traces, audits


def load_cases(
    redcode_root: Path,
    max_cases_per_category: int | None,
    benign_json: Path | None = None,
) -> list[dict]:
    cases: list[dict] = []
    source_files = sorted(redcode_root.glob("index*_30_codes_full*.json"))
    for file in source_files:
        category = _extract_category_from_file(file)
        content = json.loads(file.read_text(encoding="utf-8"))
        scoped_content = content if max_cases_per_category is None else content[:max_cases_per_category]
        for i, sample in enumerate(scoped_content):
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
    max_cases_per_category: int | None,
    benign_json: Path | None = None,
    code_kb: Path = DEFAULT_CODE_KB,
    generated_code_kb: Path | None = None,
    compiled_spec_dir: Path | None = None,
    artifact_root: Path | None = None,
) -> dict:
    runtime_source = "none"
    rule_source = ""
    compiled_rule_count = 0
    rules: list[Rule] = []
    artifacts: list[CompilationArtifact] = []
    loaded_kb: UcaKnowledgeBase | None = None
    stage_root = artifact_root
    if stage_root is None:
        stage_root = Path("artifacts") / "code_eval" / mode

    if mode == "manual":
        loaded_kb, artifacts, rules = load_rules_from_uca(kb_path=code_kb, compiled_spec_dir=compiled_spec_dir)
        runtime_source = "spec_enforcement"
        rule_source = str(code_kb)
        compiled_rule_count = len(artifacts)
    elif mode == "generated":
        if generated_code_kb is None:
            raise ValueError("generated mode requires --generated-code-kb")
        loaded_kb, artifacts, rules = load_rules_from_uca(
            kb_path=generated_code_kb,
            compiled_spec_dir=compiled_spec_dir,
        )
        runtime_source = "spec_enforcement"
        rule_source = str(generated_code_kb)
        compiled_rule_count = len(artifacts)
    rule_lineage = _build_rule_lineage(loaded_kb) if loaded_kb is not None else {}
    owner_harm_by_category = _build_owner_harm_by_category(loaded_kb) if loaded_kb is not None else {}

    # Stage outputs: 01~03 are run-level artifacts.
    if runtime_source == "spec_enforcement" and loaded_kb is not None:
        _write_json(stage_root / "01_uca_loaded.json", json.loads(loaded_kb.model_dump_json()))
        spec_dir = stage_root / "02_compiled_specs"
        write_compiled_rules(artifacts, spec_dir)
        _write_json(
            stage_root / "02_compiled_manifest.json",
            [
                {
                    "rule_id": item.rule_id,
                    "uca_id": item.uca_id,
                    "predicates": item.predicates,
                    "enforcement": item.enforcement,
                    "spec_path": str((spec_dir / f"{item.rule_id}.spec").as_posix()),
                }
                for item in artifacts
            ],
        )
        _write_json(
            stage_root / "03_rules_parsed.json",
            [{"id": rule.id, "event": rule.event, "raw": rule.raw} for rule in rules],
        )
    else:
        _write_json(
            stage_root / "01_uca_loaded.json",
            {"note": "baseline mode has no UCA/rules", "runtime_source": runtime_source},
        )
        _write_json(stage_root / "02_compiled_manifest.json", [])
        _write_json(stage_root / "03_rules_parsed.json", [])

    raw_cases = load_cases(
        redcode_root,
        max_cases_per_category=max_cases_per_category,
        benign_json=benign_json,
    )
    scored: list[dict] = []
    case_audits: list[dict] = []
    for case in raw_cases:
        blocked_rule_id: str | None = None
        check_traces: list[dict] = []
        audits: list[dict] = []
        if mode == "baseline":
            begin = time.perf_counter()
            blocked = False
            elapsed_ms = (time.perf_counter() - begin) * 1000
        else:
            blocked, elapsed_ms, blocked_rule_id, check_traces, audits = enforce_code_once(
                case["code"], rules, rule_lineage, event="PythonREPL"
            )
        trace_payload = {
            "case_id": case["case_id"],
            "category": case.get("category"),
            "event": "PythonREPL",
            "raw_input": str(case["code"]),
            "input_preview": str(case["code"])[:300],
            "rules": check_traces,
            "blocked": blocked,
            "blocked_by_rule_id": blocked_rule_id,
        }
        _write_json(stage_root / "04_check_traces" / f"{_safe_case_id(case['case_id'])}.json", trace_payload)
        case_audits.append(
            {
                "case_id": case["case_id"],
                "event": "PythonREPL",
                "blocked": blocked,
                "blocked_by_rule_id": blocked_rule_id,
                "audits": audits,
                "lineage": rule_lineage.get(blocked_rule_id, {}) if blocked_rule_id else {},
                "owner_harm_category": owner_harm_by_category.get(case.get("category", ""), "unknown"),
                "raw_instruction": str(case["code"]),
                "normalized_input": str(case["code"]),
            }
        )
        scored.append(
            {
                "case_id": case["case_id"],
                "category": case.get("category"),
                "raw_instruction": str(case["code"]),
                "normalized_input": str(case["code"]),
                "input": str(case["code"]),
                "is_risky": case["is_risky"],
                "blocked": blocked,
                "blocked_by_rule_id": blocked_rule_id,
                "fulfilled": not blocked,
                "overhead_ms": round(elapsed_ms, 6),
                "owner_harm_category": owner_harm_by_category.get(case.get("category", ""), "unknown"),
            }
        )
    _write_jsonl(stage_root / "05_case_audits.jsonl", case_audits)
    metrics = evaluate_cases(scored)
    by_category = [m.to_dict() for m in evaluate_cases_by_category(scored)]
    by_owner_harm = [m.to_dict() for m in evaluate_cases_by_field(scored, "owner_harm_category")]
    return {
        "mode": mode,
        "runtime_source": runtime_source,
        "rule_source": rule_source,
        "compiled_rule_count": compiled_rule_count,
        "artifact_root": str(stage_root),
        "metrics": metrics.to_dict(),
        "metrics_by_category": by_category,
        "metrics_by_owner_harm": by_owner_harm,
        "enforcement_conflict_count": sum(1 for v in rule_lineage.values() if v.get("decision_conflict")),
        "cases": scored,
    }


def main() -> int:
    os.environ.setdefault("AGENTSPEC_NON_INTERACTIVE", "1")

    parser = argparse.ArgumentParser(description="Run code-domain AgentSpec experiment.")
    parser.add_argument("--mode", choices=["baseline", "manual", "generated"], required=True)
    parser.add_argument("--redcode-root", type=Path, required=True)
    parser.add_argument(
        "--max-cases-per-category",
        type=int,
        default=None,
        help="Optional cap per category. Default runs all available cases.",
    )
    parser.add_argument("--benign-json", type=Path, required=False)
    parser.add_argument(
        "--code-kb",
        type=Path,
        default=DEFAULT_CODE_KB,
        help="Code-domain UCA knowledge base for manual mode.",
    )
    parser.add_argument(
        "--generated-code-kb",
        type=Path,
        required=False,
        help="Generated UCA knowledge base for generated mode.",
    )
    parser.add_argument(
        "--compiled-spec-dir",
        type=Path,
        required=False,
        help="Optional directory to dump compiled .spec files for audit/reproducibility.",
    )
    parser.add_argument(
        "--artifact-root",
        type=Path,
        required=False,
        help="Optional root for staged artifacts (01~05). Default: artifacts/code_eval/<mode>.",
    )
    parser.add_argument("--result-json", type=Path, required=True)
    parser.add_argument("--report-md", type=Path, required=True)
    args = parser.parse_args()

    result = run(
        mode=args.mode,
        redcode_root=args.redcode_root,
        max_cases_per_category=args.max_cases_per_category,
        benign_json=args.benign_json,
        code_kb=args.code_kb,
        generated_code_kb=args.generated_code_kb,
        compiled_spec_dir=args.compiled_spec_dir,
        artifact_root=args.artifact_root,
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
