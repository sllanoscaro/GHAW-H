"""Summarize manual qualitative coding in ``analisis_cualitativo.csv``.

Each CSV row represents an inspected PR. Coding status and evidence quality
are independent dimensions: coding may describe context without a supported
closure cause. Category counts and percentages include only coded PRs with
``evidencia_disponible == yes``, using those PRs as the denominator.
Categories are multi-label: a PR is counted once per category if it appears as
either its primary or secondary reason.
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter
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
CODED_STATUS = "codificado"
EXPLICIT_EVIDENCE = "yes"
INSUFFICIENT_EVIDENCE = {"no", "ambiguous"}
REPO_LABELS = {
    "advanced-security/advanced-security-material": "advanced-security",
    "elastic/elastic-docs-skills": "elastic-docs-skills",
    "elastic/terraform-provider-elasticstack": "elasticstack",
    "fsprojects/FSharp.Formatting": "FSharp.Formatting",
    "github/copilot-sdk": "copilot-sdk",
    "iamnbutler/gpui-unofficial": "gpui-unofficial",
    "dotnet/msbuild": "msbuild",
    "dotnet/runtime": "runtime",
}
EVIDENCE_LABELS = {"no": "No", "ambiguous": "Ambigua", "yes": "Sí"}
STATUS_LABELS = {"pendiente": "Pendiente", "codificado": "Codificado"}
REASON_LABELS = {
    "cierre_silencioso": "Cierre silencioso",
    "error_red_agente": "Error de red del agente",
    "modificacion_archivo_protegido": "Archivo protegido",
    "abandono_revisor": "Abandono del revisor",
    "datos_obsoletos": "Datos obsoletos",
    "amenaza_agente": "Amenaza del agente",
    "error_parseo": "Error de parseo",
    "fallo_orquestacion": "Fallo de orquestación",
    "pr_huerfano": "PR huérfano",
}


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

    seen = set()
    for line_number, row in enumerate(rows, start=2):
        if not (row.get("repo") or "").strip() or not (row.get("pr_id") or "").strip():
            raise ValueError(f"Falta repo o pr_id en la fila CSV {line_number}")
        key = (row["repo"].strip().casefold(), row["pr_id"].strip())
        if key in seen:
            raise ValueError(f"PR duplicado en la fila CSV {line_number}: {key}")
        seen.add(key)
        for field, allowed in (("coding status", STATUS_LABELS), ("evidencia_disponible", EVIDENCE_LABELS)):
            if (row.get(field) or "").strip().casefold() not in allowed:
                raise ValueError(f"Valor inválido de {field} en la fila CSV {line_number}")
    return rows


def summarize(rows: list[dict[str, str]]) -> dict:
    coded = [
        row for row in rows
        if (row.get("coding status") or "").strip().casefold() == CODED_STATUS
    ]
    explicit = [
        row for row in coded
        if (row.get("evidencia_disponible") or "").strip().casefold() == EXPLICIT_EVIDENCE
    ]
    insufficient = [
        row for row in coded
        if (row.get("evidencia_disponible") or "").strip().casefold() in INSUFFICIENT_EVIDENCE
    ]

    # Category distribution is restricted to coded PRs with explicit evidence.
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
    evidence_counts = Counter((row.get("evidencia_disponible") or "").strip().casefold() for row in rows)
    status_counts = Counter((row.get("coding status") or "").strip().casefold() for row in rows)
    cross_counts = Counter(((row.get("coding status") or "").strip().casefold(),
                            (row.get("evidencia_disponible") or "").strip().casefold()) for row in rows)
    return {
        "total_rows": len(rows),
        "inspected": len(rows),
        "coded": len(coded),
        "pending": status_counts["pendiente"],
        "evidence_counts": {quality: evidence_counts[quality] for quality in ("yes", "ambiguous", "no")},
        "status_evidence": {status: {quality: cross_counts[status, quality] for quality in ("yes", "ambiguous", "no")}
                            for status in ("codificado", "pendiente")},
        "explicit_evidence": len(explicit),
        "insufficient_evidence": len(insufficient),
        "categories": categories,
    }


def format_report(summary: dict, input_path: Path, rows: list[dict[str, str]]) -> str:
    lines = [
        f"Resumen de codificación: {input_path}",
        "",
        f"PRs inspeccionados (una fila por PR): {summary['inspected']}",
        f"PRs codificados: {summary['coded']}",
        f"PRs pendientes: {summary['pending']}",
        f"Calidad de evidencia en todos los inspeccionados: yes={summary['evidence_counts']['yes']}, "
        f"ambiguous={summary['evidence_counts']['ambiguous']}, no={summary['evidence_counts']['no']}",
        f"PRs codificados con evidencia explícita (yes): {summary['explicit_evidence']}",
        f"PRs codificados sin evidencia suficiente (ambiguous/no): {summary['insufficient_evidence']}",
        "",
        "Inspeccionado significa examinado y registrado en el CSV; codificado puede incluir clasificación contextual sin causa confirmada.",
        "",
        "## Cruce de estado de codificación y calidad de evidencia",
        "",
        "| Estado | yes | ambiguous | no | Total |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for status, counts in summary["status_evidence"].items():
        lines.append(f"| {STATUS_LABELS[status]} | {counts['yes']} | {counts['ambiguous']} | {counts['no']} | {sum(counts.values())} |")
    counts = summary["evidence_counts"]
    lines.extend([
        f"| Total | {counts['yes']} | {counts['ambiguous']} | {counts['no']} | {summary['inspected']} |",
        "",
        "## Distribución de razones respaldadas según la codificación manual",
        "",
        "Sólo casos codificados con evidencia explícita yes. La extracción no valida automáticamente la atribución causal.",
        f"(N={summary['explicit_evidence']}; categorías no excluyentes)",
        "",
        "| Categoría | PRs | Porcentaje |",
        "| --- | ---: | ---: |",
    ])
    if summary["categories"]:
        lines.extend(
            f"| `{item['category']}` | {item['count']} | {item['percentage']:.1f}% |"
            for item in summary["categories"]
        )
    else:
        lines.append("| *(sin categorías asignadas)* | 0 | 0.0% |")

    lines.extend(
        [
            "",
            "## Tabla cualitativa de los PRs seleccionados",
            "",
            "Esta tabla se genera desde el CSV fuente y sustenta la tabla cualitativa del paper.",
            "Las categorías con evidencia ambiguous son anotaciones contextuales o hipótesis originales, no causas confirmadas; se excluyen de los porcentajes anteriores.",
            "",
            "| PR | Evidencia | Estado | Categoría principal | Categoría secundaria | Alcance de las categorías |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
    )
    for row in rows:
        repository = (row.get("repo") or "").strip()
        pr_label = REPO_LABELS.get(repository, repository.rsplit("/", 1)[-1])
        evidence = (row.get("evidencia_disponible") or "").strip().casefold()
        status = (row.get("coding status") or "").strip().casefold()
        primary = (row.get("razon_principal") or "").strip()
        secondary = (row.get("razon_secundaria") or "").strip()
        if status == CODED_STATUS and evidence == EXPLICIT_EVIDENCE:
            scope = "Respaldadas según codificación manual" if primary or secondary else "Sin categorías asignadas"
        elif evidence == "ambiguous" and (primary or secondary):
            scope = "Contexto/hipótesis; causa no confirmada"
        else:
            scope = "Sin causa respaldada"
        lines.append(
            "| {} #{} | {} | {} | {} | {} | {} |".format(
                pr_label,
                (row.get("pr_id") or "").strip(),
                EVIDENCE_LABELS.get(evidence, evidence or "---"),
                STATUS_LABELS.get(status, status or "---"),
                REASON_LABELS.get(primary, primary or "---"),
                REASON_LABELS.get(secondary, secondary or "---"),
                scope,
            )
        )
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

    report = format_report(summarize(rows), args.input, rows)
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
