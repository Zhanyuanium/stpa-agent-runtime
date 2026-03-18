from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from agentspec_codegen.uca.models import UcaEntry, UcaKnowledgeBase, UcaRiskType


DEFAULT_PREDICATE_BY_RISK = {
    UcaRiskType.UNTRUSTED_POST_REQUEST: ["submit_post_request", "request_untrusted_source"],
    UcaRiskType.NETWORK_EXFILTRATION: ["encode_data", "write_to_io"],
    UcaRiskType.SENSITIVE_DATA_LEAK: ["read_io", "write_to_io"],
    UcaRiskType.STARTUP_FILE_TAMPER: ["write_to_io", "involve_system_file"],
    UcaRiskType.BASHRC_ALIAS_BACKDOOR: ["write_to_io", "involve_bash_rc"],
    UcaRiskType.PRIVILEGE_RETENTION: ["execute_script", "involve_system_file"],
    # Keep predicate names parser-compatible with the current AgentSpec grammar.
    UcaRiskType.SHELL_DESTRUCTIVE_DELETE: ["destuctive_os_inst", "involve_system_file"],
    UcaRiskType.SHELL_PRIVILEGE_ESCALATION: ["is_improper_execution_privilege_code"],
    UcaRiskType.SHELL_PROFILE_TAMPER: ["involve_bash_rc"],
}


@dataclass(frozen=True)
class CompilationArtifact:
    rule_id: str
    uca_id: str
    spec_text: str
    predicates: list[str]


def _normalize_rule_id(uca_id: str) -> str:
    return uca_id.lower().replace("-", "_")


def _resolve_predicates(entry: UcaEntry) -> list[str]:
    if entry.predicate_hints:
        return entry.predicate_hints
    return DEFAULT_PREDICATE_BY_RISK[entry.risk_type]


def compile_entry(entry: UcaEntry) -> CompilationArtifact:
    rule_id = _normalize_rule_id(entry.uca_id)
    predicates = _resolve_predicates(entry)
    template_dir = Path(__file__).resolve().parent / "templates"
    env = Environment(
        loader=FileSystemLoader(str(template_dir)),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    template = env.get_template("rule.spec.j2")
    spec_text = template.render(
        rule_id=rule_id,
        trigger_event=entry.trigger_event,
        predicates=predicates,
        enforcement=entry.enforcement,
    )
    spec_text = spec_text.rstrip() + "\n"
    return CompilationArtifact(rule_id=rule_id, uca_id=entry.uca_id, spec_text=spec_text, predicates=predicates)


def compile_knowledge_base(knowledge_base: UcaKnowledgeBase) -> list[CompilationArtifact]:
    return [compile_entry(entry) for entry in knowledge_base.entries]


def write_compiled_rules(artifacts: list[CompilationArtifact], output_dir: str | Path) -> list[Path]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for artifact in artifacts:
        path = output / f"{artifact.rule_id}.spec"
        path.write_text(artifact.spec_text, encoding="utf-8")
        written.append(path)
    return written
