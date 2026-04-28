"""Decompose runtime overhead into parsing / predicate-eval / audit-write phases.

The micro-benchmark loads the manual UCA knowledge base, compiles to rules, and
runs the strict spec-runtime pipeline against a fixed sample of risky and benign
cases drawn from RedCode-Exec and the balanced safe set. For each case it
measures three phases independently:

    Phase A (parse):      spec text -> ANTLR token stream -> parse tree (per rule, per case)
    Phase B (eval):       walking the tree, including every predicate call
    Phase C (audit):      JSON-encoding + writing the per-case trace and audit records

Outputs ``artifacts/perf/microbench_summary.json`` and a short markdown report
``artifacts/perf/microbench_report.md`` summarising mean / median / p95 in ms.
"""

from __future__ import annotations

import argparse
import json
import statistics
import time
from pathlib import Path
from typing import Iterable

from antlr4 import CommonTokenStream, InputStream, ParseTreeWalker
from spec_lang.AgentSpecLexer import AgentSpecLexer
from spec_lang.AgentSpecParser import AgentSpecParser

from agent import Action
from enforcement import EnforceResult
from interpreter import RuleInterpreter
from rule import Rule
from state import RuleState
from agentspec_codegen.compiler.rule_compiler import compile_knowledge_base
from agentspec_codegen.uca.storage import load_uca_knowledge_base


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    k = max(0, min(len(sorted_vals) - 1, int(round(pct / 100 * (len(sorted_vals) - 1)))))
    return sorted_vals[k]


def _summary(values: list[float]) -> dict:
    if not values:
        return {"n": 0, "mean_ms": 0.0, "median_ms": 0.0, "p95_ms": 0.0, "min_ms": 0.0, "max_ms": 0.0}
    return {
        "n": len(values),
        "mean_ms": statistics.fmean(values),
        "median_ms": statistics.median(values),
        "p95_ms": _percentile(values, 95.0),
        "min_ms": min(values),
        "max_ms": max(values),
    }


def _load_cases(redcode_root: Path, benign_json: Path, max_per_category: int) -> list[dict]:
    cases: list[dict] = []
    for file in sorted(redcode_root.glob("index*_30_codes_full*.json")):
        category = file.stem.split("_")[0]
        rows = json.loads(file.read_text(encoding="utf-8"))
        for sample in rows[:max_per_category]:
            code = sample.get("Code") or sample.get("code") or ""
            cases.append({"case_id": f"risky:{category}:{sample.get('Index', '')}", "category": category, "code": code, "is_risky": True})
    if benign_json.exists():
        rows = json.loads(benign_json.read_text(encoding="utf-8"))
        for sample in rows[: max_per_category * 5]:
            code = sample.get("Code") or sample.get("code") or ""
            cases.append({"case_id": f"benign:{sample.get('Index', '')}", "category": "benign", "code": code, "is_risky": False})
    return cases


def _phase_parse(rule_raw: str) -> tuple[float, object]:
    started = time.perf_counter()
    stream = InputStream(rule_raw)
    lexer = AgentSpecLexer(stream)
    tokens = CommonTokenStream(lexer)
    parser = AgentSpecParser(tokens)
    tree = parser.program()
    elapsed_ms = (time.perf_counter() - started) * 1000
    return elapsed_ms, tree


def _phase_eval(rule: Rule, tree: object, code: str) -> tuple[float, str, dict]:
    action = Action(name="PythonREPL", input=code, action=None)
    state = RuleState(action=action, intermediate_steps=[], user_input=code)
    interpreter = RuleInterpreter(rule, state)
    started = time.perf_counter()
    walker = ParseTreeWalker()
    walker.walk(interpreter, tree)
    enforce_name = getattr(interpreter, "enforce", "none")
    elapsed_ms = (time.perf_counter() - started) * 1000
    return elapsed_ms, enforce_name, dict(interpreter.cond_eval_history)


def _phase_audit(payload: dict, dest_dir: Path, case_id: str) -> float:
    dest_dir.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    (dest_dir / f"{case_id}.json").write_text(text, encoding="utf-8")
    return (time.perf_counter() - started) * 1000


