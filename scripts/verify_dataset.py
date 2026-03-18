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


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify local RedCode dataset layout.")
    parser.add_argument("--redcode-root", required=True, type=Path)
    args = parser.parse_args()

    ok, message = verify_redcode_root(args.redcode_root)
    print(message)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
