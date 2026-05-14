"""KIS OAuth token lifecycle (skeleton). No secrets in logs or /api/status."""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_RUNTIME_DIR = Path(os.environ.get("SIMON_RUNTIME_DIR", _PROJECT_ROOT / "runtime"))

TOKEN_META_PATH = _RUNTIME_DIR / "kis_token_meta.json"
REFRESH_MARGIN_SEC = int(os.environ.get("SIMON_KIS_TOKEN_REFRESH_MARGIN_SEC", "120"))


@dataclass(frozen=True)
class TokenAudit:
    token_state: str
    token_expires_in_sec: int | None
    last_broker_error_summary: str | None


def _load_meta() -> dict[str, Any]:
    if not TOKEN_META_PATH.exists():
        return {}
    try:
        with TOKEN_META_PATH.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def save_token_meta(
    *,
    expires_at_epoch: float | None,
    last_error_summary: str | None = None,
) -> None:
    """Persist only expiry + masked error summary (never the raw token)."""
    _RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "expires_at_epoch": expires_at_epoch,
        "last_error_summary": last_error_summary,
        "updated_at_epoch": time.time(),
    }
    tmp = TOKEN_META_PATH.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
    tmp.replace(TOKEN_META_PATH)


class KISTokenManager:
    """Single place for token refresh (implement HTTP when API keys exist)."""

    def __init__(self) -> None:
        raw = os.environ.get("SIMON_BROKER_PROFILE", "kis_paper").strip().lower()
        self._profile = raw if raw in ("kis_paper", "kis_live") else "kis_paper"

    @property
    def broker_profile(self) -> str:
        return self._profile

    def audit_snapshot(self) -> TokenAudit:
        meta = _load_meta()
        exp = meta.get("expires_at_epoch")
        err = meta.get("last_error_summary")
        if not isinstance(err, str):
            err = None
        if err is not None and len(err) > 240:
            err = err[:237] + "..."

        if exp is None:
            return TokenAudit("missing", None, err)

        try:
            exp_f = float(exp)
        except (TypeError, ValueError):
            return TokenAudit("error", None, err or "invalid_expires_at_epoch")

        now = time.time()
        remain = int(exp_f - now)
        if remain <= 0:
            return TokenAudit("expired", 0, err)
        if remain <= REFRESH_MARGIN_SEC:
            return TokenAudit("expiring", remain, err)
        return TokenAudit("valid", remain, err)

    def refresh_if_needed(self) -> bool:
        """Reserved: call KIS token API once, obey 1 rps; no-op until wired."""
        _ = self.audit_snapshot()
        return False
