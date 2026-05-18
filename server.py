from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, request, send_from_directory

BASE_DIR = Path(__file__).resolve().parent
UI_DIR = BASE_DIR / "ui"
RESIDENT_PID_PATH = BASE_DIR / "data" / "logs" / "resident" / "resident_agent.pid"
RESIDENT_SPAWN_LOG = BASE_DIR / "data" / "logs" / "resident" / "resident_spawn.log"
RESIDENT_START_SCRIPT = "scripts/start_simon_resident.bat"
CHAT_EVENTS_PATH = BASE_DIR / "data" / "logs" / "chat_events.jsonl"
CHAT_PIPELINE_VERSION = "chat_v2_ssot_routing_decision_v1"


class IPC:
    def write_command(
        self,
        command: str,
        *,
        source: str | None = None,
        hold: bool | None = None,
        order_execution_enabled: bool | None = None,
    ) -> str:
        payload = {
            "command": command,
            "source": source,
            "hold": hold,
            "order_execution_enabled": order_execution_enabled,
            "ts": time.time(),
        }
        cmd_dir = BASE_DIR / "data" / "commands"
        cmd_dir.mkdir(parents=True, exist_ok=True)
        cmd_id = f"cmd_{command}_{int(time.time() * 1000)}"
        (cmd_dir / f"{cmd_id}.json").write_text(
            json.dumps(payload, ensure_ascii=False), encoding="utf-8"
        )
        return cmd_id


ipc = IPC()

app = Flask(__name__)


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def build_control_status() -> dict[str, Any]:
    allow_live = os.environ.get("SIMON_ALLOW_LIVE", "0")
    hold = _env_bool("STOCK_HOLD", default=True)
    read_only = _env_bool("STOCK_READ_ONLY", default=True)
    broker_submit_allowed = (
        allow_live == "1" and not hold and not read_only and _env_bool("STOCK_BROKER_SUBMIT", default=False)
    )
    return {
        "SIMON_ALLOW_LIVE": allow_live,
        "HOLD": hold,
        "read_only": read_only,
        "broker_submit_allowed": broker_submit_allowed,
        "order_execution_enabled": broker_submit_allowed,
        "auto_trade_enabled": _env_bool("STOCK_AUTO_TRADE", default=False),
        "chat_pipeline_version": CHAT_PIPELINE_VERSION,
    }


def _auto_trade_missing_requirements(status: dict[str, Any]) -> list[str]:
    missing: list[str] = []
    if status["SIMON_ALLOW_LIVE"] != "1":
        missing.append("SIMON_ALLOW_LIVE=1")
    if status["HOLD"]:
        missing.append("hold=false")
    if status["read_only"]:
        missing.append("read_only=false")
    if not status["broker_submit_allowed"]:
        missing.append("broker_submit_allowed=true")
    return missing


def _read_resident_pid_file() -> int | None:
    if not RESIDENT_PID_PATH.is_file():
        return None
    try:
        raw = RESIDENT_PID_PATH.read_text(encoding="utf-8").strip()
        return int(raw) if raw else None
    except (OSError, ValueError):
        return None


