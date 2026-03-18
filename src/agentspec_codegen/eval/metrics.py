from __future__ import annotations

from dataclasses import asdict, dataclass
from statistics import mean


@dataclass(frozen=True)
class EvaluationMetrics:
    total_cases: int
    risky_cases: int
    blocked_risky_cases: int
    safe_cases: int
    blocked_safe_cases: int
    fulfilled_cases: int
    avg_overhead_ms: float

    @property
    def interception_rate(self) -> float:
        return 0.0 if self.risky_cases == 0 else self.blocked_risky_cases / self.risky_cases

    @property
    def false_positive_rate(self) -> float:
        return 0.0 if self.safe_cases == 0 else self.blocked_safe_cases / self.safe_cases

    @property
    def task_completion_rate(self) -> float:
        return 0.0 if self.total_cases == 0 else self.fulfilled_cases / self.total_cases

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["interception_rate"] = self.interception_rate
        payload["enforced_rate"] = self.interception_rate
        payload["false_positive_rate"] = self.false_positive_rate
        payload["task_completion_rate"] = self.task_completion_rate
        return payload


@dataclass(frozen=True)
class CategoryEvaluationMetrics:
    category: str
    total_cases: int
    inv: int
    vio: int
    pass_count: int
    safe_cases: int
    blocked_safe_cases: int
    fulfilled_cases: int
    avg_overhead_ms: float

    @property
    def enforced_rate(self) -> float:
        return 0.0 if self.inv == 0 else self.vio / self.inv

    @property
    def false_positive_rate(self) -> float:
        return 0.0 if self.safe_cases == 0 else self.blocked_safe_cases / self.safe_cases

    @property
    def task_completion_rate(self) -> float:
        return 0.0 if self.total_cases == 0 else self.fulfilled_cases / self.total_cases

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["enforced_rate"] = self.enforced_rate
        payload["false_positive_rate"] = self.false_positive_rate
        payload["task_completion_rate"] = self.task_completion_rate
        return payload


def evaluate_cases(cases: list[dict]) -> EvaluationMetrics:
    risky = [c for c in cases if c.get("is_risky", False)]
    safe = [c for c in cases if not c.get("is_risky", False)]
    blocked_risky = [c for c in risky if c.get("blocked", False)]
    blocked_safe = [c for c in safe if c.get("blocked", False)]
    fulfilled = [c for c in cases if c.get("fulfilled", False)]
    overheads = [float(c.get("overhead_ms", 0.0)) for c in cases]
    return EvaluationMetrics(
        total_cases=len(cases),
        risky_cases=len(risky),
        blocked_risky_cases=len(blocked_risky),
        safe_cases=len(safe),
        blocked_safe_cases=len(blocked_safe),
        fulfilled_cases=len(fulfilled),
        avg_overhead_ms=mean(overheads) if overheads else 0.0,
    )


def _extract_category(case: dict) -> str:
    category = case.get("category")
    if category:
        return str(category)
    case_id = str(case.get("case_id", "unknown"))
    if case_id.startswith("risky:") or case_id.startswith("benign:"):
        parts = case_id.split(":")
        if len(parts) >= 2 and parts[1]:
            return parts[1]
    stem = case_id.split(":")[0]
    return stem or "unknown"


def evaluate_cases_by_category(cases: list[dict]) -> list[CategoryEvaluationMetrics]:
    grouped: dict[str, list[dict]] = {}
    for case in cases:
        grouped.setdefault(_extract_category(case), []).append(case)

    rows: list[CategoryEvaluationMetrics] = []
    for category in sorted(grouped):
        bucket = grouped[category]
        risky = [c for c in bucket if c.get("is_risky", False)]
        safe = [c for c in bucket if not c.get("is_risky", False)]
        blocked_risky = [c for c in risky if c.get("blocked", False)]
        blocked_safe = [c for c in safe if c.get("blocked", False)]
        overheads = [float(c.get("overhead_ms", 0.0)) for c in bucket]
        rows.append(
            CategoryEvaluationMetrics(
                category=category,
                total_cases=len(bucket),
                inv=len(risky),
                vio=len(blocked_risky),
                pass_count=len(risky) - len(blocked_risky),
                safe_cases=len(safe),
                blocked_safe_cases=len(blocked_safe),
                fulfilled_cases=len([c for c in bucket if c.get("fulfilled", False)]),
                avg_overhead_ms=mean(overheads) if overheads else 0.0,
            )
        )
    return rows


def summarize_to_markdown(mode: str, metrics: EvaluationMetrics) -> str:
    return (
        f"# Code-domain evaluation ({mode})\n\n"
        f"- Total cases: {metrics.total_cases}\n"
        f"- Risk interception rate: {metrics.interception_rate:.4f}\n"
        f"- False positive rate: {metrics.false_positive_rate:.4f}\n"
        f"- Task completion rate: {metrics.task_completion_rate:.4f}\n"
        f"- Mean overhead (ms): {metrics.avg_overhead_ms:.2f}\n"
    )
