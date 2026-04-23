from __future__ import annotations

import json

from scripts.verify_dataset import verify_benign_dataset, verify_current_eval_manifest, verify_redcode_root


def test_verify_dataset_success(tmp_path) -> None:
    root = tmp_path / "py2text_dataset_json"
    root.mkdir()
    (root / "index1_30_codes_full.json").write_text(json.dumps([{"Code": "print(1)"}]), encoding="utf-8")
    ok, msg = verify_redcode_root(root)
    assert ok
    assert "ok" in msg


def test_verify_benign_dataset_success(tmp_path) -> None:
    benign = tmp_path / "benign.json"
    benign.write_text(json.dumps([{"command": "ls -la"}]), encoding="utf-8")
    ok, msg = verify_benign_dataset(benign)
    assert ok
    assert "benign" in msg


def test_verify_current_eval_manifest_success(tmp_path) -> None:
    code = tmp_path / "code.json"
    shell = tmp_path / "shell.json"
    code.write_text("[]", encoding="utf-8")
    shell.write_text("[]", encoding="utf-8")
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "risky_code_count": 10,
                "risky_shell_count": 10,
                "safe_code_count": 10,
                "safe_shell_count": 10,
                "code_safe_output": str(code),
                "shell_safe_output": str(shell),
            }
        ),
        encoding="utf-8",
    )
    ok, msg = verify_current_eval_manifest(manifest)
    assert ok
    assert "manifest" in msg
