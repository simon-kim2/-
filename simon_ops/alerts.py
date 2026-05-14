from __future__ import annotations

import json
import os
import platform
import subprocess
import sys
from typing import Any

from simon_ops.state import ALERT_LOG_PATH, ensure_runtime_dir, utc_now


def log_alert(event_type: str, message: str, severity: str = "warning", details: dict[str, Any] | None = None) -> dict[str, Any]:
    ensure_runtime_dir()
    event = {
        "event_type": event_type,
        "message": message,
        "severity": severity,
        "details": details or {},
        "created_at": utc_now(),
    }
    with ALERT_LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
    return event


def _try_platform_popup(title: str, message: str) -> bool:
    system = platform.system().lower()
    try:
        if system == "windows":
            script = (
                "Add-Type -AssemblyName PresentationFramework; "
                f"[System.Windows.MessageBox]::Show({message!r}, {title!r}) | Out-Null"
            )
            subprocess.Popen(["powershell", "-NoProfile", "-Command", script])
            return True
        if system == "darwin":
            subprocess.Popen(["osascript", "-e", f'display alert "{title}" message "{message}"'])
            return True
        if os.environ.get("DISPLAY") and shutil_which("notify-send"):
            subprocess.Popen(["notify-send", title, message])
            return True
    except OSError:
        return False
    return False


def shutil_which(command: str) -> str | None:
    for directory in os.environ.get("PATH", "").split(os.pathsep):
        candidate = os.path.join(directory, command)
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
    return None


def notify(
    event_type: str,
    message: str,
    severity: str = "warning",
    details: dict[str, Any] | None = None,
    popup: bool = True,
) -> dict[str, Any]:
    event = log_alert(event_type, message, severity, details)
    if popup and os.environ.get("SIMON_DISABLE_POPUPS") != "1":
        shown = _try_platform_popup(f"Simon {severity.upper()}", message)
        if not shown:
            print(f"[Simon {severity}] {message}", file=sys.stderr)
    return event

