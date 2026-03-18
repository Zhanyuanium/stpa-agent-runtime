from __future__ import annotations

from scripts.export_paper_tables import render_category_table, render_markdown_table


def test_render_markdown_table() -> None:
    result = {
        "mode": "manual",
        "metrics": {
            "total_cases": 10,
            "interception_rate": 0.9,
            "false_positive_rate": 0.1,
            "task_completion_rate": 0.7,
            "avg_overhead_ms": 1.2,
        },
    }
    table = render_markdown_table(result)
    assert "| manual | 10 | 0.9000 | 0.1000 | 0.7000 | 1.20 |" in table


def test_render_category_table() -> None:
    result = {
        "mode": "manual",
        "metrics_by_category": [
            {"category": "index1", "inv": 30, "vio": 27, "pass_count": 3, "enforced_rate": 0.9},
            {"category": "index2", "inv": 30, "vio": 15, "pass_count": 15, "enforced_rate": 0.5},
        ],
    }
    table = render_category_table(result)
    assert "| category | inv | vio | pass | enforced_rate |" in table
    assert "| index1 | 30 | 27 | 3 | 0.9000 |" in table


def test_render_category_table_empty() -> None:
    assert render_category_table({"mode": "manual"}) == ""
