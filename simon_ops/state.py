from __future__ import annotations

import copy
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_DIR = Path(os.environ.get("SIMON_RUNTIME_DIR", PROJECT_ROOT / "runtime"))
STATE_PATH = RUNTIME_DIR / "state.json"
RESIDENT_STATE_PATH = RUNTIME_DIR / "resident_state.json"
WATCHDOG_STATE_PATH = RUNTIME_DIR / "watchdog_state.json"
ALERT_LOG_PATH = RUNTIME_DIR / "alerts.jsonl"

STARTED_AT = datetime.now(timezone.utc)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def ensure_runtime_dir() -> None:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)


def _read_json(path: Path, default: dict[str, Any]) -> dict[str, Any]:
    try:
        if not path.exists():
            return copy.deepcopy(default)
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        if isinstance(data, dict):
            merged = copy.deepcopy(default)
            merged.update(data)
            return merged
    except (OSError, json.JSONDecodeError):
        pass
    return copy.deepcopy(default)


def _write_json(path: Path, data: dict[str, Any]) -> None:
    ensure_runtime_dir()
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with tmp_path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
    tmp_path.replace(path)


DEFAULT_RESIDENT_STATE: dict[str, Any] = {
    "enabled": False,
    "running": False,
    "wake_word": "사이먼",
    "mode": "text_fallback",
    "stt_available": False,
    "status": "stopped",
    "last_heartbeat_at": None,
    "last_command": None,
    "last_route": None,
    "known_issue": "Resident STT hotword capture is not enabled in this environment.",
}

DEFAULT_WATCHDOG_STATE: dict[str, Any] = {
    "enabled": False,
    "running": False,
    "status": "stopped",
    "last_heartbeat_at": None,
    "last_status_ok_at": None,
    "last_restart_at": None,
    "restart_count": 0,
    "last_error": None,
}

DEFAULT_CORE_STATE: dict[str, Any] = {
    "mode": "paper",
    "account_number": None,
    "account_connected": False,
    "broker_vendor": "kis",
    "broker_profile": "kis_paper",
    "broker_connected": False,
    "openapi_errors": [],
    "price_feed_available": False,
    "current_price_source": "unavailable",
    "stale_price": True,
    "market_data_limited": True,
    "cash_balance_available": False,
    "cash_balance": None,
    "holdings_available": False,
    "holdings": [],
    "pending_order": None,
    "approval_status": "missing",
    "approval_guard_status": "blocked:no_user_approval",
    "risk_guard_status": "blocked:price_feed_unavailable",
    "trading_execution_policy": "blocked:hold_enabled",
    "order_execution_enabled": False,
    "order_execution_block_reason": [
        "hold_enabled",
        "user_final_approval_missing",
        "price_feed_unavailable",
    ],
    "executed_order_count": 0,
    "auto_trade_enabled": False,
    "HOLD": True,
    "broker_submit_enabled": False,
    "production_model_auto_promote": False,
}


def load_core_state() -> dict[str, Any]:
    return _read_json(STATE_PATH, DEFAULT_CORE_STATE)


def save_core_state(patch: dict[str, Any]) -> dict[str, Any]:
    state = load_core_state()
    state.update(patch)
    _write_json(STATE_PATH, state)
    return state


def load_resident_state() -> dict[str, Any]:
    return _read_json(RESIDENT_STATE_PATH, DEFAULT_RESIDENT_STATE)


def save_resident_state(patch: dict[str, Any]) -> dict[str, Any]:
    state = load_resident_state()
    state.update(patch)
    _write_json(RESIDENT_STATE_PATH, state)
    return state


def load_watchdog_state() -> dict[str, Any]:
    return _read_json(WATCHDOG_STATE_PATH, DEFAULT_WATCHDOG_STATE)


def save_watchdog_state(patch: dict[str, Any]) -> dict[str, Any]:
    state = load_watchdog_state()
    state.update(patch)
    _write_json(WATCHDOG_STATE_PATH, state)
    return state


