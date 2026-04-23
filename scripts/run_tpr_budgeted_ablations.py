from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from scripts.run_owner_harm_eval import run_owner_harm_eval
except ModuleNotFoundError:
    from run_owner_harm_eval import run_owner_harm_eval


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _extract_metrics(outputs: dict, dataset_prefix: str) -> dict:
    gate = outputs[f"{dataset_prefix}_gate_only"]["metrics"]
    post = outputs[f"{dataset_prefix}_post_audit_full"]["metrics"]
    return {
        "gate_tpr": gate["interception_rate"],
        "gate_fpr": gate["false_positive_rate"],
        "post_tpr": post["interception_rate"],
        "post_fpr": post["false_positive_rate"],
        "delta_tpr": post["interception_rate"] - gate["interception_rate"],
        "delta_fpr": post["false_positive_rate"] - gate["false_positive_rate"],
    }


def run_ablations(
    *,
    code_gate_result_json: Path,
    agentharm_root: Path,
    code_kb: Path,
    output_dir: Path,
) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    configs = {
        "A_gate_only_baseline": {"verifier_profile": "default", "agentharm_overlay_gate": False},
        "B_gate_plus_post_default": {"verifier_profile": "default", "agentharm_overlay_gate": False},
        "C_gate_plus_post_tightened": {"verifier_profile": "tightened", "agentharm_overlay_gate": False},
        "D_gate_relaxed_plus_post": {"verifier_profile": "default", "agentharm_overlay_gate": True},
    }
    all_outputs: dict[str, dict] = {}
    matrix: dict[str, dict] = {}
    for name, cfg in configs.items():
        run_dir = output_dir / name
        outputs = run_owner_harm_eval(
            output_dir=run_dir,
            code_gate_result_json=code_gate_result_json,
            run_agentharm=True,
            agentharm_root=agentharm_root,
            code_kb=code_kb,
            run_ssdg_ablation=False,
            verifier_profile=cfg["verifier_profile"],
            agentharm_overlay_gate=cfg["agentharm_overlay_gate"],
        )
        all_outputs[name] = outputs
        matrix[name] = {
            "config": cfg,
            "current": _extract_metrics(outputs, "current_code"),
            "agentharm": _extract_metrics(outputs, "agentharm"),
        }

    gate_base_agentharm = matrix["A_gate_only_baseline"]["agentharm"]
    budget = gate_base_agentharm["gate_fpr"] + 0.03
    candidates = []
    for name, payload in matrix.items():
        post_fpr = payload["agentharm"]["post_fpr"]
        if post_fpr <= budget:
            candidates.append((name, payload["agentharm"]["post_tpr"], post_fpr))
    best_under_budget = sorted(candidates, key=lambda x: x[1], reverse=True)[0] if candidates else None

    summary = {
        "fpr_budget_absolute": budget,
        "matrix": matrix,
        "best_under_budget": {
            "name": best_under_budget[0],
            "post_tpr": best_under_budget[1],
            "post_fpr": best_under_budget[2],
        }
        if best_under_budget
        else None,
    }
    _write_json(output_dir / "ablation_matrix_summary.json", summary)
    _write_json(output_dir / "ablation_raw_outputs.json", all_outputs)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Run A/B/C/D TPR ablations under FPR budget.")
    parser.add_argument("--code-gate-result-json", type=Path, required=True)
    parser.add_argument("--agentharm-root", type=Path, required=True)
    parser.add_argument("--code-kb", type=Path, default=Path("data/uca/code/sample_kb.json"))
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts/owner_harm_eval/tpr_ablations"))
    args = parser.parse_args()
    summary = run_ablations(
        code_gate_result_json=args.code_gate_result_json,
        agentharm_root=args.agentharm_root,
        code_kb=args.code_kb,
        output_dir=args.output_dir,
    )
    print(f"output_dir={args.output_dir}")
    print(f"best_under_budget={summary.get('best_under_budget')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
