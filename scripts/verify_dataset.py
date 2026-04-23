from __future__ import annotations

import argparse
import json
from pathlib import Path


def verify_redcode_root(root: Path) -> tuple[bool, str]:
    if not root.exists():
        return False, f"dataset root not found: {root}"
    files = list(root.glob("index*_30_codes_full.json"))
    if not files:
        return False, f"no RedCode category files found in: {root}"
    bad = []
    for file in files:
        try:
            data = json.loads(file.read_text(encoding="utf-8"))
            if not isinstance(data, list):
                bad.append(f"{file.name}: expected list")
        except Exception as exc:  # noqa: BLE001
            bad.append(f"{file.name}: {exc}")
    if bad:
        return False, "invalid files:\n" + "\n".join(bad)
    return True, f"ok ({len(files)} category files)"


def verify_benign_dataset(path: Path) -> tuple[bool, str]:
    if not path.exists():
        return False, f"benign dataset not found: {path}"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        return False, f"benign dataset parse failed: {exc}"
    if not isinstance(data, list):
        return False, "benign dataset must be a list"
    for idx, item in enumerate(data):
        if not isinstance(item, dict):
            return False, f"benign item {idx} must be dict"
        if not (item.get("Code") or item.get("code") or item.get("command")):
            return False, f"benign item {idx} missing Code/code/command field"
    return True, f"ok ({len(data)} benign samples)"


def verify_current_eval_manifest(path: Path) -> tuple[bool, str]:
    if not path.exists():
        return False, f"current eval manifest not found: {path}"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        return False, f"current eval manifest parse failed: {exc}"
    required = [
        "risky_code_count",
        "risky_shell_count",
        "safe_code_count",
        "safe_shell_count",
        "code_safe_output",
        "shell_safe_output",
    ]
    for key in required:
        if key not in payload:
            return False, f"current eval manifest missing key: {key}"
    for key in ("code_safe_output", "shell_safe_output"):
        target = Path(payload[key])
        if not target.exists():
            return False, f"referenced file not found: {target}"
    return True, "ok (current eval manifest)"


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify local RedCode dataset layout.")
    parser.add_argument("--redcode-root", required=True, type=Path)
    parser.add_argument("--benign-json", required=False, type=Path)
    parser.add_argument("--current-eval-manifest", required=False, type=Path)
    args = parser.parse_args()

    ok, message = verify_redcode_root(args.redcode_root)
    messages = [message]
    if args.benign_json:
        ok_benign, msg_benign = verify_benign_dataset(args.benign_json)
        ok = ok and ok_benign
        messages.append(msg_benign)
    if args.current_eval_manifest:
        ok_manifest, msg_manifest = verify_current_eval_manifest(args.current_eval_manifest)
        ok = ok and ok_manifest
        messages.append(msg_manifest)
    print("\n".join(messages))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
