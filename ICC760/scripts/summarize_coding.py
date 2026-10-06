"""Summarize manual qualitative coding in ``analisis_cualitativo.csv``.

By default, a PR is considered reviewed when ``coding status`` is ``codificado``.
Explicit evidence means ``evidencia_disponible == yes``; insufficient evidence
means ``no`` or ``ambiguous``. Category counts and percentages include only
reviewed PRs with explicit evidence, using those PRs as the denominator.
Categories are multi-label: a PR is counted once per category if it appears as
either its primary or secondary reason.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
DEFAULT_INPUT = PROJECT_DIR / "analisis_cualitativo.csv"

REQUIRED_COLUMNS = {
    "repo",
    "pr_id",
    "evidencia_disponible",
    "razon_principal",
    "razon_secundaria",
    "coding status",
}
REVIEWED_STATUS = "codificado"
EXPLICIT_EVIDENCE = "yes"
INSUFFICIENT_EVIDENCE = {"no", "ambiguous"}


def load_rows(path: Path) -> list[dict[str, str]]:
    """Load and validate CSV rows, preserving multiline quoted fields."""
    with path.open("r", encoding="utf-8-sig", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        if reader.fieldnames is None:
            raise ValueError("El CSV está vacío o no tiene encabezado")
        missing = REQUIRED_COLUMNS - set(reader.fieldnames)
        if missing:
            raise ValueError(f"Faltan columnas requeridas: {', '.join(sorted(missing))}")
        rows = list(reader)

    for line_number, row in enumerate(rows, start=2):
        if not (row.get("repo") or "").strip() or not (row.get("pr_id") or "").strip():
            raise ValueError(f"Falta repo o pr_id en la fila CSV {line_number}")
    return rows


def summarize(rows: list[dict[str, str]]) -> dict:
    reviewed = [
        row for row in rows
        if (row.get("coding status") or "").strip().casefold() == REVIEWED_STATUS
    ]
    explicit = [
        row for row in reviewed
        if (row.get("evidencia_disponible") or "").strip().casefold() == EXPLICIT_EVIDENCE
    ]
    insufficient = [
        row for row in reviewed
        if (row.get("evidencia_disponible") or "").strip().casefold() in INSUFFICIENT_EVIDENCE
    ]

    # Category distribution is restricted to reviewed PRs with explicit evidence.
    # Sets ensure a repeated code on the same PR cannot inflate its count.
    category_prs: dict[str, set[tuple[str, str]]] = {}
    for row in explicit:
        pr_key = ((row.get("repo") or "").strip(), (row.get("pr_id") or "").strip())
        codes = {
            (row.get(field) or "").strip()
            for field in ("razon_principal", "razon_secundaria")
        }
        for code in codes - {""}:
            category_prs.setdefault(code, set()).add(pr_key)

    denominator = len(explicit)
    categories = [
        {
            "category": category,
            "count": len(prs),
            "percentage": (100 * len(prs) / denominator) if denominator else 0.0,
        }
        for category, prs in sorted(category_prs.items())
    ]
    return {
        "total_rows": len(rows),
        "reviewed": len(reviewed),
        "explicit_evidence": len(explicit),
        "insufficient_evidence": len(insufficient),
        "categories": categories,
    }


def format_report(summary: dict, input_path: Path) -> str:
    lines = [
        f"Resumen de codificación: {input_path}",
        "",
        f"Total PRs reviewed: {summary['reviewed']}",
        f"PRs with explicit evidence: {summary['explicit_evidence']}",
        f"PRs without sufficient evidence: {summary['insufficient_evidence']}",
        f"Filas totales en el CSV: {summary['total_rows']}",
        "",
        "PRs per category / Percentage per category",
        "(sólo PRs codificados con evidencia explícita yes; categorías no excluyentes)",
        "",
        "| Categoría | PRs | Porcentaje |",
        "| --- | ---: | ---: |",
    ]
    if summary["categories"]:
        lines.extend(
            f"| `{item['category']}` | {item['count']} | {item['percentage']:.1f}% |"
            for item in summary["categories"]
        )
    else:
        lines.append("| *(sin categorías asignadas)* | 0 | 0.0% |")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help=f"CSV de entrada (predeterminado: {DEFAULT_INPUT})")
    parser.add_argument("--output", type=Path, help="Guardar también el informe Markdown en este archivo")
    args = parser.parse_args()

    try:
        rows = load_rows(args.input)
    except (OSError, csv.Error, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2

    report = format_report(summarize(rows), args.input)
    print(report)
    if args.output:
        try:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(report + "\n", encoding="utf-8")
        except OSError as error:
            print(f"Error al guardar {args.output}: {error}", file=sys.stderr)
            return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
