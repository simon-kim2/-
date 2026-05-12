from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path
from typing import Any

from simon_ops.alerts import notify
from simon_ops.state import PROJECT_ROOT, RUNTIME_DIR, ensure_runtime_dir, utc_now

DEFAULT_PORT = int(os.environ.get("STOCK_SERVER_PORT", "8080"))
PID_FILE = RUNTIME_DIR / "simon_ops.pid"
LAUNCH_STATE_FILE = RUNTIME_DIR / "launcher_state.json"


def _python_exe() -> str:
    return sys.executable or "python"


def _read_launch_state() -> dict[str, Any]:
    try:
        with LAUNCH_STATE_FILE.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _write_launch_state(data: dict[str, Any]) -> None:
    ensure_runtime_dir()
    with LAUNCH_STATE_FILE.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _terminate_pid(pid: int, timeout: float = 8.0) -> bool:
    if not _pid_alive(pid):
        return True
    try:
        if os.name == "nt":
            result = subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], check=False, capture_output=True, text=True)
            return result.returncode == 0 or not _pid_alive(pid)
        os.kill(pid, signal.SIGTERM)
    except OSError:
        return False
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not _pid_alive(pid):
            return True
        time.sleep(0.2)
    try:
        os.kill(pid, signal.SIGKILL)
    except OSError:
        pass
    return not _pid_alive(pid)


def stop_existing() -> list[int]:
    stopped: list[int] = []
    state = _read_launch_state()
    for raw_pid in {state.get("pid"), _read_pid_file()}:
        try:
            pid = int(raw_pid)
        except (TypeError, ValueError):
            continue
        if _terminate_pid(pid):
            stopped.append(pid)
    return stopped


def _read_pid_file() -> int | None:
    try:
        return int(PID_FILE.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return None


def _target_script(target: str) -> Path:
    if target == "main":
        return PROJECT_ROOT / "main.py"
    if target == "server":
        return PROJECT_ROOT / "server.py"
    main_path = PROJECT_ROOT / "main.py"
    return main_path if main_path.exists() else PROJECT_ROOT / "server.py"


def start_process(target: str, port: int) -> subprocess.Popen[Any]:
    script = _target_script(target)
    if not script.exists():
        raise FileNotFoundError(f"launch target not found: {script}")
    env = os.environ.copy()
    env.setdefault("PYTHONIOENCODING", "utf-8")
    env["STOCK_SERVER_PORT"] = str(port)
    env.setdefault("STOCK_IPC_MODE", "file")
    env.setdefault("STOCK_SHADOW_MODE", "1")
    log_path = RUNTIME_DIR / "simon_ops.log"
    ensure_runtime_dir()
    log_handle = log_path.open("a", encoding="utf-8")
    kwargs: dict[str, Any] = {
        "cwd": str(PROJECT_ROOT),
        "env": env,
        "stdout": log_handle,
        "stderr": subprocess.STDOUT,
        "stdin": subprocess.DEVNULL,
    }
    if os.name == "nt":
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    proc = subprocess.Popen([_python_exe(), "-X", "utf8", str(script)], **kwargs)
    PID_FILE.write_text(str(proc.pid), encoding="utf-8")
    _write_launch_state(
        {
            "pid": proc.pid,
            "target": str(script),
            "port": port,
            "started_at": utc_now(),
            "log_path": str(log_path),
        }
    )
    return proc


def fetch_status(port: int, timeout: float = 3.0) -> dict[str, Any]:
    url = f"http://127.0.0.1:{port}/api/status"
    with urllib.request.urlopen(url, timeout=timeout) as response:
        payload = response.read().decode("utf-8")
    data = json.loads(payload)
    if not isinstance(data, dict):
        raise RuntimeError("status response is not a JSON object")
    return data


def wait_for_status(port: int, deadline_seconds: float = 30.0) -> dict[str, Any]:
    deadline = time.monotonic() + deadline_seconds
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            return fetch_status(port, timeout=3.0)
        except (OSError, urllib.error.URLError, json.JSONDecodeError, RuntimeError) as exc:
            last_error = exc
            time.sleep(1.0)
    raise TimeoutError(f"/api/status did not become ready within {deadline_seconds}s: {last_error}")


def open_dashboards(port: int) -> None:
    base = f"http://127.0.0.1:{port}"
    for path in ("/chat", "/dashboard/account", "/dashboard/market", "/dashboard/orders"):
        webbrowser.open_new_tab(base + path)


def start(args: argparse.Namespace) -> int:
    stopped = stop_existing()
    proc = start_process(args.target, args.port)
    try:
        status = wait_for_status(args.port, args.ready_timeout)
    except Exception as exc:
        notify("server_start_failed", f"사이먼 실행 실패: {exc}", "critical", {"pid": proc.pid, "stopped": stopped})
        return 2
    open_dashboards(args.port)
    notify(
        "server_started",
        f"사이먼 서버 시작 PID={proc.pid}, status={status.get('health')}",
        "info",
        {"pid": proc.pid, "stopped": stopped, "status": status},
        popup=False,
    )
    return 0


def stop(args: argparse.Namespace) -> int:
    stopped = stop_existing()
    if stopped:
        notify("server_stopped", f"사이먼 서버 중지: {stopped}", "info", popup=False)
    else:
        notify("server_stop_noop", "중지할 사이먼 서버 PID를 찾지 못했습니다.", "warning", popup=False)
    return 0


def status(args: argparse.Namespace) -> int:
    data = fetch_status(args.port, timeout=3.0)
    print(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Simon one-click launcher")
    sub = parser.add_subparsers(dest="command", required=True)
    start_parser = sub.add_parser("start")
    start_parser.add_argument("--target", choices=("auto", "main", "server"), default=os.environ.get("SIMON_START_TARGET", "auto"))
    start_parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    start_parser.add_argument("--ready-timeout", type=float, default=30.0)
    stop_parser = sub.add_parser("stop")
    stop_parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    status_parser = sub.add_parser("status")
    status_parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.command == "start":
        return start(args)
    if args.command == "stop":
        return stop(args)
    if args.command == "status":
        return status(args)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

