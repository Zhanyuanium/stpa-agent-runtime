from __future__ import annotations

from langchain_core.agents import AgentAction

from agent import Action
from interpreter import RuleInterpreter
from rule import Rule
from rules.manual.table import predicate_table
from state import RuleState
from agentspec_codegen.shell_parser import get_shellcheck_summary_for_audit
from agentspec_codegen.runtime import RuleAuditRecord


def test_shell_predicate_populates_shellcheck_for_audit() -> None:
    """When a shell rule runs, shellcheck is invoked and available for runtime audit."""
    rule = Rule.from_text(
        """rule @shell_destructive
trigger
    TerminalExecute
check
    destuctive_os_inst
enforce
    stop
end
"""
    )
    action = Action.from_langchain(
        AgentAction(tool="TerminalExecute", tool_input="sudo rm -rf /etc/nginx", log="")
    )
    state = RuleState(action=action, intermediate_steps=[], user_input="")
    interpreter = RuleInterpreter(rule, state)
    interpreter.verify_and_enforce(action)
    summary = get_shellcheck_summary_for_audit()
    assert summary is not None
    assert "available" in summary
    assert "diagnostic_count" in summary
    assert "level_counts" in summary
    record = RuleAuditRecord(
        rule_id=rule.id,
        event=rule.event,
        action_name=action.name,
        enforce_result="stop",
        detail="{}",
        shellcheck_summary=summary,
    )
    assert record.shellcheck_summary["available"] in (True, False)
    assert record.shellcheck_summary["diagnostic_count"] >= 0


def test_rule_interpreter_uses_predicate_cache() -> None:
    called = {"count": 0}

    def _cached_predicate(user_input, tool_input, intermediate_steps):
        called["count"] += 1
        return True

    old = predicate_table.get("has_bias_issues")
    predicate_table["has_bias_issues"] = _cached_predicate
    try:
        rule = Rule.from_text(
            """rule @cache_rule
trigger
    PythonREPL
check
    has_bias_issues
enforce
    stop
end
"""
        )
        action = Action.from_langchain(AgentAction(tool="PythonREPL", tool_input="print('a')", log=""))
        state = RuleState(action=action, intermediate_steps=[], user_input="demo")
        interpreter = RuleInterpreter(rule, state)
        interpreter.verify_and_enforce(action)
        interpreter.verify_and_enforce(action)
        assert called["count"] == 1
    finally:
        if old is None:
            predicate_table.pop("has_bias_issues", None)
        else:
            predicate_table["has_bias_issues"] = old
