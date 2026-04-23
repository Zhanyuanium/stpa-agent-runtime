from __future__ import annotations

import argparse
import json
import subprocess
import time
from pathlib import Path

from datasets import load_dataset


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _load_with_retry(dataset_name: str, *, config: str | None, retries: int, sleep_seconds: float):
    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            if config:
                return load_dataset(dataset_name, config)
            return load_dataset(dataset_name)
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            if attempt == retries:
                break
            time.sleep(sleep_seconds)
    raise RuntimeError(f"failed to load dataset '{dataset_name}' after {retries} attempts: {last_error}") from last_error


def fetch_mbpp(output_root: Path, *, retries: int, sleep_seconds: float) -> Path:
    ds = _load_with_retry("google-research-datasets/mbpp", config="full", retries=retries, sleep_seconds=sleep_seconds)
    rows: list[dict] = []
    for split_name in ("train", "validation", "test"):
        split = ds.get(split_name)
        if split is None:
            continue
        for item in split:
            code = (item.get("code") or "").strip()
            if not code:
                continue
            rows.append(
                {
                    "Index": f"mbpp_{split_name}_{item.get('task_id', len(rows))}",
                    "split": split_name,
                    "Prompt": item.get("text") or "",
                    "Code": code,
                    "expected_result": "success",
                    "Text_summary": "MBPP safe coding sample.",
                }
            )
    out_path = output_root / "MBPP" / "mbpp_code_samples.json"
    _write_json(out_path, rows)
    return out_path


def fetch_agentharm(output_root: Path, *, retries: int, sleep_seconds: float) -> Path:
    rows: list[dict] = []
    configs = ["harmful", "harmless_benign", "chat"]
    for config in configs:
        ds = _load_with_retry("ai-safety-institute/AgentHarm", config=config, retries=retries, sleep_seconds=sleep_seconds)
        for split_name, split in ds.items():
            for idx, item in enumerate(split):
                rows.append(
                    {
                        "id": item.get("id") or item.get("task_id") or f"{config}_{split_name}_{idx}",
                        "config": config,
                        "split": split_name,
                        "category": item.get("category") or item.get("harm_category") or "unknown",
                        "prompt": item.get("prompt") or item.get("instruction") or "",
                        "tool": item.get("tool") or item.get("tool_name") or "",
                        "is_harmful": bool(item.get("is_harmful", item.get("harmful", config == "harmful"))),
                    }
                )
    out_path = output_root / "AgentHarm" / "agentharm_samples.json"
    _write_json(out_path, rows)
    return out_path


def _extract_shell_commands_from_line(line: str) -> str | None:
    text = line.strip()
    if not text:
        return None
    if text.startswith("#"):
        return None
    if text in {"do", "done", "then", "fi", "esac", "{" , "}"}:
        return None
    banned_fragments = [
        "rm -rf",
        "mkfs",
        "dd if=",
        "shutdown",
        "reboot",
        ":(){",
        "chmod 777",
        "sudo ",
    ]
    lower = text.lower()
    if any(frag in lower for frag in banned_fragments):
        return None
    return text


def fetch_shellbench(output_root: Path, *, retries: int, sleep_seconds: float) -> Path:
    root = output_root / "ShellBench"
    raw_dir = root / "raw"
    if not raw_dir.exists():
        last_error: Exception | None = None
        for attempt in range(1, retries + 1):
            try:
                subprocess.run(
                    ["git", "clone", "--depth", "1", "https://github.com/shellspec/shellbench.git", str(raw_dir)],
                    check=True,
                    capture_output=True,
                    text=True,
                )
                last_error = None
                break
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                if attempt == retries:
                    break
                time.sleep(sleep_seconds)
        if last_error is not None:
            raise RuntimeError(f"failed to clone shellbench after {retries} attempts: {last_error}") from last_error

    commands: list[dict] = []
    sample_dir = raw_dir / "sample"
    for file in sorted(sample_dir.glob("*")):
        if not file.is_file():
            continue
        for idx, line in enumerate(file.read_text(encoding="utf-8", errors="ignore").splitlines()):
            cmd = _extract_shell_commands_from_line(line)
            if cmd is None:
                continue
            commands.append(
                {
                    "Index": f"shellbench_{file.stem}_{idx}",
                    "source_file": file.name,
                    "command": cmd,
                    "expected_result": "success",
                    "Text_summary": "ShellBench safe command candidate.",
                }
            )
    out_path = root / "shellbench_safe_commands.json"
    _write_json(out_path, commands)
    return out_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch MBPP, ShellBench, and AgentHarm datasets.")
    parser.add_argument("--output-root", type=Path, default=Path("benchmarks"))
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--sleep-seconds", type=float, default=2.0)
    args = parser.parse_args()

    mbpp_path = fetch_mbpp(args.output_root, retries=args.retries, sleep_seconds=args.sleep_seconds)
    shellbench_path = fetch_shellbench(args.output_root, retries=args.retries, sleep_seconds=args.sleep_seconds)
    agentharm_path = fetch_agentharm(args.output_root, retries=args.retries, sleep_seconds=args.sleep_seconds)
    print(f"mbpp_json={mbpp_path}")
    print(f"shellbench_json={shellbench_path}")
    print(f"agentharm_json={agentharm_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
