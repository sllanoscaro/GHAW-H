"""Collect qualitative evidence for closed, unmerged pull requests.

Requires GitHub CLI (``gh``) authenticated for the relevant repositories.
By default reads ``ICC760/output/unmerged_prs.json`` and writes
``ICC760/output/pr_evidence.json``. Supports resuming from the output file.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
DEFAULT_INPUT = PROJECT_DIR / "output" / "unmerged_prs.json"
DEFAULT_OUTPUT = PROJECT_DIR / "output" / "pr_evidence.json"


class GitHubCLIError(RuntimeError):
    """Raised when a GitHub CLI request cannot be completed."""


def gh_json(args: list[str], *, retries: int = 3) -> Any:
    """Run ``gh`` and decode its JSON output, retrying transient failures."""
    for attempt in range(retries):
        try:
            proc = subprocess.run(
                ["gh", *args], capture_output=True, text=True, timeout=180,
                errors="replace",
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            if attempt + 1 == retries:
                raise GitHubCLIError(str(error)) from error
            time.sleep(2**attempt)
            continue

        if proc.returncode == 0:
            if not proc.stdout.strip():
                return None
            try:
                return json.loads(proc.stdout)
            except json.JSONDecodeError as error:
                raise GitHubCLIError(f"gh devolvió JSON inválido: {error}") from error

        message = (proc.stderr or proc.stdout).strip()
        transient = any(word in message.lower() for word in ("rate limit", "secondary", "abuse", "temporarily unavailable"))
        if attempt + 1 < retries and transient:
            time.sleep(5 * (attempt + 1))
            continue
        raise GitHubCLIError(message or f"gh terminó con código {proc.returncode}")
    raise GitHubCLIError("Se agotaron los reintentos de gh")


def api(repo: str, endpoint: str) -> Any:
    """Fetch every page from a REST endpoint, returning all items."""
    result = gh_json(["api", "--paginate", "--slurp", f"repos/{repo}/{endpoint}"])
    if result is None:
        return []
    if not isinstance(result, list):
        return result
    # With --slurp, each page is an array or an object with an item collection.
    combined: list[Any] = []
    for page in result:
        if isinstance(page, list):
            combined.extend(page)
        elif isinstance(page, dict):
            items = page.get("items")
            if isinstance(items, list):
                combined.extend(items)
            elif isinstance(page.get("comments"), list):
                combined.extend(page["comments"])
            else:
                combined.append(page)
    return combined


def fetch_pr_evidence(record: dict[str, Any]) -> dict[str, Any]:
    repo = record.get("target_repo")
    number = record.get("pr_number")
    if not repo or number is None:
        raise ValueError("El registro debe incluir target_repo y pr_number")
    prefix = f"pulls/{number}"
    pr = gh_json(["api", f"repos/{repo}/{prefix}"])
    if not isinstance(pr, dict):
        raise GitHubCLIError(f"No se pudo obtener {repo}#{number}")

    result: dict[str, Any] = {
        "pr": {
            "number": pr.get("number", number),
            "id": pr.get("id"),
            "url": pr.get("html_url") or record.get("pr_url"),
            "repository": repo,
            "state": pr.get("state"),
            "title": pr.get("title"),
            "body": pr.get("body"),
            "author": (pr.get("user") or {}).get("login"),
            "created_at": pr.get("created_at"),
            "updated_at": pr.get("updated_at"),
            "closed_at": pr.get("closed_at"),
            "merged_at": pr.get("merged_at"),
            "base_branch": (pr.get("base") or {}).get("ref"),
            "head_branch": (pr.get("head") or {}).get("ref"),
            "head_sha": (pr.get("head") or {}).get("sha"),
        },
        "origin": {
            "workflow_id": record.get("workflow_id"),
            "origin_repo": record.get("origin_repo"),
            "run_id": record.get("run_id"),
            "run_url": record.get("run_url"),
            "run_created_at": record.get("run_created_at"),
        },
        "comments": [],
        "reviews": [],
        "review_comments": [],
        "ci": {},
        "collection_errors": [],
    }

    # Include the originating Actions run details when it is still accessible.
    run_id = record.get("run_id")
    origin_repo = record.get("origin_repo") or repo
    if run_id:
        try:
            run = gh_json(["api", f"repos/{origin_repo}/actions/runs/{run_id}"])
            if isinstance(run, dict):
                result["origin"]["run"] = {
                    key: run.get(key)
                    for key in ("id", "name", "display_title", "event", "status", "conclusion", "created_at", "updated_at", "html_url", "head_branch", "head_sha")
                    if key in run
                }
        except GitHubCLIError as error:
            result["collection_errors"].append({"source": "origin_run", "error": str(error)})

    requests = {
        "comments": f"issues/{number}/comments?per_page=100",
        "reviews": f"pulls/{number}/reviews?per_page=100",
        "review_comments": f"pulls/{number}/comments?per_page=100",
    }
    for key, endpoint in requests.items():
        try:
            result[key] = api(repo, endpoint)
        except GitHubCLIError as error:
            result["collection_errors"].append({"source": key, "error": str(error)})

    sha = result["pr"].get("head_sha")
    if sha:
        ci_endpoints = {
            "check_runs": f"commits/{sha}/check-runs?per_page=100",
            "combined_status": f"commits/{sha}/status?per_page=100",
        }
        for key, endpoint in ci_endpoints.items():
            try:
                result["ci"][key] = gh_json(["api", f"repos/{repo}/{endpoint}"])
            except GitHubCLIError as error:
                result["collection_errors"].append({"source": f"ci.{key}", "error": str(error)})
    else:
        result["collection_errors"].append({"source": "ci", "error": "El PR no tiene head SHA disponible"})

    return result


def load_records(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"Se esperaba una lista JSON en {path}")
    if any(not isinstance(item, dict) for item in data):
        raise ValueError(f"Todos los registros de {path} deben ser objetos JSON")
    return data


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help=f"JSON de entrada (predeterminado: {DEFAULT_INPUT})")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help=f"JSON de salida (predeterminado: {DEFAULT_OUTPUT})")
    parser.add_argument("--no-resume", action="store_true", help="No reutilizar evidencias existentes en el archivo de salida")
    parser.add_argument("--delay", type=float, default=0.2, help="Pausa entre PRs en segundos (predeterminado: 0.2)")
    args = parser.parse_args()

    try:
        records = load_records(args.input)
    except (OSError, json.JSONDecodeError, ValueError) as error:
        parser.error(str(error))

    evidence: dict[str, dict[str, Any]] = {}
    if not args.no_resume and args.output.exists():
        try:
            previous = json.loads(args.output.read_text(encoding="utf-8"))
            for item in previous.get("pull_requests", []):
                key = f"{item['pr']['repository']}#{item['pr']['number']}"
                evidence[key] = item
        except (OSError, json.JSONDecodeError, KeyError, TypeError):
            print(f"Aviso: no se pudo reutilizar {args.output}; se recopilará desde cero", file=sys.stderr)

    total = len(records)
    for index, record in enumerate(records, start=1):
        key = f"{record.get('target_repo')}#{record.get('pr_number')}"
        if key in evidence:
            print(f"[{index}/{total}] reutilizado {key}")
            continue
        try:
            evidence[key] = fetch_pr_evidence(record)
            status = "recopilado"
        except (GitHubCLIError, ValueError) as error:
            evidence[key] = {
                "pr": {"number": record.get("pr_number"), "url": record.get("pr_url"), "repository": record.get("target_repo")},
                "origin": {"workflow_id": record.get("workflow_id"), "origin_repo": record.get("origin_repo"), "run_id": record.get("run_id"), "run_url": record.get("run_url")},
                "collection_errors": [{"source": "pull_request", "error": str(error)}],
            }
            status = f"error: {error}"
        print(f"[{index}/{total}] {key}: {status}")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps({"pull_requests": list(evidence.values())}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        if args.delay > 0 and index < total:
            time.sleep(args.delay)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({"pull_requests": list(evidence.values())}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Evidencia guardada en {args.output} ({len(evidence)} PRs)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
