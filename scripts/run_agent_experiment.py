"""Run strict spec-runtime shell enforcement experiments."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from agentspec_codegen.eval import evaluate_cases, summarize_to_markdown
from agentspec_codegen.runtime import RuleAuditRecord
from agentspec_codegen.shell_parser import get_shellcheck_summary_for_audit
from agentspec_codegen.uca.storage import load_uca_knowledge_base
from agentspec_codegen.compiler.rule_compiler import CompilationArtifact, compile_knowledge_base, write_compiled_rules
from agent import Action
from enforcement import EnforceResult
from interpreter import RuleInterpreter
from rule import Rule
from state import RuleState


def _safe_case_id(case_id: str) -> str:
    return case_id.replace(":", "_").replace("/", "_").replace("\\", "_")


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = "\n".join(json.dumps(row, ensure_ascii=False) for row in rows)
    path.write_text(content + ("\n" if content else ""), encoding="utf-8")


def _load_rules_from_kb(kb_path: Path) -> tuple[object, list[CompilationArtifact], list[Rule]]:
    kb = load_uca_knowledge_base(kb_path)
    artifacts = compile_knowledge_base(kb)
    return kb, artifacts, [Rule.from_text(item.spec_text) for item in artifacts]


def _enforce_once(action: Action, rules: list[Rule], user_input: str) -> tuple[bool, float, str | None, list[dict], list[dict]]:
    started = time.perf_counter()
    state = RuleState(action=action, intermediate_steps=[], user_input=user_input)
    blocked = False
    blocked_rule_id: str | None = None
    traces: list[dict] = []
    case_audits: list[dict] = []
    for rule in rules:
        triggered = rule.triggered(action.name, action.input)
        if not triggered:
            traces.append(
                {
                    "rule_id": rule.id,
                    "event": rule.event,
                    "triggered": False,
                    "check_history": {},
                    "enforce_result": "not_triggered",
                }
            )
            continue
        interpreter = RuleInterpreter(rule, state)
        res, _next = interpreter.verify_and_enforce(action)
        shellcheck_summary = get_shellcheck_summary_for_audit()
        shellcheck_diagnostics = shellcheck_summary.get("diagnostics", []) if shellcheck_summary else None
        command_text = shellcheck_summary.get("command_text") if shellcheck_summary else None
        record = RuleAuditRecord(
            rule_id=rule.id,
            event=rule.event,
            action_name=action.name,
            enforce_result=res.name.lower(),
            detail=str(interpreter.cond_eval_history),
            command_text=command_text,
            shellcheck_summary=shellcheck_summary,
            shellcheck_diagnostics=shellcheck_diagnostics,
        )
        state.runtime_context.add_audit(record)
        traces.append(
            {
                "rule_id": rule.id,
                "event": rule.event,
                "triggered": True,
                "check_history": interpreter.cond_eval_history,
                "enforce_result": res.name.lower(),
            }
        )
        case_audits.append(record.model_dump())
        if res in (EnforceResult.SKIP, EnforceResult.STOP):
            blocked = True
            blocked_rule_id = rule.id
            break
    elapsed_ms = (time.perf_counter() - started) * 1000
    return blocked, elapsed_ms, blocked_rule_id, traces, case_audits


def _load_case_items(path: Path) -> list[tuple[str, dict]]:
    """
    Load case objects from a json file or a directory of json files.
    Returns tuples of (source_tag, case_obj).
    """
    if path.is_dir():
        items: list[tuple[str, dict]] = []
        for file in sorted(path.glob("*.json")):
            data = json.loads(file.read_text(encoding="utf-8"))
            if not isinstance(data, list):
                continue
            for obj in data:
                if isinstance(obj, dict):
                    items.append((file.stem, obj))
        return items

    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        return []
    return [(path.stem, obj) for obj in data if isinstance(obj, dict)]


def _extract_command(item: dict) -> str:
    return (
        item.get("command")
        or item.get("Code")
        or item.get("code")
        or item.get("Bash")
        or ""
    )


def _load_eval_cases(risky_json: Path, benign_json: Path | None) -> list[dict]:
    risky_items = _load_case_items(risky_json)
    cases: list[dict] = []
    for idx, (source, item) in enumerate(risky_items):
        command = _extract_command(item)
        event = item.get("event", "TerminalExecute")
        sample_id = item.get("Index", idx)
        cases.append(
            {
                "case_id": f"risky:{source}:{sample_id}",
                "event": event,
                "input": command,
                "is_risky": True,
            }
        )
    if benign_json and benign_json.exists():
        benign_items = _load_case_items(benign_json)
        for idx, (source, item) in enumerate(benign_items):
            command = _extract_command(item)
            event = item.get("event", "TerminalExecute")
            sample_id = item.get("Index", idx)
            cases.append(
                {
                    "case_id": f"benign:{source}:{sample_id}",
                    "event": event,
                    "input": command,
                    "is_risky": False,
                }
            )
    return cases


def run_model_in_loop(
    shell_kb_path: Path,
    risky_json: Path,
    benign_json: Path | None,
    *,
    artifact_root: Path | None = None,
) -> dict:
    """Run shell enforcement experiment with strict spec runtime."""
    cases = _load_eval_cases(risky_json, benign_json)
    scored: list[dict] = []
    stage_root = artifact_root or (Path("artifacts") / "shell_eval" / "spec_runtime")
    all_case_audits: list[dict] = []
    kb, artifacts, rules = _load_rules_from_kb(shell_kb_path)
    runtime_source = "spec_enforcement"
    rule_source = str(shell_kb_path)
    compiled_rule_count = len(artifacts)
    _write_json(stage_root / "01_uca_loaded.json", json.loads(kb.model_dump_json()))
    spec_dir = stage_root / "02_compiled_specs"
    write_compiled_rules(artifacts, spec_dir)
    _write_json(
        stage_root / "02_compiled_manifest.json",
        [
            {
                "rule_id": item.rule_id,
                "uca_id": item.uca_id,
                "predicates": item.predicates,
                "spec_path": str((spec_dir / f"{item.rule_id}.spec").as_posix()),
            }
            for item in artifacts
        ],
    )
    _write_json(
        stage_root / "03_rules_parsed.json",
        [{"id": rule.id, "event": rule.event, "raw": rule.raw} for rule in rules],
    )
    for case in cases:
        action = Action(name=case["event"], input=case["input"], action=None)
        blocked, elapsed_ms, blocked_rule_id, traces, audits = _enforce_once(
            action, rules, user_input=case["input"]
        )
        _write_json(
            stage_root / "04_check_traces" / f"{_safe_case_id(case['case_id'])}.json",
            {
                "case_id": case["case_id"],
                "event": case["event"],
                "rules": traces,
                "blocked": blocked,
                "blocked_by_rule_id": blocked_rule_id,
            },
        )
        all_case_audits.append(
            {
                "case_id": case["case_id"],
                "event": case["event"],
                "blocked": blocked,
                "blocked_by_rule_id": blocked_rule_id,
                "audits": audits,
            }
        )
        scored.append(
            {
                "case_id": case["case_id"],
                "is_risky": case["is_risky"],
                "blocked": blocked,
                "blocked_by_rule_id": blocked_rule_id,
                "fulfilled": not blocked,
                "overhead_ms": round(elapsed_ms, 6),
            }
        )

    _write_jsonl(stage_root / "05_case_audits.jsonl", all_case_audits)
    metrics = evaluate_cases(scored)
    return {
        "mode": "model_in_loop",
        "backend": "spec_runtime",
        "runtime_source": runtime_source,
        "rule_source": rule_source,
        "compiled_rule_count": compiled_rule_count,
        "artifact_root": str(stage_root),
        "metrics": metrics.to_dict(),
        "cases": scored,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run strict spec-runtime shell experiment.")
    parser.add_argument(
        "--shell-kb",
        type=Path,
        default=Path("data/uca/shell/shell_kb.json"),
        help="UCA knowledge base for strict spec-runtime shell enforcement.",
    )
    parser.add_argument(
        "--risky-json",
        type=Path,
        required=True,
        help="Risky dataset path: json file or directory of json files (e.g. bash2text_dataset_json)",
    )
    parser.add_argument(
        "--benign-json",
        type=Path,
        required=False,
        help="Optional benign dataset path: json file or directory of json files",
    )
    parser.add_argument("--result-json", type=Path, required=True)
    parser.add_argument("--report-md", type=Path, required=True)
    parser.add_argument(
        "--artifact-root",
        type=Path,
        required=False,
        help="Optional root for staged artifacts (01~05). Default: artifacts/shell_eval/spec_runtime.",
    )
    args = parser.parse_args()

    result = run_model_in_loop(
        shell_kb_path=args.shell_kb,
        risky_json=args.risky_json,
        benign_json=args.benign_json,
        artifact_root=args.artifact_root,
    )
    args.result_json.parent.mkdir(parents=True, exist_ok=True)
    args.report_md.parent.mkdir(parents=True, exist_ok=True)
    args.result_json.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    mode_label = "model_in_loop_spec_runtime"
    args.report_md.write_text(summarize_to_markdown(mode_label, evaluate_cases(result["cases"])), encoding="utf-8")
    print(f"result_json={args.result_json}")
    print(f"report_md={args.report_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
