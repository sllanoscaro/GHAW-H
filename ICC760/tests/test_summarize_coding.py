import tempfile
import unittest
from pathlib import Path

from ICC760.scripts import summarize_coding as coding


class SummarizeCodingTests(unittest.TestCase):
    def test_pilot_counts_and_table_preserve_all_inspected_prs(self):
        rows = coding.load_rows(coding.DEFAULT_INPUT)
        summary = coding.summarize(rows)
        self.assertEqual((summary["inspected"], summary["coded"], summary["pending"]), (10, 7, 3))
        self.assertEqual(summary["evidence_counts"], {"yes": 3, "ambiguous": 4, "no": 3})
        self.assertEqual(summary["status_evidence"], {
            "codificado": {"yes": 3, "ambiguous": 4, "no": 0},
            "pendiente": {"yes": 0, "ambiguous": 0, "no": 3},
        })
        self.assertEqual(summary["explicit_evidence"], 3)
        self.assertEqual(summary["insufficient_evidence"], 4)
        self.assertEqual(len(summary["categories"]), 6)
        for category in summary["categories"]:
            self.assertEqual(category["count"], 1)
            self.assertAlmostEqual(category["percentage"], 100 / 3)
        report = coding.format_report(summary, coding.DEFAULT_INPUT, rows)
        self.assertIn("N=3;", report)
        self.assertEqual(sum(line.startswith("| ") and " #" in line for line in report.splitlines()), 10)
        self.assertEqual(report.count("Contexto/hipótesis; causa no confirmada"), 4)
        for row in rows:
            self.assertEqual(report.count(f" #{row['pr_id']} |"), 1)

    def test_changed_yes_fixture_uses_only_coded_yes_as_denominator(self):
        path = Path(__file__).parent / "fixtures" / "coding_changed_yes.csv"
        rows = coding.load_rows(path)
        summary = coding.summarize(rows)
        self.assertEqual(summary["evidence_counts"]["yes"], 2)
        self.assertEqual(summary["explicit_evidence"], 2)
        self.assertEqual(summary["categories"], [
            {"category": "datos_obsoletos", "count": 2, "percentage": 100.0},
            {"category": "error_parseo", "count": 1, "percentage": 50.0},
        ])
        report = coding.format_report(summary, path, rows)
        self.assertIn("N=2;", report)
        self.assertNotIn("N=3;", report)
        self.assertIn("| Pendiente | 0 | 0 | 2 | 2 |", report)
        rows[-1].update({"evidencia_disponible": "yes", "razon_principal": "pr_huerfano"})
        with_pending_yes = coding.summarize(rows)
        self.assertEqual(with_pending_yes["evidence_counts"]["yes"], 3)
        self.assertEqual(with_pending_yes["explicit_evidence"], 2)
        self.assertEqual(with_pending_yes["categories"], summary["categories"])

    def test_no_coded_yes_and_empty_sample(self):
        for rows in ([], [{"repo": "a/b", "pr_id": "1", "coding status": "pendiente", "evidencia_disponible": "yes"}]):
            with self.subTest(rows=rows):
                summary = coding.summarize(rows)
                self.assertEqual(summary["categories"], [])
                self.assertIn("N=0;", coding.format_report(summary, Path("empty.csv"), rows))

    def test_invalid_dimensions_and_duplicate_prs_are_rejected(self):
        header = "repo,pr_id,evidencia_disponible,razon_principal,razon_secundaria,coding status\n"
        for data in ("a/b,1,maybe,,,codificado\n", "a/b,1,yes,,,unknown\n",
                     "a/b,1,yes,,,codificado\nA/B,1,no,,,pendiente\n"):
            with self.subTest(data=data), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "invalid.csv"
                path.write_text(header + data, encoding="utf-8")
                with self.assertRaises(ValueError):
                    coding.load_rows(path)


if __name__ == "__main__":
    unittest.main()
