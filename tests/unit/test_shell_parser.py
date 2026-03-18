from __future__ import annotations

from agentspec_codegen.shell_parser import extract_command_features, run_shellcheck


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
