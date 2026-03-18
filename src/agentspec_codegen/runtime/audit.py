from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class RuleAuditRecord(BaseModel):
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    rule_id: str
    event: str
    action_name: str
    enforce_result: str
    detail: str = ""
    shellcheck_summary: dict[str, Any] | None = None


class RuleRuntimeContext(BaseModel):
    predicate_cache: dict[str, bool] = Field(default_factory=dict)
    audits: list[RuleAuditRecord] = Field(default_factory=list)

    def get_cached_predicate(self, key: str) -> bool | None:
        return self.predicate_cache.get(key)

    def set_cached_predicate(self, key: str, value: bool) -> None:
        self.predicate_cache[key] = value

    def add_audit(self, record: RuleAuditRecord) -> None:
        self.audits.append(record)