def read_recent_alerts(limit: int = 10) -> list[dict[str, Any]]:
    if not ALERT_LOG_PATH.exists():
        return []
    alerts: list[dict[str, Any]] = []
    try:
        with ALERT_LOG_PATH.open("r", encoding="utf-8") as handle:
            lines = handle.readlines()[-limit:]
    except OSError:
        return []
    for line in lines:
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict):
            alerts.append(data)
    return alerts


def _git_hash_short() -> str:
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            return proc.stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        pass
    return "unknown"


def _broker_error_summary(core: dict[str, Any]) -> str | None:
    errors = core.get("openapi_errors")
    if not isinstance(errors, list) or not errors:
        return None
    last = errors[-1]
    if isinstance(last, str):
        text = last
    elif isinstance(last, dict):
        text = str(last.get("message") or last.get("msg") or last)
    else:
        text = str(last)
    text = text.strip()
    if len(text) > 240:
        return text[:237] + "..."
    return text or None


def _build_status_audit(core: dict[str, Any]) -> dict[str, Any]:
    from simon_ops.kis_token_manager import KISTokenManager

    tm = KISTokenManager()
    snap = tm.audit_snapshot()
    api_err = _broker_error_summary(core)
    summary = snap.last_broker_error_summary or api_err
    return {
        "git_hash": _git_hash_short(),
        "broker_profile": tm.broker_profile,
        "token_expires_in_sec": snap.token_expires_in_sec,
        "token_state": snap.token_state,
        "last_broker_error_summary": summary,
        "security_volume_status": os.environ.get("SIMON_SECURITY_VOLUME_STATUS", "unknown"),
    }


def compute_order_execution(core: dict[str, Any]) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    if core.get("mode") != "paper":
        reasons.append("not_paper_mode")
    if core.get("HOLD") is not False:
        reasons.append("hold_enabled")
    if core.get("approval_status") != "approved":
        reasons.append("user_final_approval_missing")
    if not core.get("price_feed_available"):
        reasons.append("price_feed_unavailable")
    if core.get("stale_price"):
        reasons.append("stale_price")
    if core.get("risk_guard_status") != "ok":
        reasons.append("risk_guard_not_ok")
    if core.get("trading_execution_policy") != "ok":
        reasons.append("trading_execution_policy_not_ok")
    if not core.get("broker_submit_enabled"):
        reasons.append("broker_submit_disabled")
    return (len(reasons) == 0, reasons)


def build_status() -> dict[str, Any]:
    core = load_core_state()
    order_enabled, block_reasons = compute_order_execution(core)
    core["order_execution_enabled"] = order_enabled
    core["order_execution_block_reason"] = block_reasons

    health = "ok"
    if core.get("HOLD") or not core.get("price_feed_available") or core.get("market_data_limited"):
        health = "degraded"
    if core.get("executed_order_count", 0) != 0 or core.get("auto_trade_enabled"):
        health = "unsafe"

    status = {
        "status_schema_version": "ops-p0-1",
        "view_model_schema": "StatusViewModel.v1",
        "generated_at": utc_now(),
        "server_pid": os.getpid(),
        "started_at": STARTED_AT.isoformat().replace("+00:00", "Z"),
        "uptime_seconds": round((datetime.now(timezone.utc) - STARTED_AT).total_seconds(), 3),
        "api_latency_budget_seconds": 3,
        "health": health,
        "safe_to_trade": False,
        "operational_mode": "p0_stabilization_no_live_trading",
        "core": core,
        "resident": load_resident_state(),
        "watchdog": load_watchdog_state(),
        "dashboards": {
            "chat": "/chat",
            "account": "/dashboard/account",
            "market": "/dashboard/market",
            "orders": "/dashboard/orders",
            "wall": "/dashboard/wall",
        },
        "safety_invariants": {
            "actual_orders_without_approval_forbidden": True,
            "question_sentences_do_not_execute_orders": True,
            "voice_orders_require_reconfirmation": True,
            "auto_trade_requires_reconfirmation": True,
            "external_sources_advisory_only": True,
            "unknown_numbers_are_not_fabricated": True,
            "stale_or_fallback_data_must_be_displayed": True,
            "production_auto_promote_forbidden": True,
        },
        "recent_alerts": read_recent_alerts(),
        "status_audit": _build_status_audit(core),
    }
    return status

