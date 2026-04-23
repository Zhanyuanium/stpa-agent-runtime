from __future__ import annotations

import argparse
import json
from pathlib import Path


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _metrics_row(name: str, payload: dict) -> str:
    m = payload["metrics"]
    return (
        f"| {name} | {m['interception_rate']:.4f} | {m['false_positive_rate']:.4f} | "
        f"{m['task_completion_rate']:.4f} | {m['avg_overhead_ms']:.2f} |"
    )


def _collect_failure_clusters(payload: dict, top_k: int = 5) -> list[tuple[str, int]]:
    counter: dict[str, int] = {}
    for case in payload.get("cases", []):
        if not case.get("is_risky", False):
            continue
        if not case.get("blocked", False):
            continue
        rules = ((case.get("post_audit") or {}).get("triggered_rules")) or []
        if not rules:
            rules = ["gate_only_block"]
        for rule in rules:
            counter[rule] = counter.get(rule, 0) + 1
    return sorted(counter.items(), key=lambda x: x[1], reverse=True)[:top_k]


def _render_cluster_table(title: str, payload: dict) -> str:
    rows = _collect_failure_clusters(payload)
    if not rows:
        return f"### {title}\n\n无可统计失败簇。\n"
    lines = [f"### {title}", "", "| failure_cluster | count |", "|---|---:|"]
    for name, count in rows:
        lines.append(f"| {name} | {count} |")
    lines.append("")
    return "\n".join(lines)


def _delta(gate: dict, post: dict) -> tuple[float, float]:
    gate_metrics = gate["metrics"]
    post_metrics = post["metrics"]
    return (
        float(post_metrics["interception_rate"]) - float(gate_metrics["interception_rate"]),
        float(post_metrics["false_positive_rate"]) - float(gate_metrics["false_positive_rate"]),
    )


def _render_ablation_summary(path: Path | None) -> list[str]:
    if path is None or not path.exists():
        return []
    payload = _load(path)
    best = payload.get("best_under_budget")
    if not best:
        return []
    lines = [
        "## 预算内消融最优配置",
        "",
        f"- 最优配置：`{best.get('name')}`",
        f"- 最优后验 TPR：`{best.get('post_tpr'):.4f}`",
        f"- 最优后验 FPR：`{best.get('post_fpr'):.4f}`",
        f"- FPR 预算上限：`{payload.get('fpr_budget_absolute'):.4f}`",
        "",
    ]
    return lines


def export_report(
    *,
    baseline_dir: Path,
    unified_summary_json: Path,
    output_md: Path,
    ablation_summary_json: Path | None = None,
) -> Path:
    baseline = _load(baseline_dir / "baseline_result.json")
    manual = _load(baseline_dir / "manual_result.json")
    generated = _load(baseline_dir / "generated_result.json")
    unified = _load(unified_summary_json)

    current_gate = unified["current_code_gate_only"]
    current_full = unified["current_code_post_audit_full"]
    agentharm_gate = unified.get("agentharm_gate_only")
    agentharm_full = unified.get("agentharm_post_audit_full")
    d_current_tpr, d_current_fpr = _delta(current_gate, current_full)
    d_agentharm_tpr = d_agentharm_fpr = 0.0
    if agentharm_gate and agentharm_full:
        d_agentharm_tpr, d_agentharm_fpr = _delta(agentharm_gate, agentharm_full)

    lines = [
        "# Owner-Harm 融合实验报告（自动汇总）",
        "",
        "## 当前数据集主结果",
        "",
        "| setting | interception | false_positive | completion | overhead_ms |",
        "|---|---:|---:|---:|---:|",
        _metrics_row("baseline_gate", baseline),
        _metrics_row("manual_gate", manual),
        _metrics_row("generated_gate", generated),
        _metrics_row("current_gate_only", current_gate),
        _metrics_row("current_post_audit_full", current_full),
        "",
        f"- Current TPR 增量（post-gate 相对 gate-only）: `{d_current_tpr:+.4f}`",
        f"- Current FPR 增量（post-gate 相对 gate-only）: `{d_current_fpr:+.4f}`",
        "",
        "## AgentHarm（Gate vs Post-Audit）",
        "",
    ]
    if agentharm_gate and agentharm_full:
        lines.extend(
            [
                "| setting | interception | false_positive | completion | overhead_ms |",
                "|---|---:|---:|---:|---:|",
                _metrics_row("agentharm_gate_only", agentharm_gate),
                _metrics_row("agentharm_post_audit_full", agentharm_full),
                "",
                f"- AgentHarm TPR 增量（post-gate 相对 gate-only）: `{d_agentharm_tpr:+.4f}`",
                f"- AgentHarm FPR 增量（post-gate 相对 gate-only）: `{d_agentharm_fpr:+.4f}`",
                "",
            ]
        )
    lines.extend(
        [
            "## FPR 根因与修复结论",
            "",
            "- 原始 FPR 激增主因：`is_buggy_ip_validation_code` 过宽，普通 benign 代码也被误判。",
            "- 修复动作：将该谓词改为“仅在 IP 校验语境下判定”，并收紧 regex/range 检查。",
            "- 数据集动作：引入 MBPP/ShellBench 等量 safe 与 RedCode risky 配平，降低小样本偏差。",
            "",
            _render_cluster_table("失败案例簇（current/full）", current_full),
        ]
    )
    lines.extend(_render_ablation_summary(ablation_summary_json))
    lines.extend(
        [
        "## 参考依据",
        "",
        "- Owner-Harm 论文摘要与实验表述：[arXiv:2604.18658](https://arxiv.org/abs/2604.18658)",
        "",
        ]
    )
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_md.write_text("\n".join(lines), encoding="utf-8")
    return output_md


def main() -> int:
    parser = argparse.ArgumentParser(description="Export owner-harm merged report markdown.")
    parser.add_argument("--baseline-dir", type=Path, required=True)
    parser.add_argument("--unified-summary-json", type=Path, required=True)
    parser.add_argument("--output-md", type=Path, required=True)
    parser.add_argument("--ablation-summary-json", type=Path, required=False, default=None)
    args = parser.parse_args()
    out = export_report(
        baseline_dir=args.baseline_dir,
        unified_summary_json=args.unified_summary_json,
        output_md=args.output_md,
        ablation_summary_json=args.ablation_summary_json,
    )
    print(f"owner_harm_report_md={out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
