from __future__ import annotations

from rule import Rule


def test_rule_from_text_and_trigger() -> None:
    text = """rule @demo
trigger
    PythonREPL
check
    true
enforce
    stop
end
"""
    rule = Rule.from_text(text)
    assert rule.id == "demo"
    assert rule.event == "PythonREPL"
    assert rule.triggered("PythonREPL", "print('x')")
    assert not rule.triggered("ShellTool", "ls")