def _is_process_alive(pid: int | None) -> bool:
    if pid is None or pid <= 0:
        return False
    if os.name == "nt":
        try:
            import ctypes

            PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
            handle = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
            if not handle:
                return False
            exit_code = ctypes.c_ulong()
            alive = bool(
                ctypes.windll.kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code))
                and exit_code.value == 259
            )
            ctypes.windll.kernel32.CloseHandle(handle)
            return alive
        except Exception:
            return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _spawn_resident_bat() -> dict[str, Any]:
    script = BASE_DIR / RESIDENT_START_SCRIPT
    RESIDENT_SPAWN_LOG.parent.mkdir(parents=True, exist_ok=True)
    log_rel = str(RESIDENT_SPAWN_LOG.relative_to(BASE_DIR)).replace("\\", "/")
    if not script.is_file():
        return {
            "ok": False,
            "spawned": False,
            "error": "resident_start_script_missing",
            "pid_file": None,
            "log": log_rel,
        }

    with RESIDENT_SPAWN_LOG.open("a", encoding="utf-8") as logf:
        logf.write(f"[spawn] starting {script}\n")
        try:
            if os.name == "nt":
                subprocess.Popen(
                    ["cmd", "/c", str(script)],
                    cwd=str(BASE_DIR),
                    creationflags=subprocess.CREATE_NEW_CONSOLE,
                )
            else:
                subprocess.Popen([str(script)], cwd=str(BASE_DIR))
        except OSError as exc:
            logf.write(f"[spawn] error={exc}\n")
            return {
                "ok": False,
                "spawned": False,
                "error": str(exc),
                "pid_file": None,
                "log": log_rel,
            }

        deadline = time.time() + 20.0
        while time.time() < deadline:
            pid = _read_resident_pid_file()
            if pid is not None and _is_process_alive(pid):
                logf.write(f"[spawn] pid={pid}\n")
                return {
                    "ok": True,
                    "spawned": True,
                    "pid": pid,
                    "pid_file": str(RESIDENT_PID_PATH),
                    "log": log_rel,
                }
            time.sleep(0.5)

        logf.write("[spawn] resident_pid_not_alive_after_timeout\n")
    return {
        "ok": False,
        "spawned": True,
        "error": "resident_pid_not_alive_after_timeout",
        "pid_file": None,
        "log": log_rel,
    }


@app.get("/api/status")
def api_status() -> Any:
    status = build_control_status()
    pid = _read_resident_pid_file()
    status["resident_pid"] = pid
    status["resident_pid_alive"] = _is_process_alive(pid)
    return jsonify(status)


@app.get("/chat_v2")
def chat_v2() -> Any:
    return send_from_directory(UI_DIR, "chat_v2.html")


@app.post("/api/control/auto-trade")
def control_auto_trade() -> Any:
    payload = request.get_json(silent=True) or {}
    enabled = bool(payload.get("enabled"))
    status = build_control_status()

    if enabled:
        missing = _auto_trade_missing_requirements(status)
        if missing:
            return (
                jsonify(
                    {
                        "ok": False,
                        "blocked": True,
                        "flag_armed": False,
                        "missing_requirements": missing,
                        "status": {
                            "broker_submit_allowed": status["broker_submit_allowed"],
                            "SIMON_ALLOW_LIVE": status["SIMON_ALLOW_LIVE"],
                            "HOLD": status["HOLD"],
                        },
                    }
                ),
                409,
            )
        cmd_id = ipc.write_command("auto_trade_start", source="control_bar")
        return jsonify(
            {
                "ok": True,
                "action": "auto_trade_start",
                "flag_armed": True,
                "broker_submit": status["broker_submit_allowed"],
                "command_id": cmd_id,
            }
        )

    cmd_id = ipc.write_command("auto_trade_stop", source="control_bar")
    return jsonify(
        {
            "ok": True,
            "action": "auto_trade_stop",
            "flag_armed": False,
            "broker_submit": False,
            "command_id": cmd_id,
        }
    )


@app.post("/api/control/emergency-stop")
def control_emergency_stop() -> Any:
    cmd_id = ipc.write_command(
        "emergency_stop",
        source="control_bar",
        hold=True,
        order_execution_enabled=False,
    )
    return jsonify(
        {
            "ok": True,
            "action": "emergency_stop",
            "hold": True,
            "order_execution_enabled": False,
            "broker_submit": False,
            "command_id": cmd_id,
        }
    )


@app.post("/api/control/resident/start")
def control_resident_start() -> Any:
    pid = _read_resident_pid_file()
    if pid is not None and _is_process_alive(pid):
        return jsonify({"ok": True, "already_running": True, "pid": pid})

    spawn = _spawn_resident_bat()
    if spawn.get("ok"):
        return jsonify(
            {
                "ok": True,
                "already_running": False,
                "pid": spawn["pid"],
                "script": RESIDENT_START_SCRIPT,
                "log": spawn["log"],
            }
        )

    return (
        jsonify(
            {
                "ok": False,
                "error": spawn.get("error", "resident_spawn_failed"),
                "spawned": spawn.get("spawned", False),
                "log": spawn.get("log"),
            }
        ),
        503,
    )


if __name__ == "__main__":
    port = int(os.environ.get("STOCK_SERVER_PORT", "18080"))
    app.run(host="127.0.0.1", port=port, debug=False)
