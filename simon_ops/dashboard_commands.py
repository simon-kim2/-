from __future__ import annotations

import re
from typing import Any

from simon_ops.state import save_resident_state, utc_now

DASHBOARDS = {
    "chat": "/chat",
    "account": "/dashboard/account",
    "market": "/dashboard/market",
    "orders": "/dashboard/orders",
    "wall": "/dashboard/wall",
}

QUESTION_MARKERS = ("?", "어때", "될까", "인가", "나요", "해도 돼", "해도되", "가능")
ORDER_ACTION_MARKERS = ("매수", "매도", "주문", "사줘", "팔아", "담아", "정리")
ORDER_STATUS_MARKERS = ("주문 상태", "대기 주문", "미체결", "체결", "승인 상태")
AUTO_TRADE_START_MARKERS = ("자동매매 시작", "자동 매매 시작", "오토트레이딩 시작", "auto trade start")


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def _strip_wake_word(text: str) -> tuple[str, bool]:
    normalized = _normalize(text)
    wake_detected = normalized.startswith("사이먼")
    if wake_detected:
        normalized = normalized.replace("사이먼", "", 1).strip()
    return normalized, wake_detected


def _contains_any(text: str, markers: tuple[str, ...]) -> bool:
    return any(marker in text for marker in markers)


def route_voice_command(text: str) -> dict[str, Any]:
    command, wake_detected = _strip_wake_word(text)
    question_detected = _contains_any(command, QUESTION_MARKERS)
    route = {
        "input": text,
        "wake_word_detected": wake_detected,
        "question_detected": question_detected,
        "action": "chat_response",
        "target_dashboard": None,
        "target_url": "/chat",
        "execution_allowed": False,
        "approval_required": False,
        "pending_order_candidate": False,
        "auto_trade_candidate": False,
        "message": "요청을 채팅 응답으로 처리합니다. 주문과 자동매매는 실행하지 않았습니다.",
    }

    if not command:
        route.update(
            {
                "message": "사이먼 호출을 감지했습니다. 필요한 내용을 말씀해 주세요.",
                "target_dashboard": "chat",
                "target_url": DASHBOARDS["chat"],
            }
        )
    elif _contains_any(command, AUTO_TRADE_START_MARKERS):
        route.update(
            {
                "action": "approval_required",
                "target_dashboard": "orders",
                "target_url": DASHBOARDS["orders"],
                "approval_required": True,
                "auto_trade_candidate": True,
                "message": "자동매매 시작 요청은 재확인과 사용자 승인이 필요합니다. 자동매매는 켜지지 않았습니다.",
            }
        )
    elif _contains_any(command, ORDER_STATUS_MARKERS):
        route.update(
            {
                "action": "open_dashboard",
                "target_dashboard": "orders",
                "target_url": DASHBOARDS["orders"],
                "message": "주문 대시보드를 엽니다.",
            }
        )
    elif _contains_any(command, ORDER_ACTION_MARKERS) and not question_detected:
        route.update(
            {
                "action": "pending_order_candidate",
                "target_dashboard": "orders",
                "target_url": DASHBOARDS["orders"],
                "approval_required": True,
                "pending_order_candidate": True,
                "message": "주문성 음성은 주문 후보로만 표시합니다. 최종 승인 전에는 실행하지 않습니다.",
            }
        )
    elif _contains_any(command, ORDER_ACTION_MARKERS) and question_detected:
        route.update(
            {
                "action": "answer_only",
                "target_dashboard": "orders",
                "target_url": DASHBOARDS["orders"],
                "message": "질문형 주문 문장으로 판단했습니다. 주문 후보를 만들거나 실행하지 않습니다.",
            }
        )
    elif any(marker in command for marker in ("시장", "나스닥", "코스피", "코스닥", "테마")):
        route.update(
            {
                "action": "open_dashboard",
                "target_dashboard": "market",
                "target_url": DASHBOARDS["market"],
                "message": "시장 대시보드를 엽니다.",
            }
        )
    elif any(marker in command for marker in ("큰 화면", "월", "wall", "전광판")):
        route.update(
            {
                "action": "open_dashboard",
                "target_dashboard": "wall",
                "target_url": DASHBOARDS["wall"],
                "message": "큰 화면 대시보드를 엽니다.",
            }
        )
    elif any(marker in command for marker in ("현황", "예수금", "잔고", "계좌", "보유")):
        route.update(
            {
                "action": "open_dashboard",
                "target_dashboard": "account",
                "target_url": DASHBOARDS["account"],
                "message": "계좌 현황 대시보드를 엽니다.",
            }
        )
    elif any(marker in command for marker in ("대시보드", "화면", "보여줘", "띄워줘")):
        route.update(
            {
                "action": "open_dashboard",
                "target_dashboard": "account",
                "target_url": DASHBOARDS["account"],
                "message": "기본 현황 대시보드를 엽니다.",
            }
        )

    save_resident_state(
        {
            "enabled": True,
            "running": True,
            "status": "command_received",
            "last_heartbeat_at": utc_now(),
            "last_command": text,
            "last_route": route,
        }
    )
    return route

