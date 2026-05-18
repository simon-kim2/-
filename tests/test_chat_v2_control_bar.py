import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import server


class TestChatV2ControlBar(unittest.TestCase):
    def setUp(self):
        self.client = server.app.test_client()

    def test_chat_v2_control_bar_uses_status_and_no_legacy_sync(self):
        response = self.client.get("/chat_v2?session_id=resident_default&tts=1")
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn("/api/status", html)
        self.assertIn("/api/control/auto-trade", html)
        self.assertIn("/api/control/emergency-stop", html)
        self.assertIn("/api/control/resident/start", html)
        self.assertIn("SIMON_CHAT_V2_VOICE_MODE", html)
        self.assertIn("TTS only", html)
        self.assertIn("브라우저가 자동으로 듣기 시작하지 않습니다", html)
        self.assertIn("Resident 시작", html)
        self.assertIn("예수금", html)
        self.assertIn("현황", html)
        self.assertIn("전략", html)
        self.assertIn("음성대화 ON", html)
        self.assertIn("음성대화 OFF", html)
        self.assertIn("긴급중지", html)
        self.assertIn("/api/chat/messages", html)
        self.assertIn('id="mic-btn"', html)
        self.assertIn('id="ctrl-auto-on-btn"', html)
        self.assertIn("sendText('manual')", html)
        self.assertNotIn("body.voice-mode footer #mic-btn", html)
        self.assertNotIn("autoOnBtn.disabled", html)
        self.assertIn("flag not armed", html)
        self.assertNotIn("/message/sync", html)

    def test_auto_trade_on_is_blocked_by_status_gate(self):
        response = self.client.post("/api/control/auto-trade", json={"enabled": True})
        self.assertEqual(response.status_code, 409)
        payload = response.get_json()
        self.assertFalse(payload["ok"])
        self.assertTrue(payload["blocked"])
        self.assertFalse(payload["flag_armed"])
        self.assertIn("missing_requirements", payload)
        self.assertIn("read_only_mode=false", payload["missing_requirements"])
        self.assertIn("hold=false", payload["missing_requirements"])
        self.assertIn("broker_connected=true", payload["missing_requirements"])
        self.assertIn("status_degraded=false", payload["missing_requirements"])
        self.assertFalse(payload["status"]["broker_submit_allowed"])
        self.assertTrue(payload["status"]["hold"])
        self.assertTrue(payload["status"]["read_only_mode"])

    def test_api_status_exposes_control_bar_fields(self):
        response = self.client.get("/api/status")
        self.assertEqual(response.status_code, 200)
        status = response.get_json()
        for key in (
            "account_summary",
            "orderable_cash",
            "estimated_asset",
            "cash_d2",
            "broker_connected",
            "connection_status_summary",
            "hold",
            "git_hash",
            "mode",
            "stage",
            "next_stage",
            "position_policy",
            "read_only_mode",
            "executed_order_count",
            "status_degraded",
        ):
            self.assertIn(key, status)

    def test_auto_trade_off_writes_control_command(self):
        with patch.object(server.ipc, "write_command", return_value="cmd_auto_off") as write_command:
            response = self.client.post("/api/control/auto-trade", json={"enabled": False})
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["action"], "auto_trade_stop")
        self.assertFalse(payload["flag_armed"])
        self.assertFalse(payload["broker_submit"])
        write_command.assert_called_once()
        self.assertEqual(write_command.call_args.args[0], "auto_trade_stop")
        self.assertEqual(write_command.call_args.kwargs["source"], "control_bar")

    def test_emergency_stop_writes_hold_and_order_block_command_without_chat_events(self):
        operational_path = Path(server.BASE_DIR) / "data" / "logs" / "chat_events.jsonl"
        before = operational_path.stat().st_size if operational_path.exists() else 0
        with patch.object(server.ipc, "write_command", return_value="cmd_emergency") as write_command:
            response = self.client.post("/api/control/emergency-stop", json={})
        after = operational_path.stat().st_size if operational_path.exists() else 0
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["action"], "emergency_stop")
        self.assertTrue(payload["hold"])
        self.assertFalse(payload["order_execution_enabled"])
        self.assertFalse(payload["broker_submit"])
        self.assertEqual(before, after)
        write_command.assert_called_once()
        self.assertEqual(write_command.call_args.args[0], "emergency_stop")
        self.assertEqual(write_command.call_args.kwargs["source"], "control_bar")
        self.assertTrue(write_command.call_args.kwargs["hold"])
        self.assertFalse(write_command.call_args.kwargs["order_execution_enabled"])

    @patch("server._is_process_alive", return_value=True)
    @patch("server._read_resident_pid_file", return_value=99999)
    def test_resident_start_already_running(self, *_):
        with patch.object(server, "_spawn_resident_bat") as mock_spawn:
            response = self.client.post("/api/control/resident/start", json={})
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["ok"])
        self.assertTrue(payload["already_running"])
        self.assertEqual(payload["pid"], 99999)
        mock_spawn.assert_not_called()

    @patch("server._is_process_alive", return_value=False)
    @patch("server._read_resident_pid_file", return_value=4242)
    @patch("server.RESIDENT_PID_PATH")
    @patch("server._spawn_resident_bat")
    def test_resident_start_removes_stale_pid_before_spawn(self, mock_spawn, pid_path, *_):
        pid_path.is_file.return_value = True
        pid_path.unlink = MagicMock()
        mock_spawn.return_value = {"ok": True, "pid": 12345, "log": "data/logs/resident/resident_spawn.log"}
        response = self.client.post("/api/control/resident/start", json={})
        self.assertEqual(response.status_code, 200)
        pid_path.unlink.assert_called_once()
        mock_spawn.assert_called_once()

    @patch("server._is_process_alive", return_value=False)
    @patch("server._read_resident_pid_file", return_value=None)
    @patch("server._spawn_resident_bat")
    def test_resident_start_spawns_when_not_alive(self, mock_spawn, *_):
        mock_spawn.return_value = {"ok": True, "pid": 12345, "log": "data/logs/resident/resident_spawn.log"}
        response = self.client.post("/api/control/resident/start", json={})
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["ok"])
        self.assertFalse(payload["already_running"])
        self.assertEqual(payload["pid"], 12345)
        self.assertEqual(payload["script"], "scripts/start_simon_resident.bat")
        self.assertIn("resident_spawn.log", payload["log"])
        mock_spawn.assert_called_once()

    @patch("server._is_process_alive", return_value=False)
    @patch("server._read_resident_pid_file", return_value=None)
    @patch("server._spawn_resident_bat")
    def test_resident_start_returns_503_when_spawn_pid_not_alive(self, mock_spawn, *_):
        mock_spawn.return_value = {
            "ok": False,
            "spawned": True,
            "error": "resident_pid_not_alive_after_timeout",
            "pid_file": None,
            "log": "data/logs/resident/resident_spawn.log",
        }
        response = self.client.post("/api/control/resident/start", json={})
        self.assertEqual(response.status_code, 503)
        payload = response.get_json()
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["error"], "resident_pid_not_alive_after_timeout")
        self.assertIn("resident_spawn.log", payload["log"])


if __name__ == "__main__":
    unittest.main()
