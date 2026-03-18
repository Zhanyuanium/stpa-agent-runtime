from __future__ import annotations

import json

from scripts.generate_code_rules import generate_rules


class _MockResponse:
    def __init__(self, content: str) -> None:
        self.content = content


class _MockLLM:
    def invoke(self, prompt: str) -> _MockResponse:
        if "Category: index1" in prompt:
            return _MockResponse('{"predicates":["submit_post_request","involve_system_file"]}')
        return _MockResponse('{"predicates":["write_to_io"]}')


def test_generate_rules_with_mock_llm_and_split_manifest(tmp_path) -> None:
    root = tmp_path / "py2text_dataset_json"
    root.mkdir(parents=True)
    (root / "index1_30_codes_full.json").write_text(
        json.dumps([{"Code": "print('a')"} for _ in range(10)]),
        encoding="utf-8",
    )

    generated, manifest = generate_rules(
        redcode_root=root,
        max_categories=1,
        samples_per_category=10,
        llm=_MockLLM(),
    )
    assert generated["index1"] == ["submit_post_request", "involve_system_file"]
    assert manifest["categories"]["index1"]["n_example"] == 1
    assert manifest["categories"]["index1"]["n_test"] == 9
