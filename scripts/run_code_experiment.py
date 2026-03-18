from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from agentspec_codegen.eval import evaluate_cases, evaluate_cases_by_category, summarize_to_markdown
from agentspec_codegen.compiler.rule_compiler import compile_knowledge_base, write_compiled_rules
from agentspec_codegen.uca.models import UcaKnowledgeBase
from agentspec_codegen.uca.storage import load_uca_knowledge_base
from agent import Action
from enforcement import EnforceResult
from interpreter import RuleInterpreter
from rule import Rule
from state import RuleState

DEFAULT_CODE_KB = Path("data/uca/code/sample_kb.json")


def _extract_category_from_file(file: Path) -> str:
    return file.stem.split("_")[0]


def _load_generated_rules_as_kb(path: Path) -> UcaKnowledgeBase:
    """
    Backward compatibility:
    Convert deprecated generated-rules mapping (category -> predicate names)
    to an in-memory UCA knowledge base so execution still goes through
    UCA -> .spec -> RuleInterpreter chain.
    """
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("generated rules json must be an object: {category: [predicate_names...]}")
    entries = []
    for category, predicates in data.items():
        if not isinstance(category, str) or not isinstance(predicates, list):
            continue
        predicate_names = [name for name in predicates if isinstance(name, str)]
        if not predicate_names:
            continue
        entries.append(
            {
                "uca_id": f"UCA-GEN-{category.upper()}",
                "title": f"Generated runtime guard for {category}",
                "domain": "code",
                "risk_type": "untrusted_post_request",
                "mitre_tactic": "exfiltration",
                "trigger_event": "PythonREPL",
                "predicate_hints": predicate_names,
                "enforcement": "stop",
                "rationale": f"Compatibility-generated UCA for category {category}.",
                "metadata": {"source": "generated_rules_json", "category": category},
            }
        )
    return UcaKnowledgeBase.model_validate({"version": "generated-compat-0.1.0", "entries": entries})


def load_rules_from_uca(
    *,
    kb_path: Path | None = None,
    kb_obj: UcaKnowledgeBase | None = None,
    compiled_spec_dir: Path | None = None,
) -> tuple[list[Rule], int]:
    if kb_obj is None:
        if kb_path is None:
            raise ValueError("either kb_path or kb_obj must be provided")
        kb_obj = load_uca_knowledge_base(kb_path)
    artifacts = compile_knowledge_base(kb_obj)
    if compiled_spec_dir:
        write_compiled_rules(artifacts, compiled_spec_dir)
    rules = [Rule.from_text(item.spec_text) for item in artifacts]
    return rules, len(artifacts)


def enforce_code_once(code: str, rules: list[Rule], *, event: str = "PythonREPL") -> tuple[bool, float, str | None]:
    started = time.perf_counter()
    action = Action(name=event, input=code, action=None)
    state = RuleState(action=action, intermediate_steps=[], user_input=code)
    blocked = False
    blocked_rule_id: str | None = None
    for rule in rules:
        if rule.triggered(action.name, str(action.input)):
            interpreter = RuleInterpreter(rule, state)
            res, _next_action = interpreter.verify_and_enforce(action)
            if res in (EnforceResult.SKIP, EnforceResult.STOP):
                blocked = True
                blocked_rule_id = rule.id
                break
    elapsed_ms = (time.perf_counter() - started) * 1000
    return blocked, elapsed_ms, blocked_rule_id


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
    code_kb: Path = DEFAULT_CODE_KB,
    generated_code_kb: Path | None = None,
    generated_rules_json: Path | None = None,
    compiled_spec_dir: Path | None = None,
) -> dict:
    runtime_source = "none"
    rule_source = ""
    compiled_rule_count = 0
    rules: list[Rule] = []

    if mode == "manual":
        rules, compiled_rule_count = load_rules_from_uca(kb_path=code_kb, compiled_spec_dir=compiled_spec_dir)
        runtime_source = "spec_enforcement"
        rule_source = str(code_kb)
    elif mode == "generated":
        if generated_code_kb:
            rules, compiled_rule_count = load_rules_from_uca(
                kb_path=generated_code_kb,
                compiled_spec_dir=compiled_spec_dir,
            )
            runtime_source = "spec_enforcement"
            rule_source = str(generated_code_kb)
        elif generated_rules_json:
            compat_kb = _load_generated_rules_as_kb(generated_rules_json)
            rules, compiled_rule_count = load_rules_from_uca(
                kb_obj=compat_kb,
                compiled_spec_dir=compiled_spec_dir,
            )
            runtime_source = "spec_enforcement"
            rule_source = f"{generated_rules_json} (deprecated generated-rules-json compatibility)"
        else:
            raise ValueError("generated mode requires --generated-code-kb (or deprecated --generated-rules-json)")

    raw_cases = load_cases(
        redcode_root,
        max_cases_per_category=max_cases_per_category,
        benign_json=benign_json,
    )
    scored: list[dict] = []
    for case in raw_cases:
        blocked_rule_id: str | None = None
        if mode == "baseline":
            begin = time.perf_counter()
            blocked = False
            elapsed_ms = (time.perf_counter() - begin) * 1000
        else:
            blocked, elapsed_ms, blocked_rule_id = enforce_code_once(case["code"], rules, event="PythonREPL")
        scored.append(
            {
                "case_id": case["case_id"],
                "category": case.get("category"),
                "is_risky": case["is_risky"],
                "blocked": blocked,
                "blocked_by_rule_id": blocked_rule_id,
                "fulfilled": not blocked,
                "overhead_ms": round(elapsed_ms, 6),
            }
        )
    metrics = evaluate_cases(scored)
    by_category = [m.to_dict() for m in evaluate_cases_by_category(scored)]
    return {
        "mode": mode,
        "runtime_source": runtime_source,
        "rule_source": rule_source,
        "compiled_rule_count": compiled_rule_count,
        "metrics": metrics.to_dict(),
        "metrics_by_category": by_category,
        "cases": scored,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run code-domain AgentSpec experiment.")
    parser.add_argument("--mode", choices=["baseline", "manual", "generated"], required=True)
    parser.add_argument("--redcode-root", type=Path, required=True)
    parser.add_argument("--max-cases-per-category", type=int, default=5)
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
        help="Generated UCA knowledge base for generated mode (preferred).",
    )
    parser.add_argument(
        "--generated-rules-json",
        type=Path,
        required=False,
        help="Deprecated compatibility input: generated mapping (category -> predicate names).",
    )
    parser.add_argument(
        "--compiled-spec-dir",
        type=Path,
        required=False,
        help="Optional directory to dump compiled .spec files for audit/reproducibility.",
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
        generated_rules_json=args.generated_rules_json,
        compiled_spec_dir=args.compiled_spec_dir,
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
