import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from ICC760.scripts import summarize_coding as coding


class SummarizeCodingTests(unittest.TestCase):
    def test_final_csv_matches_archived_extraction_and_article(self):
        rows = coding.load_rows(coding.DEFAULT_INPUT)
        summary = coding.summarize(rows)
        records = json.loads((coding.PROJECT_DIR / 'output/unmerged_prs.json').read_text())
        self.assertEqual({row.pr_url for row in rows}, {record['pr_url'] for record in records})
        self.assertTrue(all(record['pr_state'] == 'closed' and record['pr_merged_at'] is None for record in records))
        self.assertEqual((summary.total, summary.repositories, summary.workflow_names, summary.repository_workflows), (82, 17, 15, 17))
        self.assertEqual(summary.evidence, {'explícita': 9, 'ambigua': 37, 'ausente': 36})
        self.assertEqual(summary.reasons, {
            'cambio_no_necesario': 3, 'datos_obsoletos': 2,
            'continuacion_manual': 1, 'expiracion_automatica': 1,
            'implementacion_insuficiente': 1, 'destino_incorrecto': 1,
        })
        self.assertEqual(summary.ambiguous_ci, 25)
        evidence = json.loads((coding.PROJECT_DIR / 'output/pr_evidence.json').read_text())['pull_requests']
        sources = {item.get('html_url') for record in evidence
                   for field in ('comments', 'reviews', 'review_comments') for item in record[field]}
        self.assertTrue(all(row.source_url in sources for row in rows if row.evidence == 'explícita'))

    def test_cli_reproduces_committed_report(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'summary.md'
            result = subprocess.run([
                sys.executable, str(coding.PROJECT_DIR / 'scripts/summarize_coding.py'),
                '--input', str(coding.DEFAULT_INPUT), '--output', str(output),
            ], capture_output=True, text=True, check=True)
            self.assertEqual(result.stdout, output.read_text())
            self.assertEqual(output.read_text(), (coding.PROJECT_DIR / 'output/final_summary.md').read_text())

    def test_invalid_assignments_and_duplicates_are_rejected(self):
        with coding.DEFAULT_INPUT.open(newline='') as stream:
            originals = list(csv.DictReader(stream))
        explicit = next(row for row in originals if row['evidencia_disponible'] == 'explícita')
        absent = next(row for row in originals if row['evidencia_disponible'] == 'ausente')
        cases = [
            [{**explicit, 'razon_principal': ''}],
            [{**explicit, 'verificacion_fuente': ''}],
            [{**explicit, 'evidencia_disponible': 'ambigua'}],
            [{**absent, 'senales_contextuales': 'ci_fallido'}],
            [{**explicit, 'razon_principal': 'datos_obsoletos;cambio_no_necesario'}],
            [{**absent, 'pr_id': '0'}],
            [absent, absent],
            [],
        ]
        for rows in cases:
            with self.subTest(rows=rows), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / 'invalid.csv'
                with path.open('w', newline='') as stream:
                    writer = csv.DictWriter(stream, fieldnames=list(originals[0]))
                    writer.writeheader()
                    writer.writerows(rows)
                with self.assertRaises(ValueError):
                    coding.load_rows(path)


if __name__ == '__main__':
    unittest.main()
