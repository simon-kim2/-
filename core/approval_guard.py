"""Approval guard compatible with the original file-IPC command flow."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from secrets import token_urlsafe
from typing import Any


@dataclass(frozen=True)
class ApprovalRecord:
    user_id: str
    payload: dict[str, Any]
    created_at: datetime


@dataclass
class ApprovalGuard:
    """Stores explicit one-time approvals for order commands."""

    ttl_seconds: int = 120
    _approvals: dict[str, ApprovalRecord] = field(default_factory=dict)

    def create(self, user_id: str, payload: dict[str, Any]) -> str:
        self._validate_payload(payload)
        approval_id = token_urlsafe(24)
        self._approvals[approval_id] = ApprovalRecord(
            user_id=user_id,
            payload=self._normalized_payload(payload),
            created_at=datetime.now(UTC),
        )
        return approval_id

    def verify(self, approval_id: str | None, user_id: str, payload: dict[str, Any]) -> bool:
        if not approval_id:
            return False

        record = self._approvals.get(approval_id)
        if record is None:
            return False

        if datetime.now(UTC) - record.created_at > timedelta(seconds=self.ttl_seconds):
            return False

        return record.user_id == user_id and record.payload == self._normalized_payload(payload)

    def consume(self, approval_id: str | None) -> None:
        if approval_id:
            self._approvals.pop(approval_id, None)

    def verify_and_consume(
        self,
        approval_id: str | None,
        user_id: str,
        payload: dict[str, Any],
    ) -> bool:
        if not self.verify(approval_id, user_id, payload):
            return False
        self.consume(approval_id)
        return True

    def _normalized_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        normalized = dict(payload)
        if "side" in normalized:
            normalized["side"] = str(normalized["side"]).lower()
        for code_key in ("code", "symbol"):
            if code_key in normalized and normalized[code_key] is not None:
                normalized[code_key] = str(normalized[code_key]).strip().upper()
        if "qty" in normalized and normalized["qty"] is not None:
            normalized["qty"] = int(normalized["qty"])
        if "quantity" in normalized and normalized["quantity"] is not None:
            normalized["quantity"] = int(normalized["quantity"])
        return normalized

    def _validate_payload(self, payload: dict[str, Any]) -> None:
        side = str(payload.get("side", "")).lower()
        qty = payload.get("qty", payload.get("quantity"))
        code = payload.get("code", payload.get("symbol"))
        if side not in {"buy", "sell"}:
            raise ValueError("approval payload side must be buy or sell")
        if not code:
            raise ValueError("approval payload code/symbol is required")
        if int(qty or 0) <= 0:
            raise ValueError("approval payload quantity must be positive")
