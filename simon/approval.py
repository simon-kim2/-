"""One-time approval guard for order execution."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from secrets import token_urlsafe


@dataclass
class Approval:
    symbol: str
    side: str
    quantity: int
    created_at: datetime


@dataclass
class ApprovalGuard:
    """Issues and consumes explicit order approvals.

    Orders must pass through ``verify_and_consume``. Tokens are single-use and
    expire to avoid stale approvals being reused after market context changes.
    """

    ttl_seconds: int = 120
    _approvals: dict[str, Approval] = field(default_factory=dict)

    def create_approval(self, *, symbol: str, side: str, quantity: int) -> str:
        if not symbol or quantity <= 0:
            raise ValueError("symbol and positive quantity are required")

        token = token_urlsafe(24)
        self._approvals[token] = Approval(
            symbol=symbol.strip().upper(),
            side=side.strip().lower(),
            quantity=quantity,
            created_at=datetime.now(UTC),
        )
        return token

    def verify_and_consume(
        self,
        *,
        token: str | None,
        symbol: str,
        side: str,
        quantity: int,
    ) -> bool:
        if not token:
            return False

        approval = self._approvals.pop(token, None)
        if approval is None:
            return False

        if datetime.now(UTC) - approval.created_at > timedelta(seconds=self.ttl_seconds):
            return False

        return (
            approval.symbol == symbol.strip().upper()
            and approval.side == side.strip().lower()
            and approval.quantity == quantity
        )
