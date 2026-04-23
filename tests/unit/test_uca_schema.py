from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from agentspec_codegen.uca.models import UcaEntry, UcaKnowledgeBase
from agentspec_codegen.uca.storage import load_uca_knowledge_base


def _valid_entry() -> dict:
    return {
        "uca_id": "UCA-CODE-101",
        "title": "Prevent risky post requests",
        "domain": "code",
        "risk_type": "untrusted_post_request",
        "mitre_tactic": "exfiltration",
        "trigger_event": "PythonREPL",
        "predicate_hints": ["submit_post_request"],
        "enforcement": "stop",
        "rationale": "Avoid outbound leaks.",
        "hazard_ids": ["H2"],
        "safety_constraint_ids": ["SC-01"],
    }


def test_uca_entry_accepts_valid_mitre_mapping() -> None:
    item = UcaEntry.model_validate(_valid_entry())
    assert item.mitre_tactic == "exfiltration"
    assert item.owner_harm_category == "exfiltration_via_tools"


def test_uca_entry_accepts_explicit_owner_harm_category() -> None:
    payload = _valid_entry()
    payload["owner_harm_category"] = "privacy_exposure"
    item = UcaEntry.model_validate(payload)
    assert item.owner_harm_category == "privacy_exposure"


def test_uca_entry_rejects_invalid_owner_harm_category() -> None:
    payload = _valid_entry()
    payload["owner_harm_category"] = "invalid_owner_harm"
    with pytest.raises(ValidationError):
        UcaEntry.model_validate(payload)


def test_uca_entry_rejects_invalid_mitre_mapping() -> None:
    payload = _valid_entry()
    payload["mitre_tactic"] = "persistence"
    with pytest.raises(ValidationError):
        UcaEntry.model_validate(payload)


def test_uca_entry_rejects_invalid_hazard_id() -> None:
    payload = _valid_entry()
    payload["hazard_ids"] = ["HAZARD-2"]
    with pytest.raises(ValidationError):
        UcaEntry.model_validate(payload)


def test_uca_entry_rejects_invalid_sc_id() -> None:
    payload = _valid_entry()
    payload["safety_constraint_ids"] = ["SC-1"]
    with pytest.raises(ValidationError):
        UcaEntry.model_validate(payload)


def test_uca_kb_rejects_duplicate_ids() -> None:
    entry = _valid_entry()
    payload = {"version": "0.1.0", "entries": [entry, entry]}
    with pytest.raises(ValidationError):
        UcaKnowledgeBase.model_validate(payload)


def test_load_sample_uca_kb() -> None:
    kb_path = Path(__file__).resolve().parents[2] / "data" / "uca" / "code" / "sample_kb.json"
    kb = load_uca_knowledge_base(kb_path)
    assert kb.version == "0.2.0"
    assert len(kb.entries) >= 25
    categories = {entry.metadata.get("category") for entry in kb.entries}
    assert all(cat is not None for cat in categories)
    assert len(categories) >= 25


def test_load_shell_uca_kb() -> None:
    kb_path = Path(__file__).resolve().parents[2] / "data" / "uca" / "shell" / "shell_kb.json"
    kb = load_uca_knowledge_base(kb_path)
    assert kb.entries
    assert kb.entries[0].domain.value == "shell"
    assert kb.entries[0].hazard_ids
    assert kb.entries[0].safety_constraint_ids


def test_uca_model_dump_roundtrip() -> None:
    kb = UcaKnowledgeBase.model_validate({"version": "0.1.0", "entries": [_valid_entry()]})
    dumped = kb.model_dump_json()
    assert json.loads(dumped)["entries"][0]["risk_type"] == "untrusted_post_request"
