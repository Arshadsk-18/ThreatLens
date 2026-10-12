"""Evaluation metrics calculation including Wilson score intervals."""
from __future__ import annotations

from app.services.evaluation import wilson_95_interval


def compute_wilson_interval(successes: int, total: int) -> tuple[float, float]:
    """Calculate Wilson 95% confidence interval returning (lower, upper)."""
    interval = wilson_95_interval(successes, total)
    return float(interval[0]), float(interval[1])
