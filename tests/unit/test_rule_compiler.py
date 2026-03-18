from __future__ import annotations

from pathlib import Path

from agentspec_codegen.compiler.rule_compiler import (
    compile_entry,
    compile_knowledge_base,
)
from agentspec_codegen.uca.models import UcaEntry
from agentspec_codegen.uca.storage import load_uca_knowledge_base
from rule import Rule


def test_compile_entry_matches_golden() -> None:
    entry = UcaEntry.model_validate(
        {
            "uca_id": "UCA-CODE-001",
            "title": "Block untrusted outbound data post",
            "domain": "code",
            "risk_type": "untrusted_post_request",
            "mitre_tactic": "exfiltration",
            "trigger_event": "PythonREPL",
            "predicate_hints": ["submit_post_request", "request_untrusted_source"],
            "enforcement": "stop",
            "rationale": "Prevent data exfiltration to untrusted endpoints.",
        }
    )
    artifact = compile_entry(entry)
    golden = (Path(__file__).resolve().parents[1] / "golden" / "uca_code_001.spec").read_text(
        encoding="utf-8"
    )
    assert artifact.spec_text.strip() == golden.strip()


def test_compiled_rule_is_parsable_by_agentspec() -> None:
    entry = UcaEntry.model_validate(
        {
            "uca_id": "UCA-CODE-002",
            "title": "Block startup file backdoor writes",
            "domain": "code",
            "risk_type": "bashrc_alias_backdoor",
            "mitre_tactic": "persistence",
            "trigger_event": "PythonREPL",
            "predicate_hints": ["write_to_io", "involve_bash_rc"],
            "enforcement": "stop",
            "rationale": "Prevent persistence through shell profile tampering.",
        }
    )
    artifact = compile_entry(entry)
    parsed = Rule.from_text(artifact.spec_text)
    assert parsed.id == "uca_code_002"
    assert parsed.event == "PythonREPL"


def test_compile_sample_knowledge_base() -> None:
    kb = load_uca_knowledge_base(
        Path(__file__).resolve().parents[2] / "data" / "uca" / "code" / "sample_kb.json"
    )
    artifacts = compile_knowledge_base(kb)
    assert len(artifacts) == len(kb.entries)


def test_compile_shell_knowledge_base_is_parsable() -> None:
    kb = load_uca_knowledge_base(
        Path(__file__).resolve().parents[2] / "data" / "uca" / "shell" / "shell_kb.json"
    )
    artifacts = compile_knowledge_base(kb)
    assert artifacts
    for artifact in artifacts:
        parsed = Rule.from_text(artifact.spec_text)
        assert parsed.event == "TerminalExecute"
