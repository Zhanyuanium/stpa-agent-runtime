from __future__ import annotations

from src.rules.manual.pythonrepl import is_buggy_ip_validation_code


def test_is_buggy_ip_validation_code_returns_false_for_non_ip_command() -> None:
    assert is_buggy_ip_validation_code("", "ls -la /tmp", []) is False


def test_is_buggy_ip_validation_code_detects_permissive_ip_regex() -> None:
    snippet = r"import re\nre.match(r'\\d+\\.\\d+\\.\\d+\\.\\d+', ip)"
    assert is_buggy_ip_validation_code("", snippet, []) is True


def test_is_buggy_ip_validation_code_accepts_ipaddress_api_validation() -> None:
    snippet = "import ipaddress\nipaddress.ip_address(user_input)"
    assert is_buggy_ip_validation_code("", snippet, []) is False
