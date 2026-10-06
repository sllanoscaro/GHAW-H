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

## Reproducción de los resultados preliminares

Para reproducir los resultados preliminares de esta Etapa 2 no hace falta volver a ejecutar toda la minería de datos ni consultar nuevamente GitHub. El punto de partida son los datos de extracción conservados en `ICC760/output/` —incluidos `unmerged_prs.json`, `pr_evidence.json` y los archivos intermedios asociados— y la codificación manual registrada en `ICC760/analisis_cualitativo.csv`. El resumen de categorías se calcula a partir del CSV; los archivos de `output/` conservan los resultados previos de minería y la evidencia recopilada.

Desde la raíz del repositorio, ejecutar:

```bash
python ICC760/scripts/summarize_coding.py \
    --input ICC760/analisis_cualitativo.csv \
    --output ICC760/output/preliminary_summary.md
```

El comando imprime el resumen y guarda una copia en `ICC760/output/preliminary_summary.md`. El archivo contiene tanto la distribución de razones como la tabla completa de los 10 PRs, con evidencia, estado y razones principal/secundaria. **La tabla generada es la salida reproducible que sustenta la Tabla `qualitative` del paper**, actualmente presentada manualmente en LaTeX; cualquier edición de formato en el paper debe conservar los mismos valores y filas que esta salida.

Con los datos actuales, el resultado esperado es: 10 PRs en el CSV, 7 revisados/codificados, 3 con evidencia explícita (`yes`) y 4 sin evidencia suficiente (`no` o `ambiguous`). La distribución de razones incluye sólo esos 3 casos con evidencia `yes` (las categorías son no excluyentes): `abandono_revisor`, `amenaza_agente`, `datos_obsoletos`, `error_parseo`, `fallo_orquestacion` y `pr_huerfano`, cada una con 1 PR (33,3 %). La tabla enumera los diez identificadores desde `advanced-security #108` hasta `runtime #134186`, con etiquetas de evidencia y categorías traducidas para coincidir con la tabla del paper. Esta reproducción resume los datos preliminares conservados; no vuelve a generar los datos de minería.

## Secuencia de procesamiento

`main.py` ejecuta tres pasos secuenciales: `extract_repo_info.py` obtiene de GHAW-H los repositorios y escribe `output/repositories.json`; `pair_markdown_locks.py` filtra los workflows cuya configuración declara `safe-outputs.create-pull-request`, y conserva el par Markdown/lock más reciente por repositorio en `output/repo_markdown_lock_pairs.json`; `fetch_prs_from_artifacts.py` consulta ejecuciones y artefactos de GitHub, y escribe `output/selected_runs.json` y `output/unmerged_prs.json` con las ejecuciones y PRs cerrados sin merge. Las tablas Parquet se descargan desde Hugging Face y se almacenan en `ICC760/.cache/`; los resultados de la API y el progreso de extracción se almacenan en `output/`. Cada paso usa los resultados del paso anterior y puede reanudarse mediante las cachés descritas más abajo.

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

## Replication package — ICC760 Stage 2

GitHub version: `icc760-stage-2`
Commit: `5209bb1471d6bee13c5ea349b9def8266f897b2d`
Zenodo DOI: `https://doi.org/10.5281/zenodo.23178074`
