"""Source policy helpers.

The sidongtv whitelist is internal-only. Its data can inform responses, but it
must never trigger or promote an order intent.
"""

SIDONGTV_SOURCE = "sidongtv"
ALLOWED_SOURCES = frozenset({SIDONGTV_SOURCE, "internal_market_data", "broker_api"})
ADVISORY_ONLY_SOURCES = frozenset({SIDONGTV_SOURCE})


def is_allowed_source(source: str | None) -> bool:
    return source is None or source in ALLOWED_SOURCES


def is_advisory_only(source: str | None) -> bool:
    return source in ADVISORY_ONLY_SOURCES
