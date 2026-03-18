from __future__ import annotations

from scripts.export_paper_tables import render_markdown_table


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
