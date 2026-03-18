from __future__ import annotations

import json
import subprocess
import sys
import pytest
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
    )
    assert result["mode"] == "model_in_loop"
    assert result["backend"] == "heuristic"
    assert result["metrics"]["total_cases"] == 2
    assert len(result["cases"]) == 2
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
    )
    assert result["metrics"]["total_cases"] == 1
    assert result["cases"][0]["case_id"].startswith("risky:index1_30_codes_full_upd:")


def test_run_model_in_loop_heuristic_backend_explicit(tmp_path) -> None:
    risky = tmp_path / "risky.json"
    risky.write_text(json.dumps([{"command": "ls -la"}]), encoding="utf-8")
    result = run_model_in_loop(
        shell_kb_path=Path("data/uca/shell/shell_kb.json"),
        risky_json=risky,
        benign_json=None,
        backend="heuristic",
    )
    assert result["backend"] == "heuristic"
    assert result["metrics"]["total_cases"] == 1


def test_run_model_in_loop_unknown_backend_raises(tmp_path) -> None:
    risky = tmp_path / "risky.json"
    risky.write_text(json.dumps([{"command": "ls"}]), encoding="utf-8")
    with pytest.raises(ValueError, match="Unknown backend"):
        run_model_in_loop(
            shell_kb_path=Path("data/uca/shell/shell_kb.json"),
            risky_json=risky,
            benign_json=None,
            backend="invalid",
        )


def test_run_model_in_loop_model_backend_no_api_key_raises(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    risky = tmp_path / "risky.json"
    risky.write_text(json.dumps([{"command": "ls"}]), encoding="utf-8")
    with pytest.raises(SystemExit):
        run_model_in_loop(
            shell_kb_path=Path("data/uca/shell/shell_kb.json"),
            risky_json=risky,
            benign_json=None,
            backend="model",
        )


def test_run_model_in_loop_model_backend_custom_env_missing_raises(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("VENDOR_API_KEY", raising=False)
    risky = tmp_path / "risky.json"
    risky.write_text(json.dumps([{"command": "ls"}]), encoding="utf-8")
    with pytest.raises(SystemExit):
        run_model_in_loop(
            shell_kb_path=Path("data/uca/shell/shell_kb.json"),
            risky_json=risky,
            benign_json=None,
            backend="model",
            api_key_env="VENDOR_API_KEY",
            api_base_url="https://vendor.example/v1",
        )


def test_cli_help_contains_backend_options() -> None:
    root = Path(__file__).resolve().parents[2]
    proc = subprocess.run(
        [sys.executable, "-m", "scripts.run_agent_experiment", "--help"],
        capture_output=True,
        text=True,
        cwd=root,
    )
    assert proc.returncode == 0
    out = proc.stdout + proc.stderr
    assert "--backend" in out
    assert "heuristic" in out
    assert "model" in out
    assert "--model" in out
    assert "--api-base-url" in out
    assert "--api-key-env" in out
