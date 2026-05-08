"""Training and promotion gates for Simon intent models."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from simon.intents import Intent
from simon.nlu.natural_language_router import NaturalLanguageRouter


@dataclass(frozen=True)
class QualityMetrics:
    total: int
    correct: int
    order_false_positive_count: int

    @property
    def accuracy(self) -> float:
        return 0.0 if self.total == 0 else self.correct / self.total

    @property
    def order_false_positive_rate(self) -> float:
        return 0.0 if self.total == 0 else self.order_false_positive_count / self.total


@dataclass(frozen=True)
class PromotionDecision:
    promoted: bool
    reason: str
    metrics: QualityMetrics


@dataclass(frozen=True)
class ModelPromotionGate:
    """Manual-only model promotion gate.

    Auto-promotion is not supported. A model can be promoted only when a human
    explicitly requests promotion and all quality thresholds pass.
    """

    min_accuracy: float = 0.95
    max_order_false_positive_rate: float = 0.0

    def evaluate(self, metrics: QualityMetrics, *, manual_approval: bool) -> PromotionDecision:
        if not manual_approval:
            return PromotionDecision(False, "manual_approval_required", metrics)

        if metrics.order_false_positive_rate > self.max_order_false_positive_rate:
            return PromotionDecision(False, "order_false_positive_rate_gate_failed", metrics)

        if metrics.accuracy < self.min_accuracy:
            return PromotionDecision(False, "accuracy_gate_failed", metrics)

        return PromotionDecision(True, "quality_gate_passed_manual_promotion_allowed", metrics)


class TrainingPipeline:
    """Consumes collected intent failures and evaluates candidate routing rules."""

    def __init__(self, router: NaturalLanguageRouter | None = None) -> None:
        self.router = router or NaturalLanguageRouter()

    def load_error_cases(self, path: str | Path) -> list[dict[str, str]]:
        error_path = Path(path)
        if not error_path.exists():
            return []

        cases: list[dict[str, str]] = []
        with error_path.open("r", encoding="utf-8") as input_file:
            for line in input_file:
                if not line.strip():
                    continue
                payload = json.loads(line)
                expected = payload.get("expected_intent")
                if expected:
                    cases.append({"text": payload["text"], "expected_intent": expected})
        return cases

    def evaluate_cases(self, cases: Iterable[dict[str, str]]) -> QualityMetrics:
        total = 0
        correct = 0
        order_false_positive_count = 0

        for case in cases:
            total += 1
            result = self.router.route(case["text"])
            expected = Intent(case["expected_intent"])

            if result.intent is expected:
                correct += 1

            if result.intent is Intent.ORDER and expected is not Intent.ORDER:
                order_false_positive_count += 1

        return QualityMetrics(
            total=total,
            correct=correct,
            order_false_positive_count=order_false_positive_count,
        )
