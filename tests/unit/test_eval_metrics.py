from __future__ import annotations

from agentspec_codegen.eval.metrics import evaluate_cases, evaluate_cases_by_category, evaluate_cases_by_field


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
    assert metrics.to_dict()["enforced_rate"] == 0.5
    assert metrics.false_positive_rate == 0.5
    assert metrics.task_completion_rate == 0.5
    assert metrics.avg_overhead_ms == 2.5


def test_evaluate_cases_by_category_values() -> None:
    rows = evaluate_cases_by_category(
        [
            {"case_id": "risky:index1:1_1", "category": "index1", "is_risky": True, "blocked": True, "fulfilled": False, "overhead_ms": 1.0},
            {"case_id": "risky:index1:1_2", "category": "index1", "is_risky": True, "blocked": False, "fulfilled": True, "overhead_ms": 3.0},
            {"case_id": "risky:index2:2_1", "category": "index2", "is_risky": True, "blocked": True, "fulfilled": False, "overhead_ms": 2.0},
            {"case_id": "benign:benign:0", "category": "benign", "is_risky": False, "blocked": False, "fulfilled": True, "overhead_ms": 1.5},
        ]
    )
    index1 = next(row for row in rows if row.category == "index1")
    assert index1.inv == 2
    assert index1.vio == 1
    assert index1.pass_count == 1
    assert index1.enforced_rate == 0.5

    benign = next(row for row in rows if row.category == "benign")
    assert benign.inv == 0
    assert benign.vio == 0
    assert benign.enforced_rate == 0.0


def test_evaluate_cases_by_field_values() -> None:
    rows = evaluate_cases_by_field(
        [
            {"owner_harm_category": "hijacking", "is_risky": True, "blocked": True, "fulfilled": False, "overhead_ms": 1.0},
            {"owner_harm_category": "hijacking", "is_risky": True, "blocked": False, "fulfilled": True, "overhead_ms": 2.0},
            {"owner_harm_category": "privacy_exposure", "is_risky": True, "blocked": True, "fulfilled": False, "overhead_ms": 1.0},
        ],
        "owner_harm_category",
    )
    hijacking = next(row for row in rows if row.category == "hijacking")
    assert hijacking.inv == 2
    assert hijacking.vio == 1
