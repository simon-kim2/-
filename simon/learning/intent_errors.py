"""Automatic collection of failed intent classifications."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from simon.intents import Intent, RouteResult


@dataclass(frozen=True)
class IntentErrorRecord:
    text: str
    predicted_intent: str
    expected_intent: str | None
    reason: str
    route_reason: str
    created_at: str
    metadata: dict[str, Any] = field(default_factory=dict)


class IntentErrorCollector:
    """Appends failed classifications to a JSONL training handoff file."""

    def __init__(self, path: str | Path = "data/intent_errors.jsonl") -> None:
        self.path = Path(path)

    def record(
        self,
        *,
        text: str,
        route_result: RouteResult,
        expected_intent: Intent | str | None = None,
        reason: str = "routing_error",
        metadata: dict[str, Any] | None = None,
    ) -> IntentErrorRecord:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        expected_value = expected_intent.value if isinstance(expected_intent, Intent) else expected_intent
        record = IntentErrorRecord(
            text=text,
            predicted_intent=route_result.intent.value,
            expected_intent=expected_value,
            reason=reason,
            route_reason=route_result.reason,
            created_at=datetime.now(UTC).isoformat(),
            metadata=metadata or {},
        )
        with self.path.open("a", encoding="utf-8") as output:
            output.write(json.dumps(asdict(record), ensure_ascii=False, sort_keys=True) + "\n")
        return record

    def record_if_mismatch(
        self,
        *,
        text: str,
        route_result: RouteResult,
        expected_intent: Intent,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        if route_result.intent is expected_intent:
            return False

        self.record(
            text=text,
            route_result=route_result,
            expected_intent=expected_intent,
            reason="expected_intent_mismatch",
            metadata=metadata,
        )
        return True
