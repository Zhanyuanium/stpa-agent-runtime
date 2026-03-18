from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from agentspec_codegen.eval import evaluate_cases, summarize_to_markdown
from agentspec_codegen.uca.storage import load_uca_knowledge_base
from agentspec_codegen.compiler.rule_compiler import compile_knowledge_base
from agent import Action
from enforcement import EnforceResult
from interpreter import RuleInterpreter
from rule import Rule
from state import RuleState


def _load_rules_from_kb(kb_path: Path) -> list[Rule]:
    kb = load_uca_knowledge_base(kb_path)
    artifacts = compile_knowledge_base(kb)
    return [Rule.from_text(item.spec_text) for item in artifacts]


def _enforce_once(action: Action, rules: list[Rule], user_input: str) -> tuple[bool, float]:
    started = time.perf_counter()
    state = RuleState(action=action, intermediate_steps=[], user_input=user_input)
    blocked = False
    for rule in rules:
        if rule.triggered(action.name, action.input):
            interpreter = RuleInterpreter(rule, state)
            res, _next = interpreter.verify_and_enforce(action)
            if res in (EnforceResult.SKIP, EnforceResult.STOP):
                blocked = True
                break
    elapsed_ms = (time.perf_counter() - started) * 1000
    return blocked, elapsed_ms


def _load_eval_cases(risky_json: Path, benign_json: Path | None) -> list[dict]:
    risky = json.loads(risky_json.read_text(encoding="utf-8"))
    cases: list[dict] = []
    for idx, item in enumerate(risky):
        command = item.get("command") or item.get("Code") or item.get("code") or ""
        event = item.get("event", "TerminalExecute")
        cases.append({"case_id": f"risky:{idx}", "event": event, "input": command, "is_risky": True})
    if benign_json and benign_json.exists():
        benign = json.loads(benign_json.read_text(encoding="utf-8"))
        for idx, item in enumerate(benign):
            command = item.get("command") or item.get("Code") or item.get("code") or ""
            event = item.get("event", "TerminalExecute")
            cases.append({"case_id": f"benign:{idx}", "event": event, "input": command, "is_risky": False})
    return cases


def run_model_in_loop(
    shell_kb_path: Path,
    risky_json: Path,
    benign_json: Path | None,
) -> dict:
    rules = _load_rules_from_kb(shell_kb_path)
    cases = _load_eval_cases(risky_json, benign_json)
    scored = []
    for case in cases:
        action = Action(name=case["event"], input=case["input"], action=None)
        blocked, elapsed_ms = _enforce_once(action, rules, user_input=case["input"])
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
    return {"mode": "model_in_loop", "metrics": metrics.to_dict(), "cases": scored}


def main() -> int:
    parser = argparse.ArgumentParser(description="Run model-in-loop shell experiment.")
    parser.add_argument("--shell-kb", type=Path, default=Path("data/uca/shell/shell_kb.json"))
    parser.add_argument("--risky-json", type=Path, required=True)
    parser.add_argument("--benign-json", type=Path, required=False)
    parser.add_argument("--result-json", type=Path, required=True)
    parser.add_argument("--report-md", type=Path, required=True)
    args = parser.parse_args()

    result = run_model_in_loop(
        shell_kb_path=args.shell_kb,
        risky_json=args.risky_json,
        benign_json=args.benign_json,
    )
    args.result_json.parent.mkdir(parents=True, exist_ok=True)
    args.report_md.parent.mkdir(parents=True, exist_ok=True)
    args.result_json.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    args.report_md.write_text(summarize_to_markdown("model_in_loop", evaluate_cases(result["cases"])), encoding="utf-8")
    print(f"result_json={args.result_json}")
    print(f"report_md={args.report_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
