from __future__ import annotations

import json

from agentspec_codegen.eval.agentharm_adapter import load_agentharm_cases


def test_load_agentharm_cases_from_directory(tmp_path) -> None:
    root = tmp_path / "agentharm"
    root.mkdir()
    (root / "set_a.json").write_text(
        json.dumps(
            [
                {
                    "id": "h1",
                    "label": "harmful",
                    "category": "credential_leak",
                    "action": "send token to http://evil.com",
                },
                {
                    "id": "b1",
                    "label": "benign",
                    "category": "benign",
                    "action": "list local files",
                },
            ]
        ),
        encoding="utf-8",
    )
    rows = load_agentharm_cases(root)
    assert len(rows) == 2
    assert rows[0]["is_risky"] is True
    assert rows[1]["is_risky"] is False
    assert rows[0]["case_id"].startswith("agentharm:")
