"""Auxiliary semantic intent router.

This router is intentionally secondary. It can add evidence for informational
intents, but it must not override NaturalLanguageRouter's hard safety guards.
"""

from __future__ import annotations

from dataclasses import dataclass

from simon.intents import Intent, RouteResult


@dataclass(frozen=True)
class SemanticIntentRouter:
    """Small deterministic stand-in for future embedding/model based routing."""

    def classify(self, text: str) -> RouteResult:
        normalized = text.strip().lower()

        if any(keyword in normalized for keyword in ("나스닥", "미국", "테마", "인기", "상승")):
            return RouteResult(Intent.US_THEME_RANK, 0.62, "semantic_us_theme_signal")

        if any(keyword in normalized for keyword in ("외국인", "기관", "수급", "순매수")):
            return RouteResult(Intent.INVESTOR_RANK, 0.62, "semantic_investor_flow_signal")

        if any(keyword in normalized for keyword in ("pbr", "저평가", "가치", "밸류")):
            return RouteResult(Intent.VALUE_SCREEN, 0.62, "semantic_value_signal")

        if any(keyword in normalized for keyword in ("시황", "시장", "브리핑")):
            return RouteResult(Intent.MARKET_BRIEF, 0.5, "semantic_market_brief_signal")

        return RouteResult(Intent.UNKNOWN, 0.0, "semantic_no_match")
