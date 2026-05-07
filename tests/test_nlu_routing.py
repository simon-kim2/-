import unittest

from simon.approval import ApprovalGuard
from simon.intents import Intent
from simon.nlu.natural_language_router import NaturalLanguageRouter


class NaturalLanguageRouterTest(unittest.TestCase):
    def setUp(self):
        self.approval_guard = ApprovalGuard()
        self.router = NaturalLanguageRouter(approval_guard=self.approval_guard)

    def test_us_theme_rank_priority_beats_market_brief(self):
        cases = [
            "나스닥 현재 인기 상승 테마 알려줘",
            "미국 증시 강세 테마 순위 보여줘",
            "nasdaq 상승 섹터 랭킹",
        ]
        for text in cases:
            with self.subTest(text=text):
                result = self.router.route(text)
                self.assertEqual(Intent.US_THEME_RANK, result.intent)

    def test_investor_rank_priority(self):
        cases = [
            "외국인 기관 수급 좋은 종목 순위",
            "기관 순매수 랭킹 알려줘",
            "외국인 매집 종목 보여줘",
        ]
        for text in cases:
            with self.subTest(text=text):
                self.assertEqual(Intent.INVESTOR_RANK, self.router.route(text).intent)

    def test_value_screen_priority(self):
        cases = [
            "PBR 낮은 저평가 종목 찾아줘",
            "PER 낮은 가치주 순위 알려줘",
            "밸류 좋은 종목 스크리닝",
        ]
        for text in cases:
            with self.subTest(text=text):
                self.assertEqual(Intent.VALUE_SCREEN, self.router.route(text).intent)

    def test_question_forms_never_route_to_order(self):
        cases = [
            "삼성전자 사도 돼?",
            "AAPL 10주 매수할까?",
            "TSLA 사는 거 어때?",
            "005930 3주 매수 가능?",
            "나스닥 테마 사도 돼?",
        ]
        for text in cases:
            with self.subTest(text=text):
                result = self.router.route(text)
                self.assertNotEqual(Intent.ORDER, result.intent)
                self.assertFalse(result.allowed_to_order)

    def test_imperative_quantity_without_approval_is_demoted(self):
        result = self.router.route("AAPL 10주 매수")
        self.assertEqual(Intent.ORDER_QUERY, result.intent)
        self.assertFalse(result.allowed_to_order)

    def test_order_requires_verify_and_consume(self):
        token = self.approval_guard.create_approval(symbol="AAPL", side="buy", quantity=10)

        first = self.router.route("AAPL 10주 매수", approval_token=token)
        self.assertEqual(Intent.ORDER, first.intent)
        self.assertTrue(first.allowed_to_order)

        second = self.router.route("AAPL 10주 매수", approval_token=token)
        self.assertEqual(Intent.ORDER_QUERY, second.intent)
        self.assertFalse(second.allowed_to_order)

    def test_sidongtv_is_advisory_only_and_cannot_trigger_order(self):
        token = self.approval_guard.create_approval(symbol="AAPL", side="buy", quantity=10)
        result = self.router.route("AAPL 10주 매수", approval_token=token, source="sidongtv")
        self.assertEqual(Intent.ORDER_QUERY, result.intent)
        self.assertTrue(result.advisory_only)
        self.assertFalse(result.allowed_to_order)

    def test_order_false_positive_rate_quality_gate(self):
        negative_cases = [
            "나스닥 현재 인기 상승 테마 알려줘",
            "외국인 기관 수급 좋은 종목 순위",
            "PBR 낮은 저평가 종목 찾아줘",
            "삼성전자 사도 돼?",
            "AAPL 10주 매수할까?",
            "TSLA 현재가 알려줘",
            "미체결 주문 취소할까?",
        ]
        false_positives = [text for text in negative_cases if self.router.route(text).intent is Intent.ORDER]
        self.assertEqual([], false_positives)


if __name__ == "__main__":
    unittest.main()
