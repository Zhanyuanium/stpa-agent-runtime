from __future__ import annotations

from agentspec_codegen.eval.metrics import evaluate_cases


def test_evaluate_cases_metrics_values() -> None:
    metrics = evaluate_cases(
        [
            {"is_risky": True, "blocked": True, "fulfilled": False, "overhead_ms": 1.0},
            {"is_risky": True, "blocked": False, "fulfilled": True, "overhead_ms": 3.0},
            {"is_risky": False, "blocked": True, "fulfilled": False, "overhead_ms": 2.0},
            {"is_risky": False, "blocked": False, "fulfilled": True, "overhead_ms": 4.0},
        ]
    )
    assert metrics.total_cases == 4
    assert metrics.interception_rate == 0.5
    assert metrics.false_positive_rate == 0.5
    assert metrics.task_completion_rate == 0.5
    assert metrics.avg_overhead_ms == 2.5
