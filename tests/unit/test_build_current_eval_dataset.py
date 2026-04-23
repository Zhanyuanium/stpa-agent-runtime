from __future__ import annotations

import json

from scripts.build_current_eval_dataset import build_current_eval_dataset


def test_build_current_eval_dataset_balanced_counts(tmp_path) -> None:
    code_root = tmp_path / "py2text_dataset_json"
    shell_root = tmp_path / "bash2text_dataset_json"
    code_root.mkdir()
    shell_root.mkdir()
    (code_root / "index1_30_codes_full.json").write_text(
        json.dumps([{"Code": "print(1)"}, {"Code": "print(2)"}]),
        encoding="utf-8",
    )
    (shell_root / "index1_30_codes_full_upd.json").write_text(
        json.dumps([{"Code": "ls -la"}, {"Code": "pwd"}, {"Code": "echo ok"}]),
        encoding="utf-8",
    )
    mbpp = tmp_path / "mbpp.json"
    shellbench = tmp_path / "shellbench.json"
    mbpp.write_text(
        json.dumps([{"Code": "def a():\n    return 1"}, {"Code": "def b():\n    return 2"}]),
        encoding="utf-8",
    )
    shellbench.write_text(
        json.dumps([{"command": "ls"}, {"command": "pwd"}]),
        encoding="utf-8",
    )
    out_dir = tmp_path / "current_eval"
    manifest = build_current_eval_dataset(
        redcode_code_root=code_root,
        redcode_shell_root=shell_root,
        mbpp_json=mbpp,
        shellbench_json=shellbench,
        output_dir=out_dir,
        seed=42,
    )
    assert manifest["risky_code_count"] == 2
    assert manifest["risky_shell_count"] == 3
    assert manifest["safe_code_count"] == 2
    assert manifest["safe_shell_count"] == 3
    assert (out_dir / "code_safe_equal_mbpp.json").exists()
    assert (out_dir / "shell_safe_equal_shellbench.json").exists()
