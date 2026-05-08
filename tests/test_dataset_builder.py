import tempfile
import unittest
from pathlib import Path

from tools.build_qa_hardfail_dataset import HARD_QUESTION_ROWS, TOTAL_ROWS, build_rows, quality_gate, summarize, write_outputs


class DatasetBuilderTest(unittest.TestCase):
    def test_hardfail_dataset_quality_gate(self):
        rows = build_rows()
        report = summarize(rows)
        self.assertTrue(quality_gate(report))
        self.assertEqual(TOTAL_ROWS, report["rows"])
        self.assertEqual(TOTAL_ROWS, report["total_rows"])
        self.assertGreaterEqual(report["hard_question_rows"], HARD_QUESTION_ROWS)
        self.assertEqual(0, report["duplicate_count"])
        self.assertEqual(0, report["duplicate_qa_count"])
        self.assertEqual(0.0, report["question_to_order_contamination"]["rate"])
        self.assertLessEqual(report["max_single_intent_rate"], 0.35)

    def test_writes_expected_outputs(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            report = write_outputs(Path(tmpdir))
            self.assertTrue(report["gate_passed"])
            self.assertTrue((Path(tmpdir) / "qa_intent_40000.jsonl").exists())
            self.assertTrue((Path(tmpdir) / "qa_intent_40000.csv").exists())
            self.assertTrue((Path(tmpdir) / "qa_intent_40000_report.json").exists())

    def test_mandatory_hard_questions_are_included(self):
        rows = build_rows()
        texts = {str(row["text"]) for row in rows}
        for required in [
            "어제 나스닥 상승 테마분야는 뭐야?",
            "삼성전자 사도 돼?",
            "AAPL 10주 매수할까?",
            "TSLA 사는 거 어때?",
        ]:
            self.assertIn(required, texts)


if __name__ == "__main__":
    unittest.main()
