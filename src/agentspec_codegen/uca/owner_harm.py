from __future__ import annotations

from enum import Enum


class OwnerHarmCategory(str, Enum):
    C1_CREDENTIAL_LEAK = "credential_leak"
    C2_INFRASTRUCTURE_EXPOSURE = "infrastructure_exposure"
    C3_PRIVACY_EXPOSURE = "privacy_exposure"
    C4_INNER_CIRCLE_LEAK = "inner_circle_leak"
    C5_ASSET_DESTRUCTION = "asset_destruction"
    C6_EXFILTRATION_VIA_TOOLS = "exfiltration_via_tools"
    C7_HIJACKING = "hijacking"
    C8_UNAUTHORIZED_AUTONOMY = "unauthorized_autonomy"


_RISK_TO_OWNER_HARM: dict[str, OwnerHarmCategory] = {
    "network_exfiltration": OwnerHarmCategory.C3_PRIVACY_EXPOSURE,
    "untrusted_post_request": OwnerHarmCategory.C6_EXFILTRATION_VIA_TOOLS,
    "sensitive_data_leak": OwnerHarmCategory.C3_PRIVACY_EXPOSURE,
    "startup_file_tamper": OwnerHarmCategory.C7_HIJACKING,
    "bashrc_alias_backdoor": OwnerHarmCategory.C7_HIJACKING,
    "privilege_retention": OwnerHarmCategory.C8_UNAUTHORIZED_AUTONOMY,
    "shell_destructive_delete": OwnerHarmCategory.C5_ASSET_DESTRUCTION,
    "shell_privilege_escalation": OwnerHarmCategory.C8_UNAUTHORIZED_AUTONOMY,
    "shell_profile_tamper": OwnerHarmCategory.C7_HIJACKING,
}


def normalize_owner_harm_category(value: str | None) -> OwnerHarmCategory | None:
    if value is None:
        return None
    candidate = value.strip().lower()
    for item in OwnerHarmCategory:
        if item.value == candidate:
            return item
    raise ValueError(f"unsupported owner_harm_category: {value}")


def map_owner_harm_category(
    *,
    risk_type: str | None,
    explicit: str | None = None,
) -> OwnerHarmCategory | None:
    if explicit is not None:
        return normalize_owner_harm_category(explicit)
    if risk_type is None:
        return None
    return _RISK_TO_OWNER_HARM.get(risk_type.strip().lower())
