#!/usr/bin/env python3
"""Phase 2: run shell microbench with Python-delegate baseline vs optimized (default).

Writes ``artifacts/perf/shell_microbench_compare.json`` with both summaries.
Baseline: ``AGENTSPEC_SHELL_SHORTCIRCUIT_PY=0`` (always evaluate Python-domain predicates first).
Optimized: ``AGENTSPEC_SHELL_SHORTCIRCUIT_PY=1`` (default; skip Python predicates on obvious shell text).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _run(out: Path, shortcircuit: str) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["AGENTSPEC_SHELL_SHORTCIRCUIT_PY"] = shortcircuit
    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "run_overhead_microbench.py"),
        "--domain",
        "shell",
        "--output-dir",
        str(out),
        "--max-per-category",
        "3",
        "--repeats",
        "5",
    ]
    subprocess.run(cmd, cwd=ROOT, env=env, check=True)
    return json.loads((out / "microbench_summary.json").read_text(encoding="utf-8"))


def main() -> int:
    base_dir = ROOT / "artifacts" / "perf" / "shell_microbench_baseline"
    opt_dir = ROOT / "artifacts" / "perf" / "shell_microbench_optimized"
    before = _run(base_dir, "0")
    after = _run(opt_dir, "1")
    merged = {
        "baseline_AGENTSPEC_SHELL_SHORTCIRCUIT_PY_0": before,
        "optimized_AGENTSPEC_SHELL_SHORTCIRCUIT_PY_1": after,
    }
    dest = ROOT / "artifacts" / "perf" / "shell_microbench_compare.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
