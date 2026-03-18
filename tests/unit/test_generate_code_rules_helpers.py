from __future__ import annotations

from scripts.generate_code_rules import _default_risk_and_tactic, _normalize_predicates


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
