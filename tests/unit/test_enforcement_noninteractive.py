from __future__ import annotations

import os

import pytest

from agent import Action
from enforcement import EnforceResult, UserInspection
from state import RuleState


@pytest.fixture(autouse=True)
def _clear_noninteractive_env(monkeypatch):
    monkeypatch.delenv("AGENTSPEC_NON_INTERACTIVE", raising=False)
    yield


def test_user_inspection_non_interactive_skips(monkeypatch):
    monkeypatch.setenv("AGENTSPEC_NON_INTERACTIVE", "1")
    state = RuleState(action=None, intermediate_steps=[], user_input="x")
    ui = UserInspection(state=state)
    action = Action(name="TerminalExecute", input="echo hi", action=None)
    res, nxt = ui.apply(action)
    assert res == EnforceResult.SKIP
    assert nxt is not None
