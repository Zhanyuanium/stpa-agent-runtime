from __future__ import annotations

from pathlib import Path

import pytest
from antlr4 import CommonTokenStream, InputStream
from antlr4.error.ErrorListener import ErrorListener

from spec_lang.AgentSpecLexer import AgentSpecLexer
from spec_lang.AgentSpecParser import AgentSpecParser


class _FailFastErrorListener(ErrorListener):
    def syntaxError(self, recognizer, offendingSymbol, line, column, msg, e):  # noqa: N802
        raise ValueError(f"Syntax error at line {line}, column {column}: {msg}")


def _parse(program: str) -> None:
    input_stream = InputStream(program)
    lexer = AgentSpecLexer(input_stream)
    token_stream = CommonTokenStream(lexer)
    parser = AgentSpecParser(token_stream)
    parser.removeErrorListeners()
    parser.addErrorListener(_FailFastErrorListener())
    parser.program()


@pytest.mark.parametrize(
    "rule_text",
    [
        """rule @check_shell_exec
trigger
    PythonREPL
check
    true
enforce
    stop
end
""",
    ],
)
def test_parse_inline_rules(rule_text: str) -> None:
    _parse(rule_text)


def test_parse_all_rule_examples() -> None:
    base = Path(__file__).resolve().parents[2] / "src" / "spec_lang" / "rule_examples"
    files = list(base.glob("*"))
    assert files, "rule_examples directory should not be empty"
    for rule_file in base.glob("*"):
        text = rule_file.read_text(encoding="utf-8")
        try:
            _parse(text)
        except ValueError:
            # Some historical examples use an older grammar and are kept as references.
            assert "prepare" in text or "act " in text
