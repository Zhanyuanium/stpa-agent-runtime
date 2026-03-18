from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from scripts.run_agent_experiment import run_model_in_loop


def test_run_model_in_loop_with_mock_shell_cases(tmp_path) -> None:
    risky = tmp_path / "risky.json"
    benign = tmp_path / "benign.json"
    risky.write_text(
        json.dumps([{"event": "TerminalExecute", "command": "sudo rm -rf /etc/nginx"}]),
        encoding="utf-8",
    )
    benign.write_text(
        json.dumps([{"event": "TerminalExecute", "command": "ls -la /tmp"}]),
        encoding="utf-8",
    )

    result = run_model_in_loop(
        shell_kb_path=Path("data/uca/shell/shell_kb.json"),
        risky_json=risky,
        benign_json=benign,
        artifact_root=tmp_path / "shell_artifacts",
    )
    assert result["mode"] == "model_in_loop"
    assert result["backend"] == "spec_runtime"
    assert result["metrics"]["total_cases"] == 2
    assert len(result["cases"]) == 2
    assert result["runtime_source"] == "spec_enforcement"
    assert result["compiled_rule_count"] >= 1
    artifact_root = Path(result["artifact_root"])
    assert (artifact_root / "01_uca_loaded.json").exists()
    assert (artifact_root / "02_compiled_specs").is_dir()
    assert (artifact_root / "02_compiled_manifest.json").exists()
    assert (artifact_root / "03_rules_parsed.json").exists()
    assert (artifact_root / "04_check_traces").is_dir()
    assert (artifact_root / "05_case_audits.jsonl").exists()
    for c in result["cases"]:
        assert "case_id" in c and "is_risky" in c and "blocked" in c and "fulfilled" in c and "overhead_ms" in c


def test_run_model_in_loop_with_risky_directory_and_code_field(tmp_path) -> None:
    risky_dir = tmp_path / "bash2text_dataset_json"
    risky_dir.mkdir()
    (risky_dir / "index1_30_codes_full_upd.json").write_text(
        json.dumps(
            [
                {
                    "Index": "1_1",
                    "Language": "bash",
                    "Code": "sudo rm -rf /etc/nginx",
                    "Text_summary": "dangerous command",
                }
            ]
        ),
        encoding="utf-8",
    )
    result = run_model_in_loop(
        shell_kb_path=Path("data/uca/shell/shell_kb.json"),
        risky_json=risky_dir,
        benign_json=None,
        artifact_root=tmp_path / "shell_artifacts_dir",
    )
    assert result["metrics"]["total_cases"] == 1
    assert result["cases"][0]["case_id"].startswith("risky:index1_30_codes_full_upd:")


def test_run_model_in_loop_without_backend_switch(tmp_path) -> None:
    risky = tmp_path / "risky.json"
    risky.write_text(json.dumps([{"command": "ls -la"}]), encoding="utf-8")
    result = run_model_in_loop(
        shell_kb_path=Path("data/uca/shell/shell_kb.json"),
        risky_json=risky,
        benign_json=None,
        artifact_root=tmp_path / "spec_runtime_artifacts",
    )
    assert result["backend"] == "spec_runtime"
    assert result["metrics"]["total_cases"] == 1


def test_cli_help_contains_strict_runtime_options() -> None:
    root = Path(__file__).resolve().parents[2]
    proc = subprocess.run(
        [sys.executable, "-m", "scripts.run_agent_experiment", "--help"],
        capture_output=True,
        text=True,
        cwd=root,
    )
    assert proc.returncode == 0
    out = proc.stdout + proc.stderr
    assert "--shell-kb" in out
    assert "--risky-json" in out
    assert "--artifact-root" in out
