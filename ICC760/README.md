# ICC760 - Extracción y análisis de dataset

Este proyecto extrae, desde el dataset `pavtch/GHAW-H` (Hugging Face), los pares de archivos Markdown / `.lock.yml` que crean pull requests y, a partir de las ejecuciones de esos workflows, los PRs que fueron **cerrados sin ser integrados** (cerrados y no mergeados).

## Estructura del proyecto

- `main.py`: Orquesta el flujo completo.
- `scripts/`: Contiene scripts auxiliares para modularidad.
- `output/`: Resultados del análisis en formato JSON para futuras visualizaciones.

## Instrucciones de ejecución

1. Crea un entorno virtual y actívalo (puedes usar python3.14 si te aparece en el sistema):
   ```bash
   python3.14 -m venv .venv
   source .venv/bin/activate
   ```
2. Instala dependencias necesarias (pandas, pyarrow), usando la versión correcta de pip:
   ```bash
   python -m pip install pandas pyarrow
   ```
   O si tu entorno requiere, explícitamente:
   ```bash
   python3.14 -m pip install pandas pyarrow
   ```
3. Ejecuta el flujo principal:
   ```bash
   python main.py
   ```

## Flujo de datos

```
 Fuente: Hugging Face  pavtch/GHAW-H  (data/*.parquet)
            │  descarga y caché local en ICC760/.cache/  (utils.read_parquet_table)
            ▼
 ┌───────────────────────────────────────────────────────────────────────┐
 │ [1] extract_repo_info.py                                                │
 │   tabla repository  ─────────────►  output/repositories.json            │
 │                                     262 × {repo_full_name, url}         │
 └───────────────────────────────────────────────────────────────────────┘
            │
            ▼
 ┌───────────────────────────────────────────────────────────────────────┐
 │ [2] pair_markdown_locks.py                                              │
 │   repository ⋈ source_markdown_file_version                             │
 │                 ⋈ source_markdown_file_snapshot ⋈ lock_file_snapshot    │
 │                                                                         │
 │   filtros en orden:                                                     │
 │     1) frontmatter declara safe-outputs.create-pull-request             │
 │     2) por par (repo, md, lock) se conserva la última versión (commit)  │
 │     3) por repo se conserva el par de commit más reciente               │
 │                              │                                          │
 │                              ▼                                          │
 │   output/repo_markdown_lock_pairs.json  (118 repos, 1 par c/u)          │
 │     { "<owner/repo>": [ { markdown_file, lock_file } ] }                │
 └───────────────────────────────────────────────────────────────────────┘
            │
            ▼
 ┌───────────────────────────────────────────────────────────────────────┐
 │ [3] fetch_prs_from_artifacts.py      (GitHub API vía `gh` autenticado)  │
 │   a) runs por workflow:  gh run list --workflow <lock> --limit 100      │
 │   b) índice de artefactos safe-outputs-items por repositorio            │
 │        GET /repos/{o}/{r}/actions/artifacts?name=safe-outputs-items     │
 │   c) por run (nuevo → viejo): descarga el .zip del artefacto y parsea   │
 │        safe-output-items.jsonl → entradas create_pull_request (/pull/N) │
 │   d) estado del PR:  GET /repos/{target}/pulls/{N}                       │
 │        ¿state == closed  y  merged_at == null?  → califica              │
 │   e) sin tope: todas las runs que califiquen por workflow               │
 │                              │                                          │
 │              ┌───────────────┴───────────────┐                          │
 │              ▼                               ▼                          │
 │   output/selected_runs.json          output/unmerged_prs.json           │
 │   (runs elegidos + sus PRs)         (PRs cerrados sin merge)            │
 │                                                                         │
 │   cachés reanudables: output/_runs_raw.json                             │
 │                       output/_artifact_attempts.json                    │
 └───────────────────────────────────────────────────────────────────────┘
```

`main.py` ejecuta los tres scripts en orden. Cada script es idempotente y toma su entrada del archivo producido por el anterior.

## Descripción del flujo

