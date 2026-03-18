from __future__ import annotations

import json

from scripts.verify_dataset import verify_redcode_root


def test_verify_dataset_success(tmp_path) -> None:
    root = tmp_path / "py2text_dataset_json"
    root.mkdir()
    (root / "index1_30_codes_full.json").write_text(json.dumps([{"Code": "print(1)"}]), encoding="utf-8")
    ok, msg = verify_redcode_root(root)
    assert ok
    assert "ok" in msg
