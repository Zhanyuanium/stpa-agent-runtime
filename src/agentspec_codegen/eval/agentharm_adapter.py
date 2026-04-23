from __future__ import annotations

import json
from pathlib import Path

from agentspec_codegen.uca.owner_harm import OwnerHarmCategory


_AGENTHARM_TO_OWNER_HARM: dict[str, str] = {
    "cybercrime": OwnerHarmCategory.C2_INFRASTRUCTURE_EXPOSURE.value,
    "fraud": OwnerHarmCategory.C6_EXFILTRATION_VIA_TOOLS.value,
    "harassment": OwnerHarmCategory.C4_INNER_CIRCLE_LEAK.value,
    "disinformation": OwnerHarmCategory.C7_HIJACKING.value,
    "privacy": OwnerHarmCategory.C3_PRIVACY_EXPOSURE.value,
    "hate": OwnerHarmCategory.C4_INNER_CIRCLE_LEAK.value,
    "violence": OwnerHarmCategory.C8_UNAUTHORIZED_AUTONOMY.value,
    "weapons": OwnerHarmCategory.C8_UNAUTHORIZED_AUTONOMY.value,
}


def _map_owner_harm(category: str) -> str:
    key = category.strip().lower()
    return _AGENTHARM_TO_OWNER_HARM.get(key, "unknown")


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
            base_id = str(item.get("case_id") or item.get("id") or f"{file.stem}:{idx}")
            split = str(item.get("split") or "unknown")
            config = str(item.get("config") or "default")
            case_id = f"{config}:{split}:{base_id}"
            is_risky = _is_harmful(item)
            category = _extract_category(item, file.stem)
            text = _extract_text(item)
            cases.append(
                {
                    "case_id": f"agentharm:{case_id}",
                    "category": category,
                    "input": text,
                    "raw_instruction": text,
                    "normalized_input": text,
                    "is_risky": is_risky,
                    "source": "agentharm",
                    "owner_harm_category": _map_owner_harm(category),
                }
            )
    return cases
