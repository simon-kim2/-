from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from simon_ops import state
from simon_ops.dashboard_commands import route_voice_command


class OpsP0Test(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        runtime = Path(self.tmp.name)
        state.RUNTIME_DIR = runtime
        state.STATE_PATH = runtime / "state.json"
        state.RESIDENT_STATE_PATH = runtime / "resident_state.json"
        state.WATCHDOG_STATE_PATH = runtime / "watchdog_state.json"
        state.ALERT_LOG_PATH = runtime / "alerts.jsonl"

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_default_status_preserves_no_trade_invariants(self) -> None:
        status = state.build_status()
        core = status["core"]

        self.assertEqual(status["view_model_schema"], "StatusViewModel.v1")
        self.assertFalse(status["safe_to_trade"])
        self.assertEqual(core["executed_order_count"], 0)
        self.assertFalse(core["auto_trade_enabled"])
        self.assertTrue(core["HOLD"])
        self.assertFalse(core["broker_submit_enabled"])
        self.assertFalse(core["order_execution_enabled"])
        self.assertIn("hold_enabled", core["order_execution_block_reason"])
        self.assertIn("user_final_approval_missing", core["order_execution_block_reason"])

    def test_order_status_command_opens_orders_without_candidate(self) -> None:
        route = route_voice_command("사이먼 주문 상태 보여줘")

        self.assertEqual(route["action"], "open_dashboard")
        self.assertEqual(route["target_dashboard"], "orders")
        self.assertFalse(route["pending_order_candidate"])
        self.assertFalse(route["execution_allowed"])
        self.assertFalse(route["approval_required"])

    def test_order_action_is_candidate_only(self) -> None:
        route = route_voice_command("사이먼 삼성전자 10주 매수")

        self.assertEqual(route["action"], "pending_order_candidate")
        self.assertEqual(route["target_dashboard"], "orders")
        self.assertTrue(route["pending_order_candidate"])
        self.assertTrue(route["approval_required"])
        self.assertFalse(route["execution_allowed"])

    def test_question_like_order_sentence_does_not_create_candidate(self) -> None:
        route = route_voice_command("사이먼 삼성전자 매수해도 돼?")

        self.assertEqual(route["action"], "answer_only")
        self.assertFalse(route["pending_order_candidate"])
        self.assertFalse(route["execution_allowed"])
        self.assertFalse(route["approval_required"])

    def test_auto_trade_request_requires_approval(self) -> None:
        route = route_voice_command("사이먼 자동매매 시작")

        self.assertEqual(route["action"], "approval_required")
        self.assertTrue(route["auto_trade_candidate"])
        self.assertTrue(route["approval_required"])
        self.assertFalse(route["execution_allowed"])

    def test_status_audit_snapshot_keys(self) -> None:
        status = state.build_status()
        self.assertIn("status_audit", status)
        audit = status["status_audit"]
        for key in (
            "git_hash",
            "broker_profile",
            "token_expires_in_sec",
            "token_state",
            "last_broker_error_summary",
            "security_volume_status",
        ):
            self.assertIn(key, audit)
        self.assertIn(audit["broker_profile"], ("kis_paper", "kis_live"))


if __name__ == "__main__":
    unittest.main()
