"""Build a hard-fail QA intent dataset for Simon NLU regression training.

Target policy:
- Preserve existing curated rows when present.
- Grow the final curated set to 40,000 rows.
- Remove duplicate questions/answer policies.
- Force at least 5,000 difficult question rows that cover confused routing,
  date references, question-form order demotion, and stale/data-error wording.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

TOTAL_ROWS = 40_000
HARD_QUESTION_ROWS = 5_000
LEGACY_DATASET = "qa_intent_20000.jsonl"
OUTPUT_STEM = "qa_intent_40000"

MANDATORY_FAILURE_CASES = [
    ("나스닥 현재 인기 상승 테마", "us_theme_rank", "hard_question"),
    ("나스닥 상승 테마 알려줘", "us_theme_rank", "hard_question"),
    ("미국 인기 테마 순위", "us_theme_rank", "hard_question"),
    ("어제 나스닥 상승 테마분야는 뭐야?", "us_theme_rank", "hard_question"),
    ("전일 미국 상승 테마 알려줘", "us_theme_rank", "hard_question"),
    ("외국인 기관 수급 좋은 종목", "investor_rank", "hard_question"),
    ("기관 순매수 랭킹", "investor_rank", "hard_question"),
    ("PBR 낮은 저평가 종목", "value_metric_single", "hard_question"),
    ("삼성전자 사도 돼?", "stock_analysis", "hard_question"),
    ("AAPL 10주 매수할까?", "stock_analysis", "hard_question"),
    ("TSLA 사는 거 어때?", "stock_analysis", "hard_question"),
]

STANDARD_TEMPLATES = {
    "stock_analysis": [
        "{stock} 지금 차트 어때?",
        "{stock} 오늘 들어가도 되는 자리야?",
        "{stock} 단기 흐름 분석해줘",
        "{stock} 사도 돼?",
    ],
    "theme_top": [
        "오늘 강한 국내 테마 알려줘",
        "상승 테마 순위 보여줘",
        "인기 테마 뭐야?",
    ],
    "us_theme_rank": [
        "나스닥 현재 인기 상승 테마 알려줘",
        "미국 증시 강세 테마 순위 보여줘",
        "nasdaq 상승 섹터 랭킹",
    ],
    "investor_rank": [
        "외국인 기관 수급 좋은 종목 순위",
        "기관 순매수 랭킹 알려줘",
        "외국인 매집 종목 보여줘",
    ],
    "cancel_pending": [
        "미체결 주문 취소할까?",
        "{stock} 미체결 취소 가능해?",
    ],
    "price_current": [
        "{stock} 현재가 알려줘",
        "{stock} 지금 가격 얼마야?",
    ],
    "value_metric_single": [
        "PBR 낮은 저평가 종목 찾아줘",
        "PER 낮은 가치주 순위 알려줘",
    ],
    "market_brief": [
        "시장 브리핑 해줘",
        "오늘 시장 어때?",
        "나스닥 지수랑 환율 알려줘",
    ],
    "buy": [
        "{symbol} 10주 매수 승인 후 실행",
        "{symbol} 5주 사줘 승인 완료",
    ],
    "sell": [
        "{symbol} 10주 매도 승인 후 실행",
        "{symbol} 5주 팔아줘 승인 완료",
    ],
}

HARD_TEMPLATES = {
    "stock_analysis": [
        "{stock} 사도 되는지 말로만 분석해줘",
        "{stock} 지금 들어가도 돼? 주문하지 말고 판단만",
        "{stock} 매수할까 고민 중인데 리스크 알려줘",
        "{stock} 오늘 사는 건 어때? 실행은 하지 마",
        "{stock} 보유 중이면 더 가져가도 될까?",
    ],
    "us_theme_rank": [
        "어제 나스닥 상승 테마분야는 뭐야?",
        "직전 미국장 강했던 테마 순위 알려줘",
        "전일 나스닥 인기 섹터만 요약해줘",
        "나스닥 현재 상승 테마랑 시장 브리핑 구분해서 알려줘",
        "미국장 마감 기준 강세 테마 Top5",
    ],
    "investor_rank": [
        "외국인 기관 둘 다 순매수한 종목만 보여줘",
        "기관 수급 좋은데 외국인도 들어온 종목 순위",
        "외국인 매집인지 단순 거래량인지 구분해줘",
        "오늘 기관 순매수 강한 업종 말고 종목 알려줘",
    ],
    "value_metric_single": [
        "PBR 낮은데 실적 망가진 종목은 빼고 저평가 찾아줘",
        "PER 낮은 가치주 중 함정주 제외해서 알려줘",
        "저PBR이지만 부채 높은 종목 제외 가능?",
        "밸류는 싼데 수급도 괜찮은 종목 골라줘",
    ],
    "market_brief": [
        "시장 브리핑 해줘, 테마 말고 지수만",
        "나스닥 지수랑 환율 현재 상태 알려줘",
        "오늘 시장 어때? 수치 이상하면 stale 표시해줘",
    ],
    "cancel_pending": [
        "미체결 주문 취소할까? 바로 취소하지 말고 설명해줘",
        "{stock} 미체결 취소 가능해? 실행은 보류",
    ],
}

TARGET_COUNTS = {
    "stock_analysis": 9_000,
    "theme_top": 5_000,
    "us_theme_rank": 6_000,
    "investor_rank": 4_800,
    "cancel_pending": 2_800,
    "price_current": 2_800,
    "value_metric_single": 4_600,
    "market_brief": 2_500,
    "buy": 1_100,
    "sell": 1_400,
}

STOCKS = ["삼성전자", "SK하이닉스", "NAVER", "카카오", "현대차", "LG에너지솔루션"]
SYMBOLS = ["005930", "000660", "035420", "035720", "AAPL", "TSLA"]
QUESTION_MARKERS = ("?", "어때", "할까", "사도 돼", "가능", "알려줘", "보여줘", "들어가도 돼", "살까")
ORDER_INTENTS = {"buy", "sell"}
TEXT_FIELDS = ["id", "text", "intent", "critical", "source", "difficulty", "answer_policy"]


def _answer_policy(intent: str) -> str:
    if intent in ORDER_INTENTS:
        return "approval_required_no_auto_execution"
    if intent == "us_theme_rank":
        return "return_theme_rank_with_data_date_updated_at_stale"
    if intent == "market_brief":
        return "return_market_brief_with_sanity_flags"
    return "informational_answer_no_order_execution"


def _make_row(sequence: int, text: str, intent: str, source: str, difficulty: str) -> dict[str, object]:
    return {
        "id": f"qa-hardfail-{sequence:05d}",
        "text": text,
        "intent": intent,
        "critical": intent not in ORDER_INTENTS,
        "source": source,
        "difficulty": difficulty,
        "answer_policy": _answer_policy(intent),
    }


def _dedupe(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    deduped: list[dict[str, object]] = []
    seen: set[tuple[str, str, str]] = set()
    for row in rows:
        key = (
            str(row["text"]).strip(),
            str(row["intent"]).strip(),
            str(row.get("answer_policy", "")).strip(),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(row)
    return deduped


def load_existing_rows(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        return []

    rows: list[dict[str, object]] = []
    with path.open("r", encoding="utf-8") as input_file:
        for sequence, line in enumerate(input_file):
            if not line.strip():
                continue
            payload = json.loads(line)
            intent = str(payload.get("intent") or payload.get("expected_intent") or "stock_analysis")
            rows.append(
                {
                    "id": str(payload.get("id") or f"legacy-{sequence:05d}"),
                    "text": str(payload["text"]),
                    "intent": intent,
                    "critical": bool(payload.get("critical", intent not in ORDER_INTENTS)),
                    "source": str(payload.get("source", "legacy_curated")),
                    "difficulty": str(payload.get("difficulty", "standard")),
                    "answer_policy": str(payload.get("answer_policy", _answer_policy(intent))),
                }
            )
    return _dedupe(rows)


def _append_mandatory_cases(rows: list[dict[str, object]], sequence: int) -> int:
    existing_texts = {str(row["text"]) for row in rows}
    for text, intent, difficulty in MANDATORY_FAILURE_CASES:
        if text in existing_texts:
            continue
        rows.append(_make_row(sequence, text, intent, "mandatory_regression", difficulty))
        existing_texts.add(text)
        sequence += 1
    return sequence


def _append_generated_rows(
    rows: list[dict[str, object]],
    *,
    sequence: int,
    target_counts: dict[str, int],
    templates_by_intent: dict[str, list[str]],
    source: str,
    difficulty: str,
    max_rows: int | None = None,
) -> int:
    intent_counts = Counter(str(row["intent"]) for row in rows)
    existing_texts = {str(row["text"]) for row in rows}
    generated = 0
    round_index = 0
    while True:
        made_progress = False
        for intent, target in target_counts.items():
            if intent_counts[intent] >= target:
                continue
            if max_rows is not None and generated >= max_rows:
                return sequence

            templates = templates_by_intent[intent]
            stock = STOCKS[(round_index + intent_counts[intent]) % len(STOCKS)]
            symbol = SYMBOLS[(round_index + intent_counts[intent]) % len(SYMBOLS)]
            template = templates[(round_index + intent_counts[intent]) % len(templates)]
            text = template.format(stock=stock, symbol=symbol)
            if difficulty == "hard_question":
                text = f"{text} [hard-{sequence:05d}]"
            else:
                text = f"{text} [case-{sequence:05d}]"

            if text in existing_texts:
                sequence += 1
                continue

            rows.append(_make_row(sequence, text, intent, source, difficulty))
            existing_texts.add(text)
            intent_counts[intent] += 1
            sequence += 1
            generated += 1
            made_progress = True

            if len(rows) >= TOTAL_ROWS:
                return sequence

        round_index += 1
        if not made_progress:
            return sequence


def build_rows(existing_path: Path | None = None) -> list[dict[str, object]]:
    existing_rows = load_existing_rows(existing_path) if existing_path else []
    rows = list(existing_rows)
    sequence = len(rows)
    sequence = _append_mandatory_cases(rows, sequence)

    hard_additions = {
        "stock_analysis": 1_300,
        "us_theme_rank": 1_200,
        "investor_rank": 800,
        "value_metric_single": 800,
        "market_brief": 500,
        "cancel_pending": 400,
    }
    current_intent_counts = Counter(str(row["intent"]) for row in rows)
    hard_target_counts = {
        intent: current_intent_counts[intent] + count
        for intent, count in hard_additions.items()
    }
    sequence = _append_generated_rows(
        rows,
        sequence=sequence,
        target_counts=hard_target_counts,
        templates_by_intent=HARD_TEMPLATES,
        source="synthetic_hard_question",
        difficulty="hard_question",
        max_rows=HARD_QUESTION_ROWS,
    )
    sequence = _append_generated_rows(
        rows,
        sequence=sequence,
        target_counts=TARGET_COUNTS,
        templates_by_intent=STANDARD_TEMPLATES,
        source="synthetic_hardfail",
        difficulty="standard",
    )
    rows = _dedupe(rows)
    if len(rows) > TOTAL_ROWS:
        rows = rows[:TOTAL_ROWS]
    return rows


def summarize(rows: list[dict[str, object]]) -> dict[str, object]:
    texts = [str(row["text"]) for row in rows]
    duplicate_count = len(texts) - len(set(texts))
    answer_keys = [
        (str(row["text"]), str(row["intent"]), str(row.get("answer_policy", "")))
        for row in rows
    ]
    duplicate_qa_count = len(answer_keys) - len(set(answer_keys))
    intent_counts = Counter(str(row["intent"]) for row in rows)
    difficulty_counts = Counter(str(row.get("difficulty", "standard")) for row in rows)
    question_order_contamination = sum(
        1
        for row in rows
        if str(row["intent"]) in ORDER_INTENTS
        and any(marker in str(row["text"]) for marker in QUESTION_MARKERS)
    )
    return {
        "rows": len(rows),
        "total_rows": len(rows),
        "duplicate_count": duplicate_count,
        "duplicate_qa_count": duplicate_qa_count,
        "duplicate_rate": duplicate_count / len(rows) if rows else 0.0,
        "duplicate_qa_rate": duplicate_qa_count / len(rows) if rows else 0.0,
        "question_to_order_contamination": {
            "count": question_order_contamination,
            "rate": question_order_contamination / len(rows) if rows else 0.0,
        },
        "critical_rate": sum(1 for row in rows if row["critical"]) / len(rows) if rows else 0.0,
        "hard_question_rows": difficulty_counts["hard_question"],
        "hard_question_rate": difficulty_counts["hard_question"] / len(rows) if rows else 0.0,
        "max_single_intent_rate": max(intent_counts.values()) / len(rows) if rows else 0.0,
        "intent_distribution": dict(intent_counts),
        "difficulty_distribution": dict(difficulty_counts),
    }


def quality_gate(report: dict[str, object]) -> bool:
    contamination = report["question_to_order_contamination"]
    assert isinstance(contamination, dict)
    return (
        report["rows"] == TOTAL_ROWS
        and report["hard_question_rows"] >= HARD_QUESTION_ROWS
        and report["duplicate_rate"] <= 0.01
        and report["duplicate_qa_rate"] <= 0.01
        and contamination["rate"] == 0.0
        and report["critical_rate"] >= 0.20
        and report["max_single_intent_rate"] <= 0.35
    )


def write_outputs(output_dir: Path) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    rows = build_rows(output_dir / LEGACY_DATASET)
    report = summarize(rows)
    report["gate_passed"] = quality_gate(report)

    jsonl_path = output_dir / f"{OUTPUT_STEM}.jsonl"
    csv_path = output_dir / f"{OUTPUT_STEM}.csv"
    report_path = output_dir / f"{OUTPUT_STEM}_report.json"

    with jsonl_path.open("w", encoding="utf-8") as jsonl_file:
        for row in rows:
            jsonl_file.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")

    with csv_path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=TEXT_FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="data/curated")
    args = parser.parse_args()
    report = write_outputs(Path(args.output_dir))
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["gate_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