1. Se extrae el nombre y la URL de todos los repositorios del dataset (`extract_repo_info.py`), guardando `output/repositories.json`.
2. Se emparejan los archivos markdown con los archivos `.lock.yml` asociados a cada repositorio (`pair_markdown_locks.py`), guardando `output/repo_markdown_lock_pairs.json`. El proceso aplica los siguientes filtros en orden:
   1. **Filtro por `safe-outputs: create-pull-request`**: se conservan únicamente los pares cuyo archivo Markdown declare la sección `safe-outputs` con la clave `create-pull-request` en su frontmatter. Esto limita el alcance a workflows que crean pull requests.
   2. **Última versión por par**: para cada par `(markdown, lock)` se conserva la versión más reciente según `committed_at`.
   3. **Última modificación por repositorio**: si un repositorio aún posee más de un par, se conserva únicamente el par cuyo commit sea el más reciente.
3. Se extraen los PRs **cerrados sin merge** creados por las ejecuciones de cada workflow (`fetch_prs_from_artifacts.py`), a partir del artefacto `safe-outputs-items` de cada run. Requiere `gh` autenticado (`gh auth login`). El detalle está en la sección siguiente.

## Extracción de PRs desde artefactos (`fetch_prs_from_artifacts.py`)

Para cada workflow resultado del paso 2:

1. **Runs**: lista hasta `--max-runs-scan` (100 por defecto) ejecuciones con `gh run list --workflow <lock>.yml --limit N`. Los workflows **sin ejecuciones asociadas (0 runs) se descartan** y quedan fuera del estudio.
2. **Indexado de artefactos**: lista en bloque los artefactos `safe-outputs-items` por repositorio con
   `GET /repos/{o}/{r}/actions/artifacts?name=safe-outputs-items` (evita listar artefacto por artefacto). Si el endpoint falla, usa un listado por run como respaldo.
3. **Descarga y parseo**: descarga el `.zip` del artefacto y lee `safe-output-items.jsonl`, extrayendo las entradas `create_pull_request` con URL `/pull/N` (se descartan las de `/issues/N` producidas por `fallback-as-issue`).
4. **Estado del PR**: consulta `GET /repos/{target}/pulls/{N}` y conserva la ejecución sólo si el PR está **cerrado y no mergeado** (`state == closed` y `merged_at == null`).
5. **Selección**: por defecto conserva **todas** las ejecuciones que cumplen dentro de la ventana explorada (sin tope, `--all-runs`). Se puede acotar con `--max-runs-selected N`. Las ejecuciones sin artefacto se excluyen.

Opciones útiles:
- `--all-runs`: sin tope de selección; conserva todas las runs que califiquen (comportamiento por defecto).
- `--max-runs-selected N`: impone un tope de N runs que califican por workflow.
- `--max-runs-scan N`: cuántas ejecuciones explora por workflow (100 por defecto).
- `--reuse-runs`: reutiliza la caché de runs `output/_runs_raw.json`.
- `--reset`: ignora la caché de intentos `output/_artifact_attempts.json` y reprocesa todo desde cero.
- `--workers N`: número de hilos (por defecto 8); las llamadas a la API están limitadas globalmente para no gatillar límites secundarios.

### Salidas en `output/`

| Archivo | Contenido | Producido por |
| --- | --- | --- |
| `repositories.json` | Repositorios del dataset: nombre y URL | `extract_repo_info.py` |
| `repo_markdown_lock_pairs.json` | 1 par `markdown_file` / `lock_file` por repositorio (los que crean PR) | `pair_markdown_locks.py` |
| `selected_runs.json` | Ejecuciones seleccionadas (todas las que califican; sin tope) con sus PRs | `fetch_prs_from_artifacts.py` |
| `unmerged_prs.json` | PRs de interés (cerrados sin merge) con el run que los generó | `fetch_prs_from_artifacts.py` |
| `_runs_raw.json` | Caché de runs listados (reanudable) | `fetch_prs_from_artifacts.py` |
| `_artifact_attempts.json` | Caché de resultados por run (reanudable) | `fetch_prs_from_artifacts.py` |

Los archivos con prefijo `_` son cachés internas (excluidas por `.gitignore`).

> El proceso es **reanudable**: el progreso por run se guarda en `output/_artifact_attempts.json`; si se interrumpe, al re-ejecutar continúa donde quedó.

### Caché local

La primera ejecución descarga las tablas Parquet desde Hugging Face y las almacena en `ICC760/.cache/` para evitar depender de la red en ejecuciones posteriores. Si deseas forzar una descarga nueva, elimina esa carpeta.

Puedes modificar los scripts de `scripts/` para adaptar el análisis o el output según necesidades de visualización con librerías como matplotlib.
