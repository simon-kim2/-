import json
import tempfile
import unittest
from pathlib import Path

from simon.source_policy import SIDONGTV_CHANNEL_ID, assert_sidongtv_policy_file, sidongtv_policy
from tools.sidongtv_loop import current_phase, run_once


class YoutubePolicyTest(unittest.TestCase):
    def test_sidongtv_policy_is_internal_advisory_only(self):
        policy = sidongtv_policy()
        self.assertEqual(SIDONGTV_CHANNEL_ID, policy.channel_id)
        self.assertTrue(policy.whitelisted)
        self.assertTrue(policy.internal_only)
        self.assertTrue(policy.no_redistribute)
        self.assertTrue(policy.advisory_only)
        self.assertFalse(policy.order_trigger_allowed)
        self.assertFalse(policy.can_trigger_order)

    def test_source_policy_file_contains_required_controls(self):
        assert_sidongtv_policy_file("config/source_policy.yaml")

    def test_sidongtv_loop_writes_advisory_only_log(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "sidongtv_loop.jsonl"
            event = run_once(log_path)
            payload = json.loads(log_path.read_text(encoding="utf-8").splitlines()[0])
            self.assertEqual(event, payload)
            self.assertEqual(SIDONGTV_CHANNEL_ID, payload["channel_id"])
            self.assertEqual("advisory_only", payload["signal_mode"])
            self.assertFalse(payload["order_trigger_allowed"])
            self.assertTrue(payload["no_redistribute"])

    def test_current_phase_is_separated(self):
        self.assertIn(
            current_phase(),
            {
                "market_collect_only",
                "after_market_collect_preprocess",
                "night_collect_training_separated",
            },
        )


if __name__ == "__main__":
    unittest.main()
