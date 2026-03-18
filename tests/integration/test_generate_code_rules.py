from __future__ import annotations

import json

from scripts.generate_code_rules import generate_rules


class _MockResponse:
    def __init__(self, content: str) -> None:
        self.content = content


class _MockLLM:
    def invoke(self, prompt: str) -> _MockResponse:
        if "Category: index1" in prompt:
            return _MockResponse(
                '{"title":"Guard index1","rationale":"test rationale","predicate_hints":["submit_post_request","request_untrusted_source"],'
                '"risk_type":"untrusted_post_request","mitre_tactic":"exfiltration","enforcement":"stop"}'
            )
        return _MockResponse('{"title":"Guard default","rationale":"test rationale","predicate_hints":["write_to_io"]}')


def test_generate_rules_with_mock_llm_and_split_manifest(tmp_path) -> None:
    root = tmp_path / "py2text_dataset_json"
    root.mkdir(parents=True)
    (root / "index1_30_codes_full.json").write_text(
        json.dumps([{"Code": "print('a')"} for _ in range(10)]),
        encoding="utf-8",
    )

    generated_kb, manifest = generate_rules(
        redcode_root=root,
        max_categories=1,
        samples_per_category=10,
        llm=_MockLLM(),
    )
    assert generated_kb.entries[0].uca_id == "UCA-GEN-INDEX1"
    assert generated_kb.entries[0].predicate_hints == ["submit_post_request", "request_untrusted_source"]
    assert generated_kb.entries[0].risk_type.value == "untrusted_post_request"
    assert manifest["categories"]["index1"]["n_example"] == 1
    assert manifest["categories"]["index1"]["n_test"] == 9
