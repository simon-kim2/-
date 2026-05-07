"""Primary natural-language router for Simon.

The router favors safe informational intents over order execution. Order intent
is only returned for imperative order text that includes a quantity and has
already consumed an explicit approval token.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from simon.approval import ApprovalGuard
from simon.data_policy import is_advisory_only, is_allowed_source
from simon.intents import Intent, RouteResult
from simon.nlu.semantic_router import SemanticIntentRouter


QUESTION_SUFFIXES = (
    "사도 돼",
    "사도되",
    "살까",
    "할까",
    "어때",
    "괜찮",
    "좋을까",
    "될까",
    "가능",
)
QUESTION_MARKERS = ("?", "？", "알려줘", "보여줘", "추천", "분석", "조회")
ORDER_VERBS = ("매수", "매도", "사줘", "사라", "팔아", "팔아줘", "주문", "진입", "청산")
QUANTITY_RE = re.compile(r"(?P<quantity>\d[\d,]*)\s*(주|개|계약|shares?)", re.IGNORECASE)
SYMBOL_RE = re.compile(r"\b(?P<symbol>[A-Z]{1,6}|\d{6})(?:\b|[.:])")


@dataclass(frozen=True)
class OrderCandidate:
    side: str
    quantity: int
    symbol: str


@dataclass
class NaturalLanguageRouter:
    """Primary deterministic NLU router with hard order guards."""

    approval_guard: ApprovalGuard = field(default_factory=ApprovalGuard)
    semantic_router: SemanticIntentRouter = field(default_factory=SemanticIntentRouter)

    def route(
        self,
        text: str,
        *,
        approval_token: str | None = None,
        source: str | None = None,
    ) -> RouteResult:
        normalized = self._normalize(text)

        if not is_allowed_source(source):
            return RouteResult(Intent.UNKNOWN, 0.0, "source_not_whitelisted", source=source)

        advisory_only = is_advisory_only(source)

        priority_result = self._route_priority_informational(normalized)
        if priority_result is not None:
            return self._with_source_policy(priority_result, advisory_only, source)

        if self._is_question(normalized):
            intent = Intent.ORDER_QUERY if self._looks_like_order(normalized) else Intent.STOCK_INFO
            return self._with_source_policy(
                RouteResult(intent, 0.96, "question_form_demoted_from_order"),
                advisory_only,
                source,
            )

        order_candidate = self._extract_order_candidate(text, normalized)
        if order_candidate is not None and not advisory_only:
            if self.approval_guard.verify_and_consume(
                token=approval_token,
                symbol=order_candidate.symbol,
                side=order_candidate.side,
                quantity=order_candidate.quantity,
            ):
                return RouteResult(
                    Intent.ORDER,
                    1.0,
                    "imperative_quantity_approval_verified",
                    allowed_to_order=True,
                    source=source,
                    metadata={
                        "symbol": order_candidate.symbol,
                        "side": order_candidate.side,
                        "quantity": order_candidate.quantity,
                    },
                )

            return self._with_source_policy(
                RouteResult(
                    Intent.ORDER_QUERY,
                    0.99,
                    "order_hard_guard_missing_or_invalid_approval",
                    metadata={
                        "symbol": order_candidate.symbol,
                        "side": order_candidate.side,
                        "quantity": order_candidate.quantity,
                    },
                ),
                advisory_only,
                source,
            )

        if advisory_only and self._looks_like_order(normalized):
            return RouteResult(
                Intent.ORDER_QUERY,
                1.0,
                "advisory_only_source_order_trigger_blocked",
                advisory_only=True,
                source=source,
            )

        semantic_result = self.semantic_router.classify(text)
        if semantic_result.intent is not Intent.UNKNOWN:
            return self._with_source_policy(semantic_result, advisory_only, source)

        if any(keyword in normalized for keyword in ("시장", "시황", "브리핑", "현재")):
            return self._with_source_policy(
                RouteResult(Intent.MARKET_BRIEF, 0.7, "market_brief_fallback"),
                advisory_only,
                source,
            )

        return self._with_source_policy(
            RouteResult(Intent.UNKNOWN, 0.0, "no_route_match"),
            advisory_only,
            source,
        )

    def _route_priority_informational(self, normalized: str) -> RouteResult | None:
        if self._is_us_theme_rank(normalized):
            return RouteResult(Intent.US_THEME_RANK, 0.98, "priority_us_theme_rank_rule")

        if self._is_investor_rank(normalized):
            return RouteResult(Intent.INVESTOR_RANK, 0.98, "priority_investor_rank_rule")

        if self._is_value_screen(normalized):
            return RouteResult(Intent.VALUE_SCREEN, 0.98, "priority_value_screen_rule")

        return None

    def _is_us_theme_rank(self, normalized: str) -> bool:
        has_us_market = any(keyword in normalized for keyword in ("나스닥", "미국", "us", "nasdaq"))
        has_theme = "테마" in normalized or "섹터" in normalized
        has_rank = any(keyword in normalized for keyword in ("현재", "인기", "상승", "랭킹", "순위", "강세"))
        return has_us_market and has_theme and has_rank

    def _is_investor_rank(self, normalized: str) -> bool:
        has_investor = any(keyword in normalized for keyword in ("외국인", "기관", "연기금", "투신"))
        has_flow = any(keyword in normalized for keyword in ("수급", "순매수", "매집", "매수세", "랭킹", "순위"))
        return has_investor and has_flow

    def _is_value_screen(self, normalized: str) -> bool:
        has_value_metric = any(keyword in normalized for keyword in ("pbr", "per", "저평가", "가치주", "밸류"))
        has_screen = any(keyword in normalized for keyword in ("찾아", "종목", "스크리닝", "순위", "알려", "낮은"))
        return has_value_metric and has_screen

    def _extract_order_candidate(self, original: str, normalized: str) -> OrderCandidate | None:
        if not self._looks_like_order(normalized):
            return None

        quantity_match = QUANTITY_RE.search(normalized)
        if quantity_match is None:
            return None

        side = "sell" if any(keyword in normalized for keyword in ("매도", "팔아", "청산")) else "buy"
        quantity = int(quantity_match.group("quantity").replace(",", ""))
        symbol_match = SYMBOL_RE.search(original)
        return OrderCandidate(
            side=side,
            quantity=quantity,
            symbol=symbol_match.group("symbol").upper() if symbol_match else "",
        )

    def _looks_like_order(self, normalized: str) -> bool:
        return any(verb in normalized for verb in ORDER_VERBS)

    def _is_question(self, normalized: str) -> bool:
        return any(marker in normalized for marker in QUESTION_MARKERS) or any(
            suffix in normalized for suffix in QUESTION_SUFFIXES
        )

    def _with_source_policy(
        self,
        result: RouteResult,
        advisory_only: bool,
        source: str | None,
    ) -> RouteResult:
        if advisory_only and result.intent is Intent.ORDER:
            return RouteResult(
                Intent.ORDER_QUERY,
                1.0,
                "advisory_only_source_order_trigger_blocked",
                advisory_only=True,
                source=source,
                metadata=result.metadata,
            )

        return RouteResult(
            result.intent,
            result.confidence,
            result.reason,
            allowed_to_order=False,
            advisory_only=advisory_only,
            source=source,
            metadata=result.metadata,
        )

    def _normalize(self, text: str) -> str:
        return " ".join(text.strip().lower().split())
