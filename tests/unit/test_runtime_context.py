from __future__ import annotations

from agentspec_codegen.runtime import RuleAuditRecord, RuleRuntimeContext


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
