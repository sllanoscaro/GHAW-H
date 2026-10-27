"""Collect qualitative evidence for closed, unmerged pull requests.

Requires GitHub CLI (``gh``) authenticated for the relevant repositories.
By default reads ``ICC760/output/unmerged_prs.json`` and writes
``ICC760/output/pr_evidence.json``. Supports resuming from the output file.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
DEFAULT_INPUT = PROJECT_DIR / "output" / "unmerged_prs.json"
DEFAULT_OUTPUT = PROJECT_DIR / "output" / "pr_evidence.json"
LINKED_ISSUES_VERSION = 1
ISSUE_URL = re.compile(r"https://github\.com/([\w.-]+/[\w.-]+)/issues/(\d+)\b", re.IGNORECASE)
ISSUE_REFERENCE = re.compile(
    r"https://github\.com/(?P<url_repo>[\w.-]+/[\w.-]+)/issues/(?P<url_number>\d+)\b"
    r"|(?<![\w/])(?P<repo>[\w.-]+/[\w.-]+)\\?#(?P<number>\d+)\b"
    r"|(?<![\w/#])#(?P<local_number>\d+)\b",
    re.IGNORECASE,
)


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


def collect_linked_issues(evidence: dict[str, Any]) -> None:
    """Enrich evidence with direct references, never infer a cause of closure.

    Existing PR evidence and previously fetched issue content survive retries.
    References are not traversed recursively.
    """
    pr = evidence["pr"]
    repo, number = pr["repository"], pr["number"]
    collected_at = datetime.now(timezone.utc).isoformat()
    candidates: dict[tuple[str, int], list[dict[str, Any]]] = {}
    errors: list[dict[str, Any]] = []

    def add(repository: str, issue_number: int, relation: dict[str, Any]) -> None:
        key = (repository.casefold(), issue_number)
        if key == (repo.casefold(), number):
            return
        relations = candidates.setdefault(key, [])
        if relation not in relations:
            relations.append(relation)

    def record_error(source: str, endpoint: str, error: Exception) -> None:
        errors.append({"source": source, "endpoint": endpoint, "error": str(error), "collected_at": collected_at})

    texts = [("pr.body", pr.get("url"), pr.get("body"))]
    for source in ("comments", "reviews", "review_comments"):
        texts.extend((source, item.get("html_url") or item.get("url"), item.get("body"))
                     for item in evidence.get(source, []))
    for source, source_url, body in texts:
        for match in ISSUE_REFERENCE.finditer(body or ""):
            target_repo = match.group("url_repo") or match.group("repo") or repo
            target_number = int(match.group("url_number") or match.group("number") or match.group("local_number"))
            add(target_repo, target_number, {
                "type": "text_reference", "source": source, "source_url": source_url,
                "reference": match.group(),
                "evidence": body[max(0, match.start() - 120):match.end() + 120],
            })

    timeline_endpoint = f"repos/{repo}/issues/{number}/timeline?per_page=100"
    try:
        timeline = api(repo, f"issues/{number}/timeline?per_page=100")
        for event in timeline:
            if event.get("event") != "cross-referenced":
                continue
            issue = (event.get("source") or {}).get("issue") or {}
            match = ISSUE_URL.fullmatch(issue.get("html_url") or "")
            if "pull_request" in issue or not match:
                continue
            add(match[1], int(match[2]), {
                "type": "cross-referenced", "source": "timeline",
                "source_url": f"https://api.github.com/{timeline_endpoint}",
                "issue_url": issue["html_url"], "event_id": event.get("id"),
                "created_at": event.get("created_at"),
                "evidence": {"event": "cross-referenced", "source_issue_url": issue["html_url"]},
            })
    except GitHubCLIError as error:
        record_error("linked_issues.timeline", timeline_endpoint, error)

    linked = {(item["repository"].casefold(), item["number"]): item
              for item in evidence.get("linked_issues", [])}
    for (target_repo, target_number), relations in sorted(candidates.items()):
        endpoint = f"repos/{target_repo}/issues/{target_number}"
        key = (target_repo, target_number)
        try:
            issue = gh_json(["api", endpoint])
            if not isinstance(issue, dict) or not issue.get("number"):
                raise GitHubCLIError("Respuesta de issue inválida")
            # GitHub's issues endpoint also returns pull requests.
            if "pull_request" in issue:
                continue
        except GitHubCLIError as error:
            record_error("linked_issues.issue", endpoint, error)
            errors[-1]["relations"] = relations
            continue
        item = linked.setdefault(key, {
            "repository": target_repo, "number": target_number,
            "url": issue.get("html_url") or f"https://github.com/{target_repo}/issues/{target_number}",
            "relations": [], "content": {}, "comments": [],
        })
        for relation in relations:
            if relation not in item["relations"]:
                item["relations"].append(relation)
        item["content"] = {field: issue.get(field) for field in
                           ("title", "body", "state", "created_at", "updated_at", "closed_at")}
        item["content"]["author"] = (issue.get("user") or {}).get("login")
        item["collected_at"] = collected_at
        comments_endpoint = f"issues/{target_number}/comments?per_page=100"
        try:
            item["comments"] = api(target_repo, comments_endpoint)
        except GitHubCLIError as error:
            record_error("linked_issues.comments", f"repos/{target_repo}/{comments_endpoint}", error)

    evidence["linked_issues"] = [linked[key] for key in sorted(linked)]
    evidence.setdefault("collection_errors", []).extend(errors)
    evidence["linked_issues_collection"] = {
        "version": LINKED_ISSUES_VERSION,
        "status": "partial" if errors else "complete",
        "collected_at": collected_at,
        "limitations": [
            "Sólo referencias textuales directas y eventos cross-referenced visibles; no es una búsqueda exhaustiva.",
            "Una relación o diagnóstico técnico no confirma la causa de cierre; requiere interpretación manual.",
        ],
    }
    if not linked:
        evidence["linked_issues_collection"]["limitations"].append(
            "No se recuperaron issues verificadas automáticamente; conservar la consulta manual."
        )


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

    collect_linked_issues(result)
    return result


def load_records(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"Se esperaba una lista JSON en {path}")
    if any(not isinstance(item, dict) for item in data):
        raise ValueError(f"Todos los registros de {path} deben ser objetos JSON")
    return data


def save_evidence(path: Path, evidence: dict[str, dict[str, Any]]) -> None:
    """Replace the checkpoint atomically so interruption cannot truncate it."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps({"pull_requests": list(evidence.values())}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help=f"JSON de entrada (predeterminado: {DEFAULT_INPUT})")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help=f"JSON de salida (predeterminado: {DEFAULT_OUTPUT})")
    parser.add_argument("--no-resume", action="store_true", help="No reutilizar evidencias existentes en el archivo de salida")
    parser.add_argument("--refresh-linked-issues", action="store_true", help="Reconsultar sólo issues vinculadas, preservando la evidencia previa del PR")
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
            for item in previous["pull_requests"]:
                key = f"{item['pr']['repository']}#{item['pr']['number']}"
                evidence[key] = item
        except (OSError, json.JSONDecodeError, KeyError, TypeError, AttributeError) as error:
            parser.error(f"No se pudo reutilizar {args.output}: {error}. Revise el archivo o use --no-resume explícitamente.")

    total = len(records)
    for index, record in enumerate(records, start=1):
        key = f"{record.get('target_repo')}#{record.get('pr_number')}"
        retry_pr = any(error.get("source") == "pull_request"
                       for error in evidence.get(key, {}).get("collection_errors", []))
        if key in evidence:
            collection = evidence[key].get("linked_issues_collection", {})
            if (not args.refresh_linked_issues and not retry_pr
                    and collection.get("version") == LINKED_ISSUES_VERSION
                    and collection.get("status") == "complete"):
                print(f"[{index}/{total}] reutilizado {key}")
                continue
        try:
            if key in evidence and not retry_pr:
                collect_linked_issues(evidence[key])
                status = "contexto de issues actualizado"
            else:
                evidence[key] = fetch_pr_evidence(record)
                status = "recopilado"
        except (GitHubCLIError, ValueError) as error:
            evidence.setdefault(key, {
                "pr": {"number": record.get("pr_number"), "url": record.get("pr_url"), "repository": record.get("target_repo")},
                "origin": {"workflow_id": record.get("workflow_id"), "origin_repo": record.get("origin_repo"), "run_id": record.get("run_id"), "run_url": record.get("run_url")},
                "linked_issues": [],
                "collection_errors": [],
            })
            evidence[key].setdefault("collection_errors", []).append({"source": "pull_request", "error": str(error)})
            status = f"error: {error}"
        print(f"[{index}/{total}] {key}: {status}")
        save_evidence(args.output, evidence)
        if args.delay > 0 and index < total:
            time.sleep(args.delay)

    save_evidence(args.output, evidence)
    print(f"Evidencia guardada en {args.output} ({len(evidence)} PRs)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
