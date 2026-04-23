from __future__ import annotations

from scripts.generate_code_rules import (
    _default_risk_and_tactic,
    _deterministic_enforcement_decision,
    _normalize_predicate_groups,
    _normalize_predicates,
)


def test_normalize_predicates_filters_unknown_and_duplicates() -> None:
    available = {"submit_post_request", "request_untrusted_source"}
    result = _normalize_predicates(
        ["submit_post_request", "unknown_pred", "submit_post_request"],
        available,
    )
    assert result == ["submit_post_request"]


def test_default_risk_and_tactic_prefers_persistence_for_bashrc() -> None:
    risk, tactic = _default_risk_and_tactic(["involve_bash_rc", "write_to_io"])
    assert risk == "bashrc_alias_backdoor"
    assert tactic == "persistence"


def test_normalize_predicate_groups_filters_invalid_groups() -> None:
    available = {"submit_post_request", "request_untrusted_source", "write_to_io"}
    groups = _normalize_predicate_groups(
        [["submit_post_request", "request_untrusted_source"], ["unknown_pred"], ["write_to_io"]],
        available,
    )
    assert groups == [["submit_post_request", "request_untrusted_source"], ["write_to_io"]]


def test_deterministic_enforcement_decision_detects_conflict() -> None:
    final, reason, conflict = _deterministic_enforcement_decision(
        risk_type="untrusted_post_request",
        predicate_hints=["submit_post_request"],
        llm_suggestion="skip",
    )
    assert final == "stop"
    assert reason == "severe_risk_or_multi_predicate"
    assert conflict is True
