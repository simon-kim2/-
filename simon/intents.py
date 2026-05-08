"""Intent contracts shared by routing, execution, and quality gates."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class Intent(StrEnum):
    """Stable intent names used by the Simon NLU layer."""

    US_THEME_RANK = "us_theme_rank"
    INVESTOR_RANK = "investor_rank"
    VALUE_SCREEN = "value_screen"
    MARKET_BRIEF = "market_brief"
    STOCK_INFO = "stock_info"
    ORDER_QUERY = "order_query"
    ORDER = "order"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class RouteResult:
    """Result produced by a router.

    ``allowed_to_order`` is deliberately separate from ``intent`` so downstream
    order execution can use a single invariant: only execute when both the
    intent is ``ORDER`` and the approval guard has verified and consumed a token.
    """

    intent: Intent
    confidence: float
    reason: str
    allowed_to_order: bool = False
    advisory_only: bool = False
    source: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_order(self) -> bool:
        return self.intent is Intent.ORDER
