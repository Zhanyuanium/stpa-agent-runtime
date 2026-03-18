from __future__ import annotations

from typing import Final

ATTACK_TACTIC_TO_RISKS: Final[dict[str, set[str]]] = {
    "exfiltration": {"network_exfiltration", "untrusted_post_request", "sensitive_data_leak"},
    "persistence": {
        "startup_file_tamper",
        "bashrc_alias_backdoor",
        "privilege_retention",
        "shell_profile_tamper",
    },
    "privilege_escalation": {"shell_privilege_escalation"},
    "impact": {"shell_destructive_delete"},
}


def normalize_tactic(tactic: str) -> str:
    """Normalize ATT&CK tactic names for stable matching."""
    return tactic.strip().lower().replace(" ", "_")


def tactic_supported_for_risk(tactic: str, risk_type: str) -> bool:
    normalized_tactic = normalize_tactic(tactic)
    return risk_type in ATTACK_TACTIC_TO_RISKS.get(normalized_tactic, set())