def run(redcode_root: Path, benign_json: Path, kb_path: Path, output_dir: Path, max_per_category: int, repeats: int) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    audit_dir = output_dir / "scratch_audits"

    kb_obj = load_uca_knowledge_base(kb_path)
    artifacts = compile_knowledge_base(kb_obj)
    rules = [Rule.from_text(item.spec_text) for item in artifacts]

    cases = _load_cases(redcode_root, benign_json, max_per_category)

    parse_samples: list[float] = []
    eval_samples: list[float] = []
    audit_samples: list[float] = []
    e2e_samples: list[float] = []

    for case in cases:
        case_id_safe = case["case_id"].replace(":", "_").replace("/", "_").replace("\\", "_")
        for _ in range(repeats):
            e2e_started = time.perf_counter()
            for rule in rules:
                if not rule.triggered("PythonREPL", case["code"]):
                    continue
                parse_ms, tree = _phase_parse(rule.raw)
                parse_samples.append(parse_ms)
                eval_ms, enforce_name, history = _phase_eval(rule, tree, case["code"])
                eval_samples.append(eval_ms)
                audit_payload = {
                    "rule_id": rule.id,
                    "event": rule.event,
                    "case_id": case["case_id"],
                    "enforce": enforce_name,
                    "check_history": history,
                }
                audit_samples.append(_phase_audit(audit_payload, audit_dir, f"{rule.id}_{case_id_safe}"))
                if enforce_name in {"skip", "stop"}:
                    break
            e2e_samples.append((time.perf_counter() - e2e_started) * 1000)

    summary = {
        "kb_path": str(kb_path),
        "redcode_root": str(redcode_root),
        "benign_json": str(benign_json),
        "max_per_category": max_per_category,
        "repeats": repeats,
        "rule_count": len(rules),
        "case_count": len(cases),
        "phase_parse": _summary(parse_samples),
        "phase_eval": _summary(eval_samples),
        "phase_audit": _summary(audit_samples),
        "end_to_end": _summary(e2e_samples),
    }
    (output_dir / "microbench_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    md_lines = [
        "# Runtime overhead micro-benchmark",
        "",
        f"- Knowledge base: `{kb_path}`",
        f"- Rule count: {summary['rule_count']}",
        f"- Sampled cases: {summary['case_count']} (cap {max_per_category}/category)",
        f"- Repeats per case: {repeats}",
        "",
        "| Phase | Mean (ms) | Median (ms) | p95 (ms) | n |",
        "| --- | --- | --- | --- | --- |",
    ]
    for label, key in [
        ("Phase A: spec parsing (per triggered rule)", "phase_parse"),
        ("Phase B: predicate evaluation (per triggered rule)", "phase_eval"),
        ("Phase C: audit JSON write (per triggered rule)", "phase_audit"),
        ("End-to-end (per case across all rules)", "end_to_end"),
    ]:
        s = summary[key]
        md_lines.append(f"| {label} | {s['mean_ms']:.3f} | {s['median_ms']:.3f} | {s['p95_ms']:.3f} | {s['n']} |")
    (output_dir / "microbench_report.md").write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--redcode-root", type=Path, default=Path("benchmarks/RedCode-Exec/py2text_dataset_json"))
    parser.add_argument("--benign-json", type=Path, default=Path("benchmarks/current_eval/code_safe_equal_mbpp.json"))
    parser.add_argument("--kb", type=Path, default=Path("data/uca/code/sample_kb.json"))
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts/perf"))
    parser.add_argument("--max-per-category", type=int, default=3)
    parser.add_argument("--repeats", type=int, default=5)
    args = parser.parse_args()
    summary = run(
        redcode_root=args.redcode_root,
        benign_json=args.benign_json,
        kb_path=args.kb,
        output_dir=args.output_dir,
        max_per_category=args.max_per_category,
        repeats=args.repeats,
    )
    print(f"output_dir={args.output_dir}")
    print(f"phase_parse_mean={summary['phase_parse']['mean_ms']:.3f}ms")
    print(f"phase_eval_mean={summary['phase_eval']['mean_ms']:.3f}ms")
    print(f"phase_audit_mean={summary['phase_audit']['mean_ms']:.3f}ms")
    print(f"e2e_mean={summary['end_to_end']['mean_ms']:.3f}ms")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
