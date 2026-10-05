"""Extract "closed without merge" pull requests created by GH-AW workflow runs.

Variant A (artifact-based):
1. For each studied workflow (one MD/lock pair per repository) list its runs.
2. Locate the run's ``safe-outputs-items`` artifact (bulk listing per repo, with a
   per-run fallback) and download its zip.
3. Parse ``safe-output-items.jsonl`` for ``create_pull_request`` entries and keep
   only real PR URLs (``/pull/N``; ``fallback-as-issue`` produces ``/issues/N``).
4. Resolve each PR state and keep runs whose PR is ``closed`` and ``merged_at``
   is null. Runs without the artifact are excluded.
5. Per workflow, keep every qualifying run within the scanned window (``--all-runs``,
   the default). A cap can be imposed with ``--max-runs-selected N``.

The process is resumable: per-run results are cached in
``output/_artifact_attempts.json``.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import re
import subprocess
import sys
import tempfile
import threading
import time
import zipfile
from pathlib import Path

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / "output"
PAIRS_FILE = OUTPUT_DIR / "repo_markdown_lock_pairs.json"

RUNS_CACHE = OUTPUT_DIR / "_runs_raw.json"
ATTEMPTS_CACHE = OUTPUT_DIR / "_artifact_attempts.json"

SAFE_OUTPUTS_ARTIFACT = "safe-outputs-items"
ARTIFACT_MEMBER = "safe-output-items.jsonl"

DEFAULT_MAX_RUNS_SELECTED = None  # None = sin tope
DEFAULT_MAX_RUNS_SCAN = 100
DEFAULT_WORKERS = 8
CORE_MIN_INTERVAL = 0.75  # ~4800 core REST req/h, stays under secondary limits

_core_lock = threading.Lock()
_core_last_call = 0.0


def throttle_core() -> None:
    global _core_last_call
    with _core_lock:
        wait = CORE_MIN_INTERVAL - (time.time() - _core_last_call)
        if wait > 0:
            time.sleep(wait)
        _core_last_call = time.time()


def run_gh(args: list[str], timeout: int = 120) -> subprocess.CompletedProcess:
    throttle_core()
    return subprocess.run(
        ["gh", *args], capture_output=True, text=True, timeout=timeout, errors="replace"
    )


def gh_json(args: list[str], retries: int = 4, timeout: int = 120):
    for attempt in range(retries):
        try:
            proc = run_gh(args, timeout=timeout)
        except subprocess.TimeoutExpired:
            time.sleep(2 * (attempt + 1))
            continue
        if proc.returncode == 0 and proc.stdout.strip():
            try:
                return json.loads(proc.stdout)
            except json.JSONDecodeError:
                return None
        stderr = (proc.stderr or "").lower()
        if "rate limit" in stderr or "secondary" in stderr or "abuse" in stderr:
            time.sleep(5 * (attempt + 1))
            continue
        return None
    return None


def load_workflows() -> list[dict]:
    pairs = json.loads(PAIRS_FILE.read_text())
    workflows: list[dict] = []
    for repo, entries in pairs.items():
        for entry in entries:
            lock_path = entry["lock_file"]
            lock_base = os.path.basename(lock_path)
            workflow_id = lock_base[: -len(".lock.yml")]
            workflows.append(
                {
                    "key": f"{repo}::{workflow_id}",
                    "origin_repo": repo,
                    "workflow_id": workflow_id,
                    "lock_file": lock_path,
                    "lock_base": lock_base,
                }
            )
    return workflows


def list_runs(workflow: dict, max_runs_scan: int) -> list[dict]:
    data = gh_json(
        [
            "run",
            "list",
            "-R",
            workflow["origin_repo"],
            "--workflow",
            workflow["lock_base"],
            "--limit",
            str(max_runs_scan),
            "--json",
            "databaseId,createdAt,conclusion,event,url,headBranch,displayTitle",
        ]
    )
    if not data:
        return []
    for run in data:
        run["origin_repo"] = workflow["origin_repo"]
        run["workflow_id"] = workflow["workflow_id"]
        run["lock_file"] = workflow["lock_file"]
    return data


def fetch_all_runs(workflows: list[dict], max_runs_scan: int, workers: int) -> list[dict]:
    runs: list[dict] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(list_runs, wf, max_runs_scan): wf for wf in workflows}
        for future in concurrent.futures.as_completed(futures):
            wf = futures[future]
            try:
                result = future.result()
            except Exception as error:  # noqa: BLE001
                print(f"  ! runs {wf['origin_repo']}/{wf['workflow_id']}: {error}")
                result = []
            print(f"  runs {wf['origin_repo']}/{wf['workflow_id']}: {len(result)}")
            runs.extend(result)
    return runs


def build_artifact_index(origin: str) -> dict[int, int] | None:
    """Bulk-list safe-outputs-items artifacts for a repo -> {run_id: artifact_id}.

    Returns None if the bulk endpoint fails, so the caller can fall back to a
    per-run lookup.
    """
    args = [
        "api",
        "--paginate",
        "--slurp",
        "-X",
        "GET",
        f"repos/{origin}/actions/artifacts?name={SAFE_OUTPUTS_ARTIFACT}&per_page=100",
    ]
    proc = run_gh(args, timeout=180)
    if proc.returncode != 0 or not proc.stdout.strip():
        return None
    try:
        pages = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return None
    index: dict[int, int] = {}
    for page in pages:
        for artifact in page.get("artifacts", []):
            if artifact.get("expired"):
                continue
            run_id = (artifact.get("workflow_run") or {}).get("id")
            if run_id is not None:
                index[run_id] = artifact["id"]
    return index


def find_artifact_per_run(origin: str, run_id: int) -> int | None:
    data = gh_json(["api", f"repos/{origin}/actions/runs/{run_id}/artifacts"])
    if not data:
        return None
    for artifact in data.get("artifacts", []):
        if artifact.get("name") == SAFE_OUTPUTS_ARTIFACT and not artifact.get("expired"):
            return artifact["id"]
    return None


PR_URL_RE = re.compile(r"https://github\.com/[^/]+/[^/]+/pull/\d+")


def artifact_pr_urls(origin: str, artifact_id: int) -> list[str]:
    handle = tempfile.NamedTemporaryFile(suffix=".zip", delete=False)
    handle.close()
    try:
        for attempt in range(3):
            throttle_core()
            try:
                proc = subprocess.run(
                    ["gh", "api", f"repos/{origin}/actions/artifacts/{artifact_id}/zip"],
                    stdout=open(handle.name, "wb"),
                    stderr=subprocess.PIPE,
                    timeout=120,
                )
            except subprocess.TimeoutExpired:
                time.sleep(3 * (attempt + 1))
                continue
            if proc.returncode == 0:
                try:
                    urls: list[str] = []
                    with zipfile.ZipFile(handle.name) as archive:
                        for name in archive.namelist():
                            if not name.endswith(ARTIFACT_MEMBER):
                                continue
                            for line in archive.read(name).decode("utf-8", "replace").splitlines():
                                line = line.strip()
                                if not line:
                                    continue
                                try:
                                    item = json.loads(line)
                                except json.JSONDecodeError:
                                    continue
                                if item.get("type") != "create_pull_request":
                                    continue
                                url = item.get("url") or ""
                                if PR_URL_RE.fullmatch(url):
                                    urls.append(url)
                    return urls
                except zipfile.BadZipFile:
                    pass
            stderr = (proc.stderr or b"").decode("utf-8", "replace").lower()
            if "rate limit" not in stderr and "secondary" not in stderr:
                return []
            time.sleep(5 * (attempt + 1))
        return []
    finally:
        try:
            os.unlink(handle.name)
        except OSError:
            pass


def fetch_pr(url: str) -> dict | None:
    match = re.match(r"https://github\.com/([^/]+/[^/]+)/pull/(\d+)", url)
    if not match:
        return None
    target_repo, number = match.group(1), int(match.group(2))
    data = gh_json(["api", f"repos/{target_repo}/pulls/{number}"])
    if not data:
        return None
    merged_at = data.get("merged_at")
    return {
        "target_repo": target_repo,
        "pr_number": number,
        "pr_url": data.get("html_url"),
        "pr_title": data.get("title"),
        "pr_author": (data.get("user") or {}).get("login"),
        "pr_state": data.get("state"),
        "pr_merged": merged_at is not None,
        "pr_merged_at": merged_at,
        "pr_created_at": data.get("created_at"),
        "pr_closed_at": data.get("closed_at"),
    }


def process_run(run: dict, index: dict | None, pr_cache: dict, pr_lock: threading.Lock) -> dict:
    origin = run["origin_repo"]
    run_id = run["databaseId"]

    if index is None:
        artifact_id = find_artifact_per_run(origin, run_id)
    else:
        artifact_id = index.get(run_id)
    if not artifact_id:
        return {"qualifies": False, "prs": []}

    urls = artifact_pr_urls(origin, artifact_id)
    prs: list[dict] = []
    for url in urls:
        with pr_lock:
            pr = pr_cache.get(url)
        if pr is None:
            pr = fetch_pr(url)
            with pr_lock:
                pr_cache[url] = pr
        if pr:
            prs.append(pr)
    qualifies = any(pr["pr_state"] == "closed" and not pr["pr_merged"] for pr in prs)
    return {"qualifies": qualifies, "prs": prs}


def process_workflow(
    workflow: dict,
    runs: list[dict],
    artifact_index: dict[str, dict | None],
    attempts: dict,
    attempts_lock: threading.Lock,
    pr_cache: dict,
    pr_lock: threading.Lock,
    state: dict,
    max_runs_selected: int | None,
) -> None:
    index = artifact_index.get(workflow["origin_repo"])
    qualifying = 0
    new_attempts = 0
    for run in runs:
        run_id = run["databaseId"]
        with attempts_lock:
            result = attempts.get(run_id)
        if result is None:
            result = process_run(run, index, pr_cache, pr_lock)
            with attempts_lock:
                attempts[run_id] = result
                state["done"] = state.get("done", 0) + 1
                new_attempts += 1
                if new_attempts % 25 == 0:
                    ATTEMPTS_CACHE.write_text(json.dumps(attempts, ensure_ascii=False))
                    print(f"  procesados {state['done']} runs (checkpoint guardado)")
        if result["qualifies"]:
            qualifying += 1
            if max_runs_selected and qualifying >= max_runs_selected:
                break


def write_outputs(workflows: list[dict], runs_by_wf: dict, attempts: dict, max_runs_selected: int | None) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    selected: list[dict] = []
    unmerged: dict[tuple[str, int], dict] = {}

    for workflow in workflows:
        runs = runs_by_wf.get(workflow["key"], [])
        qualifying = 0
        for run in runs:
            result = attempts.get(run["databaseId"])
            if not result or not result["qualifies"]:
                continue
            prs = [p for p in result["prs"] if p["pr_state"] == "closed" and not p["pr_merged"]]
            record = {
                "origin_repo": workflow["origin_repo"],
                "workflow_id": workflow["workflow_id"],
                "lock_file": workflow["lock_file"],
                "run_id": run["databaseId"],
                "run_url": run.get("url"),
                "run_created_at": run.get("createdAt"),
                "run_conclusion": run.get("conclusion"),
                "run_event": run.get("event"),
                "run_head_branch": run.get("headBranch"),
                "display_title": run.get("displayTitle"),
                "pr_count": len(prs),
                "unmerged_pr_count": len(prs),
                "pr_numbers": " ".join(str(p["pr_number"]) for p in prs),
                "prs": prs,
            }
            selected.append(record)
            for pr in prs:
                key = (pr["target_repo"], pr["pr_number"])
                unmerged.setdefault(
                    key,
                    {
                        "origin_repo": workflow["origin_repo"],
                        "workflow_id": workflow["workflow_id"],
                        "run_id": run["databaseId"],
                        "run_url": run.get("url"),
                        "run_created_at": run.get("createdAt"),
                        **pr,
                    },
                )
            qualifying += 1
            if max_runs_selected and qualifying >= max_runs_selected:
                break

    unmerged_list = sorted(
        unmerged.values(), key=lambda p: (p["origin_repo"], p["workflow_id"], p["run_id"])
    )

    (OUTPUT_DIR / "selected_runs.json").write_text(
        json.dumps(selected, indent=2, ensure_ascii=False)
    )
    (OUTPUT_DIR / "unmerged_prs.json").write_text(
        json.dumps(unmerged_list, indent=2, ensure_ascii=False)
    )

    print(
        f"  -> {len(selected)} runs seleccionados, {len(unmerged_list)} PRs cerrados sin merge"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--max-runs-selected",
        type=int,
        default=DEFAULT_MAX_RUNS_SELECTED,
        help="máximo de runs que califican por workflow (por defecto: sin tope)",
    )
    parser.add_argument(
        "--all-runs",
        action="store_true",
        help="sin tope: conserva todas las runs que califiquen (tiene prioridad)",
    )
    parser.add_argument("--max-runs-scan", type=int, default=DEFAULT_MAX_RUNS_SCAN)
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS)
    parser.add_argument("--reuse-runs", action="store_true")
    parser.add_argument("--reset", action="store_true", help="ignora la caché de intentos")
    args = parser.parse_args()

    max_runs_selected = None if args.all_runs else args.max_runs_selected
    if max_runs_selected is None:
        print("Cuota de selección: sin tope (todas las runs que califiquen)")
    else:
        print(f"Cuota de selección: {max_runs_selected} runs por workflow")

    workflows = load_workflows()
    print(f"Workflows a procesar: {len(workflows)}")

    if args.reuse_runs and RUNS_CACHE.exists():
        runs = json.loads(RUNS_CACHE.read_text())
        print(f"Paso 1/4: runs reutilizados ({len(runs)})")
    else:
        print("Paso 1/4: listando runs...")
        runs = fetch_all_runs(workflows, args.max_runs_scan, args.workers)
        RUNS_CACHE.write_text(json.dumps(runs, ensure_ascii=False))
    print(f"  total runs: {len(runs)}")

    runs_by_wf: dict[str, list[dict]] = {}
    for run in runs:
        key = f"{run['origin_repo']}::{run['workflow_id']}"
        runs_by_wf.setdefault(key, []).append(run)
    for key in runs_by_wf:
        runs_by_wf[key].sort(key=lambda r: r.get("createdAt") or "", reverse=True)

    # Descartar workflows sin ejecuciones asociadas (runs == 0)
    workflows_con_runs = [wf for wf in workflows if runs_by_wf.get(wf["key"])]
    descartados = len(workflows) - len(workflows_con_runs)
    if descartados:
        print(f"  workflows sin ejecuciones descartados: {descartados}")
    workflows = workflows_con_runs
    print(f"  workflows en estudio: {len(workflows)}")

    print("Paso 2/4: indexando artefactos safe-outputs-items por repositorio...")
    origins = sorted({wf["origin_repo"] for wf in workflows})
    artifact_index: dict[str, dict | None] = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(build_artifact_index, origin): origin for origin in origins}
        for future in concurrent.futures.as_completed(futures):
            origin = futures[future]
            try:
                artifact_index[origin] = future.result()
            except Exception:  # noqa: BLE001
                artifact_index[origin] = None
    fallback = sum(1 for v in artifact_index.values() if v is None)
    print(f"  repos indexados: {len(artifact_index)} (con fallback por run: {fallback})")

    attempts: dict = {}
    if not args.reset and ATTEMPTS_CACHE.exists():
        # Las claves JSON son strings; normalizamos a int para que coincidan con databaseId.
        attempts = {
            int(run_id): value
            for run_id, value in json.loads(ATTEMPTS_CACHE.read_text()).items()
        }
        print(f"Paso 3/4: intentos previos reutilizados ({len(attempts)})")
    else:
        print("Paso 3/4: procesando runs y descargando artefactos...")

    attempts_lock = threading.Lock()
    pr_lock = threading.Lock()
    pr_cache: dict = {}
    state: dict = {"done": 0}

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [
            pool.submit(
                process_workflow,
                wf,
                runs_by_wf.get(wf["key"], []),
                artifact_index,
                attempts,
                attempts_lock,
                pr_cache,
                pr_lock,
                state,
                max_runs_selected,
            )
            for wf in workflows
        ]
        for future in concurrent.futures.as_completed(futures):
            try:
                future.result()
            except Exception as error:  # noqa: BLE001
                print(f"  ! workflow: {error}")

    ATTEMPTS_CACHE.write_text(json.dumps(attempts, ensure_ascii=False))

    print("Paso 4/4: escribiendo salidas...")
    write_outputs(workflows, runs_by_wf, attempts, max_runs_selected)


if __name__ == "__main__":
    main()
