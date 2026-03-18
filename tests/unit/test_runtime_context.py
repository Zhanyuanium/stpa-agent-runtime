from __future__ import annotations

from agentspec_codegen.runtime import RuleAuditRecord, RuleRuntimeContext


def test_rule_audit_record_shellcheck_summary_serializable() -> None:
    record = RuleAuditRecord(
        rule_id="r1",
        event="any",
        action_name="run_command",
        enforce_result="continue",
        detail="{}",
        shellcheck_summary={"available": True, "diagnostic_count": 0, "level_counts": {"error": 0, "warning": 0, "info": 0}, "stderr": ""},
    )
    assert record.shellcheck_summary is not None
    assert record.shellcheck_summary["available"] is True
    # Pydantic model is JSON-serializable
    j = record.model_dump()
    assert "shellcheck_summary" in j


def test_runtime_context_cache_and_audit() -> None:
    ctx = RuleRuntimeContext()
    assert ctx.get_cached_predicate("k") is None
    ctx.set_cached_predicate("k", True)
    assert ctx.get_cached_predicate("k") is True

    record = RuleAuditRecord(
        rule_id="r1",
        event="PythonREPL",
        action_name="PythonREPL",
        enforce_result="stop",
        detail="{}",
    )
    ctx.add_audit(record)
    assert len(ctx.audits) == 1
    assert ctx.audits[0].rule_id == "r1"
