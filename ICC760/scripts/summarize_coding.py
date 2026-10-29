"""Validate final manual coding and reproduce the article's descriptive tables.

Each unique PR has one evidence level. Only explicit evidence receives exactly
one primary reason; contextual signals never contribute to reason counts.
This validates the coding schema, not the causal interpretation of sources.
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter
from pathlib import Path
from typing import NamedTuple
from urllib.parse import urlparse


PROJECT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_INPUT = PROJECT_DIR / "analisis_cualitativo.csv"
EVIDENCE_LEVELS = ("explícita", "ambigua", "ausente")
REASONS = (
    "cambio_no_necesario", "datos_obsoletos", "continuacion_manual",
    "expiracion_automatica", "implementacion_insuficiente", "destino_incorrecto",
)
SIGNALS = frozenset({
    "ci_fallido", "archivo_protegido", "alerta_amenaza_agente", "error_parseo",
    "error_red_agente", "cierre_sin_justificacion", "revision_manual_solicitada",
    "instruccion_cierre_manual", "aprobado_sin_merge", "validacion_no_concluyente",
    "posible_obsolescencia", "posible_redundancia", "revision_no_concluyente",
    "otro_pr_existente", "contenido_posiblemente_ya_integrado",
    "rechazo_sin_motivo_documentado", "posible_reemplazo_por_otro_pr",
})
REQUIRED_COLUMNS = frozenset({
    "repo", "pr_id", "pr_url", "workflow_id", "evidencia_disponible",
    "razon_principal", "senales_contextuales", "fuente_evidencia",
    "nota_revision", "verificacion_fuente",
})


class CodingRow(NamedTuple):
    """Immutable validated fields used in the descriptive analysis."""

    repo: str
    pr_id: int
    pr_url: str
    workflow_id: str
    evidence: str
    reason: str
    signals: tuple[str, ...]
    source_url: str


class CodingSummary(NamedTuple):
    total: int
    repositories: int
    workflow_names: int
    repository_workflows: int
    evidence: Counter[str]
    reasons: Counter[str]
    ambiguous_ci: int


def validate_row(row: dict[str, str], line: int) -> CodingRow:
    """Reject incomplete records and assignments forbidden by the codebook."""
    for field in ("repo", "pr_id", "pr_url", "workflow_id", "fuente_evidencia", "nota_revision"):
        if not row[field]:
            raise ValueError(f"Fila {line}: {field} no puede estar vacío")
    if not row["pr_id"].isascii() or not row["pr_id"].isdigit() or int(row["pr_id"]) < 1:
        raise ValueError(f"Fila {line}: pr_id debe ser un entero positivo: {row['pr_id']!r}")
    expected_url = f"https://github.com/{row['repo']}/pull/{int(row['pr_id'])}"
    if row["pr_url"] != expected_url:
        raise ValueError(f"Fila {line}: pr_url debe coincidir con repo/pr_id: {expected_url}")
    evidence, reason = row["evidencia_disponible"], row["razon_principal"]
    if evidence not in EVIDENCE_LEVELS:
        raise ValueError(f"Fila {line}: evidencia_disponible inválida: {evidence!r}")
    if evidence == "explícita":
        if reason not in REASONS:
            raise ValueError(f"Fila {line}: evidencia explícita requiere una razón del codebook: {reason!r}")
        source = urlparse(row["verificacion_fuente"])
        if source.scheme != "https" or source.netloc != "github.com" or not source.path.strip("/"):
            raise ValueError(f"Fila {line}: falta URL de GitHub válida en verificacion_fuente")
    elif reason:
        raise ValueError(f"Fila {line}: evidencia {evidence} no admite razon_principal")
    signals = tuple(value.strip() for value in row["senales_contextuales"].split(";")) if row["senales_contextuales"] else ()
    if set(signals) - SIGNALS or len(signals) != len(set(signals)):
        raise ValueError(f"Fila {line}: señales desconocidas o duplicadas: {signals}")
    if evidence == "ausente" and signals:
        raise ValueError(f"Fila {line}: evidencia ausente no admite señales contextuales")
    return CodingRow(row["repo"], int(row["pr_id"]), row["pr_url"], row["workflow_id"],
                     evidence, reason, signals, row["verificacion_fuente"])


def load_rows(path: Path) -> list[CodingRow]:
    """Read the final CSV schema; unrelated extra columns are ignored."""
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames is None:
            raise ValueError(f"{path}: el CSV no tiene encabezado")
        if len(reader.fieldnames) != len(set(reader.fieldnames)):
            raise ValueError(f"{path}: columnas duplicadas")
        missing = REQUIRED_COLUMNS - set(reader.fieldnames)
        if missing:
            raise ValueError(f"{path}: faltan columnas: {', '.join(sorted(missing))}")
        rows: list[CodingRow] = []
        seen: set[tuple[str, int]] = set()
        for raw in reader:
            if None in raw or any(raw[field] is None for field in REQUIRED_COLUMNS):
                raise ValueError(f"{path}, línea {reader.line_num}: número de campos incorrecto")
            row = validate_row({field: raw[field].strip() for field in REQUIRED_COLUMNS}, reader.line_num)
            key = (row.repo.casefold(), row.pr_id)
            if key in seen:
                raise ValueError(f"{path}, línea {reader.line_num}: PR duplicado: {key}")
            seen.add(key)
            rows.append(row)
    if not rows:
        raise ValueError(f"{path}: no contiene PRs para resumir")
    return rows


def summarize(rows: list[CodingRow]) -> CodingSummary:
    """Count validated PRs without treating contextual signals as reasons."""
    return CodingSummary(
        len(rows), len({row.repo.casefold() for row in rows}),
        len({row.workflow_id for row in rows}),
        len({(row.repo.casefold(), row.workflow_id) for row in rows}),
        Counter(row.evidence for row in rows),
        Counter(row.reason for row in rows if row.evidence == "explícita"),
        sum(row.evidence == "ambigua" and "ci_fallido" in row.signals for row in rows),
    )


def format_report(summary: CodingSummary, input_path: Path, rows: list[CodingRow]) -> str:
    lines = [
        f"# Resumen de codificación final: {input_path.name}", "",
        f"PRs únicos: {summary.total}; repositorios: {summary.repositories}; "
        f"nombres de workflow: {summary.workflow_names}; pares repositorio–workflow: {summary.repository_workflows}.",
        "", "## Disponibilidad de evidencia", "",
        "| Nivel | PRs | Porcentaje del total |", "| --- | ---: | ---: |",
    ]
    for level in EVIDENCE_LEVELS:
        count = summary.evidence[level]
        percentage = f"{100 * count / summary.total:.1f}".replace(".", ",")
        lines.append(f"| {level} | {count} | {percentage}% |")
    lines.extend([
        "", "## Razones principales documentadas", "",
        f"Denominador: {summary.evidence['explícita']} PRs con evidencia explícita; una razón por PR.",
        "Las señales contextuales no aportan causas. La atribución causal requiere revisión manual.",
        "", "| Razón | PRs |", "| --- | ---: |",
    ])
    lines.extend(f"| `{reason}` | {summary.reasons[reason]} |" for reason in REASONS)
    lines.extend([
        "", f"PRs ambiguos con `ci_fallido`: {summary.ambiguous_ci}/{summary.evidence['ambigua']}.",
        "", "## Fuentes de los casos explícitos", "",
        "| PR | Razón principal | Fuente |", "| --- | --- | --- |",
    ])
    lines.extend(f"| [{row.repo}#{row.pr_id}]({row.pr_url}) | `{row.reason}` | [Fuente]({row.source_url}) |"
                 for row in rows if row.evidence == "explícita")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, help="Guardar el resumen Markdown")
    args = parser.parse_args()
    try:
        rows = load_rows(args.input)
        report = format_report(summarize(rows), args.input, rows)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(report + "\n", encoding="utf-8")
    except (OSError, csv.Error, ValueError) as error:
        print(f"Error al resumir {args.input}: {error}", file=sys.stderr)
        return 2
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
