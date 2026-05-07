import tempfile
import unittest
from pathlib import Path

from tools.build_qa_hardfail_dataset import build_rows, quality_gate, summarize, write_outputs


class DatasetBuilderTest(unittest.TestCase):
    def test_hardfail_dataset_quality_gate(self):
        rows = build_rows()
        report = summarize(rows)
        self.assertTrue(quality_gate(report))
        self.assertEqual(10_000, report["rows"])
        self.assertEqual(0, report["duplicate_count"])
        self.assertEqual(0.0, report["question_to_order_contamination"]["rate"])
        self.assertLessEqual(report["max_single_intent_rate"], 0.35)

    def test_writes_expected_outputs(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            report = write_outputs(Path(tmpdir))
            self.assertTrue(report["gate_passed"])
            self.assertTrue((Path(tmpdir) / "qa_intent_20000.jsonl").exists())
            self.assertTrue((Path(tmpdir) / "qa_intent_20000.csv").exists())
            self.assertTrue((Path(tmpdir) / "qa_intent_20000_report.json").exists())


if __name__ == "__main__":
    unittest.main()
