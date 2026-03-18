from __future__ import annotations

from langchain_core.agents import AgentAction

from agent import Action
from interpreter import RuleInterpreter
from rule import Rule
from rules.manual.table import predicate_table
from state import RuleState


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
