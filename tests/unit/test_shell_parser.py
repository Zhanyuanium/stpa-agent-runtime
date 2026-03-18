from __future__ import annotations

from agentspec_codegen.shell_parser import (
    extract_command_features,
    run_shellcheck,
    ensure_shellcheck_run,
    get_shellcheck_summary_for_audit,
)


def test_extract_command_features_detects_risky_flags() -> None:
    parsed = extract_command_features("sudo rm -rf /etc/nginx")
    assert parsed.binaries == ["sudo"]
    assert "destructive_delete" in parsed.risk_flags
    assert "privilege_command" in parsed.risk_flags
    assert "sensitive_path" in parsed.risk_flags


def test_extract_command_features_handles_malformed_input() -> None:
    parsed = extract_command_features("echo 'unterminated")
    assert parsed.argv
    assert parsed.raw.startswith("echo")


def test_shellcheck_wrapper_graceful_fallback() -> None:
    result = run_shellcheck("echo hello")
    # On systems without shellcheck, unavailable=False is expected and should not crash.
    assert isinstance(result.diagnostics, list)


def test_ensure_shellcheck_run_and_summary_for_audit() -> None:
    ensure_shellcheck_run("echo hello")
    summary = get_shellcheck_summary_for_audit()
    assert summary is not None
    assert "available" in summary
    assert "diagnostic_count" in summary
    assert "level_counts" in summary
    assert "stderr" in summary
    assert summary["level_counts"]["error"] >= 0
    assert summary["level_counts"]["warning"] >= 0
    assert summary["level_counts"]["info"] >= 0
    # Second call returns None (cleared after consume)
    assert get_shellcheck_summary_for_audit() is None


def test_ensure_shellcheck_run_empty_command_no_store() -> None:
    ensure_shellcheck_run("")
    summary = get_shellcheck_summary_for_audit()
    assert summary is None
