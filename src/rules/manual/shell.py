from __future__ import annotations

import re
from pathlib import Path

from agentspec_codegen.predicates.os_checks import (
    has_backup_for_target,
    is_network_target_untrusted,
    is_permission_change_risky,
    is_sensitive_path,
)
from agentspec_codegen.shell_parser import extract_command_features


def _as_text(tool_input: object) -> str:
    if tool_input is None:
        return ""
    return str(tool_input)


def shell_is_destructive_delete(user_input, tool_input, intermediate_steps) -> bool:
    cmd = _as_text(tool_input)
    parsed = extract_command_features(cmd)
    return "destructive_delete" in parsed.risk_flags


def shell_touches_sensitive_path(user_input, tool_input, intermediate_steps) -> bool:
    cmd = _as_text(tool_input)
    parsed = extract_command_features(cmd)
    return any(is_sensitive_path(path) for path in parsed.paths)


def shell_requires_privilege(user_input, tool_input, intermediate_steps) -> bool:
    cmd = _as_text(tool_input).lower()
    return bool(re.search(r"\b(sudo|su)\b", cmd))


def shell_missing_change_ticket(user_input, tool_input, intermediate_steps) -> bool:
    """Simple governance gate: require CHG- ticket marker in request."""
    prompt = _as_text(user_input)
    return "chg-" not in prompt.lower()


def shell_modifies_profile_startup(user_input, tool_input, intermediate_steps) -> bool:
    cmd = _as_text(tool_input).lower()
    profile_markers = [".bashrc", ".zshrc", "/etc/profile", "/etc/bash.bashrc"]
    return any(marker in cmd for marker in profile_markers)


def shell_untrusted_network_target(user_input, tool_input, intermediate_steps) -> bool:
    return is_network_target_untrusted(_as_text(tool_input))


def shell_permission_change_risky(user_input, tool_input, intermediate_steps) -> bool:
    return is_permission_change_risky(_as_text(tool_input))


def shell_target_has_backup(user_input, tool_input, intermediate_steps) -> bool:
    cmd = _as_text(tool_input)
    parsed = extract_command_features(cmd)
    for path in parsed.paths:
        if has_backup_for_target(path):
            return True
    return False


# Grammar-compatible predicate names (existing tokens) are mapped to shell-aware logic.
def destuctive_os_inst(user_input, tool_input, intermediate_steps) -> bool:
    cmd = _as_text(tool_input)
    return bool(re.search(r"\b(rm|unlink)\b", cmd)) or shell_is_destructive_delete(
        user_input, tool_input, intermediate_steps
    )


def involve_system_file(user_input, tool_input, intermediate_steps) -> bool:
    cmd = _as_text(tool_input)
    parsed = extract_command_features(cmd)
    return any(is_sensitive_path(path) for path in parsed.paths)


def is_improper_execution_privilege_code(user_input, tool_input, intermediate_steps) -> bool:
    cmd = _as_text(tool_input)
    return shell_requires_privilege(user_input, tool_input, intermediate_steps) or shell_permission_change_risky(
        user_input, cmd, intermediate_steps
    )


def involve_bash_rc(user_input, tool_input, intermediate_steps) -> bool:
    return shell_modifies_profile_startup(user_input, tool_input, intermediate_steps)


shell_predicates = {
    "shell_is_destructive_delete": shell_is_destructive_delete,
    "shell_touches_sensitive_path": shell_touches_sensitive_path,
    "shell_requires_privilege": shell_requires_privilege,
    "shell_missing_change_ticket": shell_missing_change_ticket,
    "shell_modifies_profile_startup": shell_modifies_profile_startup,
    "shell_untrusted_network_target": shell_untrusted_network_target,
    "shell_permission_change_risky": shell_permission_change_risky,
    "shell_target_has_backup": shell_target_has_backup,
    # parser-compatible overrides
    "destuctive_os_inst": destuctive_os_inst,
    "involve_system_file": involve_system_file,
    "is_improper_execution_privilege_code": is_improper_execution_privilege_code,
    "involve_bash_rc": involve_bash_rc,
}
