from __future__ import annotations

import argparse
import json
import random
from pathlib import Path


def _load_json(path: Path) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError(f"expected list json: {path}")
    return [item for item in payload if isinstance(item, dict)]


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _count_redcode_samples(root: Path, pattern: str) -> int:
    total = 0
    for file in sorted(root.glob(pattern)):
        data = _load_json(file)
        total += len(data)
    return total


def _sample_with_replacement(rows: list[dict], target_count: int, *, seed: int) -> list[dict]:
    if not rows:
        raise ValueError("cannot sample from empty rows")
    rng = random.Random(seed)
    sampled: list[dict] = []
    for i in range(target_count):
        sampled.append(dict(rng.choice(rows), __sample_index=i))
    return sampled


def _normalize_mbpp_rows(rows: list[dict], target_count: int, *, seed: int) -> list[dict]:
    cleaned = []
    for row in rows:
        code = (row.get("Code") or row.get("code") or "").strip()
        if not code:
            continue
        cleaned.append(
            {
                "Code": code,
                "Prompt": row.get("Prompt") or row.get("prompt") or "",
                "expected_result": "success",
                "Text_summary": "MBPP safe coding sample.",
            }
        )
    sampled = _sample_with_replacement(cleaned, target_count, seed=seed)
    output: list[dict] = []
    for i, row in enumerate(sampled, start=1):
        output.append(
            {
                "Index": f"mbpp_safe_{i:04d}",
                "Prompt": row["Prompt"],
                "Language": "python",
                "Code": row["Code"],
                "expected_result": row["expected_result"],
                "Text_summary": row["Text_summary"],
            }
        )
    return output


def _normalize_shellbench_rows(rows: list[dict], target_count: int, *, seed: int) -> list[dict]:
    cleaned = []
    for row in rows:
        command = (row.get("command") or row.get("Code") or row.get("code") or "").strip()
        if not command:
            continue
        cleaned.append(
            {
                "command": command,
                "source_file": row.get("source_file") or "unknown",
                "expected_result": "success",
                "Text_summary": "ShellBench safe shell sample.",
            }
        )
    sampled = _sample_with_replacement(cleaned, target_count, seed=seed)
    output: list[dict] = []
    for i, row in enumerate(sampled, start=1):
        output.append(
            {
                "Index": f"shellbench_safe_{i:04d}",
                "Prompt": "",
                "Language": "bash",
                "Code": row["command"],
                "command": row["command"],
                "expected_result": row["expected_result"],
                "Text_summary": row["Text_summary"],
                "source_file": row["source_file"],
            }
        )
    return output


def build_current_eval_dataset(
    *,
    redcode_code_root: Path,
    redcode_shell_root: Path,
    mbpp_json: Path,
    shellbench_json: Path,
    output_dir: Path,
    seed: int,
) -> dict:
    risky_code_count = _count_redcode_samples(redcode_code_root, "index*_30_codes_full*.json")
    risky_shell_count = _count_redcode_samples(redcode_shell_root, "*.json")

    code_safe = _normalize_mbpp_rows(_load_json(mbpp_json), risky_code_count, seed=seed)
    shell_safe = _normalize_shellbench_rows(_load_json(shellbench_json), risky_shell_count, seed=seed + 1)

    code_safe_path = output_dir / "code_safe_equal_mbpp.json"
    shell_safe_path = output_dir / "shell_safe_equal_shellbench.json"
    manifest_path = output_dir / "current_eval_manifest.json"
    _write_json(code_safe_path, code_safe)
    _write_json(shell_safe_path, shell_safe)
    manifest = {
        "seed": seed,
        "risky_code_count": risky_code_count,
        "risky_shell_count": risky_shell_count,
        "safe_code_count": len(code_safe),
        "safe_shell_count": len(shell_safe),
        "code_safe_source": str(mbpp_json),
        "shell_safe_source": str(shellbench_json),
        "code_safe_output": str(code_safe_path),
        "shell_safe_output": str(shell_safe_path),
    }
    _write_json(manifest_path, manifest)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Build balanced current-eval safe dataset from MBPP/ShellBench.")
    parser.add_argument(
        "--redcode-code-root",
        type=Path,
        default=Path("benchmarks/RedCode-Exec/py2text_dataset_json"),
    )
    parser.add_argument(
        "--redcode-shell-root",
        type=Path,
        default=Path("benchmarks/RedCode-Exec/bash2text_dataset_json"),
    )
    parser.add_argument(
        "--mbpp-json",
        type=Path,
        default=Path("benchmarks/MBPP/mbpp_code_samples.json"),
    )
    parser.add_argument(
        "--shellbench-json",
        type=Path,
        default=Path("benchmarks/ShellBench/shellbench_safe_commands.json"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("benchmarks/current_eval"),
    )
    parser.add_argument("--seed", type=int, default=20260423)
    args = parser.parse_args()
    manifest = build_current_eval_dataset(
        redcode_code_root=args.redcode_code_root,
        redcode_shell_root=args.redcode_shell_root,
        mbpp_json=args.mbpp_json,
        shellbench_json=args.shellbench_json,
        output_dir=args.output_dir,
        seed=args.seed,
    )
    print(f"manifest={args.output_dir / 'current_eval_manifest.json'}")
    print(f"safe_code={manifest['safe_code_count']}")
    print(f"safe_shell={manifest['safe_shell_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
