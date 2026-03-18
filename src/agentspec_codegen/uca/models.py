from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .mitre import normalize_tactic, tactic_supported_for_risk


class UcaRiskType(str, Enum):
    NETWORK_EXFILTRATION = "network_exfiltration"
    UNTRUSTED_POST_REQUEST = "untrusted_post_request"
    SENSITIVE_DATA_LEAK = "sensitive_data_leak"
    STARTUP_FILE_TAMPER = "startup_file_tamper"
    BASHRC_ALIAS_BACKDOOR = "bashrc_alias_backdoor"
    PRIVILEGE_RETENTION = "privilege_retention"
    SHELL_DESTRUCTIVE_DELETE = "shell_destructive_delete"
    SHELL_PRIVILEGE_ESCALATION = "shell_privilege_escalation"
    SHELL_PROFILE_TAMPER = "shell_profile_tamper"


class UcaDomain(str, Enum):
    CODE = "code"
    SHELL = "shell"


class UcaEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    uca_id: str = Field(min_length=3, max_length=64)
    title: str = Field(min_length=3, max_length=200)
    domain: UcaDomain = UcaDomain.CODE
    risk_type: UcaRiskType
    mitre_tactic: str
    trigger_event: str = Field(min_length=1)
    predicate_hints: list[str] = Field(default_factory=list)
    enforcement: str = Field(default="stop", min_length=1)
    rationale: str = Field(min_length=5)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _validate_mitre_mapping(self) -> "UcaEntry":
        tactic = normalize_tactic(self.mitre_tactic)
        if not tactic_supported_for_risk(tactic, self.risk_type.value):
            raise ValueError(
                f"risk_type '{self.risk_type.value}' is not mapped to tactic '{self.mitre_tactic}'"
            )
        self.mitre_tactic = tactic
        return self


class UcaKnowledgeBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: str = Field(min_length=1)
    entries: list[UcaEntry] = Field(default_factory=list)

    @model_validator(mode="after")
    def _unique_uca_id(self) -> "UcaKnowledgeBase":
        ids = [e.uca_id for e in self.entries]
        duplicates = {i for i in ids if ids.count(i) > 1}
        if duplicates:
            names = ", ".join(sorted(duplicates))
            raise ValueError(f"duplicate uca_id found: {names}")
        return self
