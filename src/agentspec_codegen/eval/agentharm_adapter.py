from __future__ import annotations

import json
from pathlib import Path


def _is_harmful(item: dict) -> bool:
    if "is_harmful" in item:
        return bool(item["is_harmful"])
    if "harmful" in item:
        return bool(item["harmful"])
    label = str(item.get("label", "")).strip().lower()
    if label in {"harmful", "unsafe", "attack", "malicious", "1", "true"}:
        return True
    if label in {"benign", "safe", "0", "false"}:
        return False
    split = str(item.get("split", "")).strip().lower()
    if split in {"harmful", "unsafe", "attack", "risky"}:
        return True
    return False


def _extract_text(item: dict) -> str:
    candidates = [
        item.get("action"),
        item.get("action_text"),
        item.get("tool_call"),
        item.get("prompt"),
        item.get("instruction"),
        item.get("input"),
        item.get("content"),
    ]
    for value in candidates:
        if value is not None and str(value).strip():
            return str(value)
    return ""


def _extract_category(item: dict, fallback: str) -> str:
    for key in ("category", "harm_category", "attack_type", "suite"):
        value = item.get(key)
        if value is not None and str(value).strip():
            return str(value)
    return fallback


def _load_file(path: Path) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        return [x for x in payload if isinstance(x, dict)]
    if isinstance(payload, dict):
        for key in ("items", "cases", "data", "examples"):
            value = payload.get(key)
            if isinstance(value, list):
                return [x for x in value if isinstance(x, dict)]
    return []


def load_agentharm_cases(agentharm_root: Path) -> list[dict]:
    files: list[Path] = []
    if agentharm_root.is_dir():
        files = sorted(agentharm_root.glob("*.json"))
    elif agentharm_root.exists():
        files = [agentharm_root]
    cases: list[dict] = []
    for file in files:
        rows = _load_file(file)
        for idx, item in enumerate(rows):
            case_id = (
                str(item.get("case_id"))
                or str(item.get("id"))
                or f"{file.stem}:{idx}"
            )
            is_risky = _is_harmful(item)
            cases.append(
                {
                    "case_id": f"agentharm:{case_id}",
                    "category": _extract_category(item, file.stem),
                    "input": _extract_text(item),
                    "is_risky": is_risky,
                    "source": "agentharm",
                }
            )
    return cases
