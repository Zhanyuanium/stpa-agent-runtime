from __future__ import annotations

import json
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
    assert result["metrics"]["total_cases"] == 2
