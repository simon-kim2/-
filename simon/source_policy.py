"""File-backed source policy checks."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

SIDONGTV_CHANNEL_ID = "UCdwlSE2aW2VCCQIS5aJwTsA"


@dataclass(frozen=True)
class SourcePolicy:
    source_name: str
    channel_id: str
    whitelisted: bool
    internal_only: bool
    no_redistribute: bool
    advisory_only: bool
    order_trigger_allowed: bool

    @property
    def can_trigger_order(self) -> bool:
        return self.whitelisted and not self.advisory_only and self.order_trigger_allowed


def sidongtv_policy() -> SourcePolicy:
    return SourcePolicy(
        source_name="sidongtv",
        channel_id=SIDONGTV_CHANNEL_ID,
        whitelisted=True,
        internal_only=True,
        no_redistribute=True,
        advisory_only=True,
        order_trigger_allowed=False,
    )


def assert_sidongtv_policy_file(path: str | Path = "config/source_policy.yaml") -> None:
    """Lightweight policy-file validation without external YAML dependency."""

    content = Path(path).read_text(encoding="utf-8")
    required_fragments = (
        SIDONGTV_CHANNEL_ID,
        "internal_only: true",
        "no_redistribute: true",
        "advisory_only: true",
        "order_trigger_allowed: false",
    )
    missing = [fragment for fragment in required_fragments if fragment not in content]
    if missing:
        raise AssertionError(f"source policy missing required fragments: {missing}")
