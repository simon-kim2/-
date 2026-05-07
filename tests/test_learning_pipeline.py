import json
import tempfile
import unittest
from pathlib import Path

from simon.intents import Intent, RouteResult
from simon.learning.intent_errors import IntentErrorCollector
from simon.learning.pipeline import ModelPromotionGate, QualityMetrics


class LearningPipelineTest(unittest.TestCase):
    def test_intent_errors_are_collected_as_jsonl(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "intent_errors.jsonl"
            collector = IntentErrorCollector(path)
            collector.record(
                text="나스닥 현재 인기 상승 테마",
                route_result=RouteResult(Intent.MARKET_BRIEF, 0.4, "bad_fallback"),
                expected_intent=Intent.US_THEME_RANK,
            )

            lines = path.read_text(encoding="utf-8").splitlines()
            self.assertEqual(1, len(lines))
            payload = json.loads(lines[0])
            self.assertEqual("market_brief", payload["predicted_intent"])
            self.assertEqual("us_theme_rank", payload["expected_intent"])

    def test_auto_promotion_is_blocked_without_manual_approval(self):
        metrics = QualityMetrics(total=100, correct=100, order_false_positive_count=0)
        decision = ModelPromotionGate().evaluate(metrics, manual_approval=False)
        self.assertFalse(decision.promoted)
        self.assertEqual("manual_approval_required", decision.reason)

    def test_order_false_positive_gate_is_zero(self):
        metrics = QualityMetrics(total=100, correct=99, order_false_positive_count=1)
        decision = ModelPromotionGate().evaluate(metrics, manual_approval=True)
        self.assertFalse(decision.promoted)
        self.assertEqual("order_false_positive_rate_gate_failed", decision.reason)


if __name__ == "__main__":
    unittest.main()
