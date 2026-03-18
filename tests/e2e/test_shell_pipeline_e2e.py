from __future__ import annotations

from pathlib import Path

from scripts.run_agent_experiment import run_model_in_loop


def test_shell_pipeline_e2e() -> None:
    result = run_model_in_loop(
        shell_kb_path=Path("data/uca/shell/shell_kb.json"),
        risky_json=Path("benchmarks/shell/risky_commands.json"),
        benign_json=Path("benchmarks/shell/benign_commands.json"),
        artifact_root=Path("artifacts/shell_eval/e2e"),
    )
    assert result["mode"] == "model_in_loop"
    assert result["metrics"]["total_cases"] >= 3
    assert "interception_rate" in result["metrics"]
    assert "artifact_root" in result
