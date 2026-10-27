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

El comando imprime el resumen y guarda una copia en `ICC760/output/preliminary_summary.md`. El archivo contiene los conteos, el cruce estado × evidencia, la distribución de razones y una tabla con una fila por cada PR inspeccionado, con evidencia, estado, categorías principal/secundaria y su alcance. **La tabla generada es la salida reproducible que sustenta la Tabla `qualitative` del paper**, actualmente presentada manualmente en LaTeX; cualquier edición de formato en el paper debe conservar los mismos valores y filas que esta salida.

Con los datos actuales, se distinguen:

- **10 inspeccionados**: diez PRs examinados y registrados en el CSV piloto, una fila por PR; no es el total de la extracción.
- **7 codificados y 3 pendientes**: estado del trabajo manual. `codificado` también admite clasificación contextual sin causa confirmada.
- **Calidad de evidencia entre los 10**: 3 `yes`, 4 `ambiguous` y 3 `no`. `yes` significa evidencia considerada explícita por la anotación manual; `ambiguous`, contexto o indicios insuficientes para atribuir una causa; `no`, ausencia de evidencia suficiente en las fuentes examinadas.
- **Cruce**: los 7 codificados son 3 `yes` + 4 `ambiguous`; los 3 pendientes son `no`. Por eso los 4 codificados sin evidencia suficiente no representan todos los casos sin evidencia suficiente de la muestra.
- **Denominador de razones respaldadas**: sólo los PRs `codificado` + `yes` (hoy N=3). Todos los conteos, porcentajes y etiquetas N se calculan desde el CSV. Las categorías son no excluyentes y cada PR cuenta una sola vez por categoría.

La distribución actual contiene `abandono_revisor`, `amenaza_agente`, `datos_obsoletos`, `error_parseo`, `fallo_orquestacion` y `pr_huerfano`, cada una con 1 PR (33,3 %). Las categorías de los cuatro casos `ambiguous` se conservan como contexto/hipótesis en la tabla, fuera de esa distribución. El [codebook](codebook.md) define esta convención para las columnas históricas `razon_principal` y `razon_secundaria`.

Una **causa de cierre respaldada** requiere evidencia que vincule explícitamente un fenómeno con la decisión de cierre. El resumen utiliza las anotaciones manuales existentes; no valida causalidad automáticamente. Esta corrección conserva el CSV original y no reclasifica los casos de la discrepancia B ni modifica cifras del paper: eso requiere una revisión metodológica separada.

## Evidencia de PRs e issues vinculadas (`collect_pr_evidence.py`)

Esta etapa se ejecuta por separado, después de obtener `unmerged_prs.json`, desde la raíz del repositorio. Requiere GitHub CLI (`gh`) autenticado y acceso a los repositorios:

```bash
python ICC760/scripts/collect_pr_evidence.py \
    --input ICC760/output/unmerged_prs.json \
    --output ICC760/output/pr_evidence.json
```

Recolecta automáticamente cuerpo y metadatos del PR, comentarios, reviews,
comentarios de revisión, estado de CI y datos del run de origen. La etapa
`collect_linked_issues` añade contexto de issues mediante:

1. Referencias directas en cuerpo, comentarios y reviews: URLs
   `https://github.com/owner/repo/issues/N`, `owner/repo#N` (también `\#` escapado)
   y `#N` del mismo repositorio. Se verifica cada candidata con la API de issues;
   se descartan las respuestas que son PRs (`pull_request`). En enlaces Markdown
   a issues/PRs de GitHub se usa el destino, no el número del texto de la etiqueta.
2. Eventos `cross-referenced` del timeline del PR: la issue de origen menciona
   el PR. Se admiten otros repositorios y se descartan orígenes que son PRs.

El JSON conserva los campos previos y añade a cada PR:

- `linked_issues`: lista (vacía si no hay issues verificadas) con `repository`,
  `number`, `url`, `relations`, `content`, `comments` y `collected_at`.
  Se deduplica por repositorio (sin distinguir mayúsculas) y número. Cada
  `relation` conserva `type` (`text_reference` o `cross-referenced`), `source`,
  `source_url` y `evidence` (extracto textual o datos del evento); las menciones
  guardan el texto reconocido en `reference`, y los eventos
  incluyen además `issue_url`, `event_id` cuando existe y `created_at`.
  `content` guarda título, cuerpo, estado, autor y fechas de la issue.
- `linked_issues_collection`: versión del esquema, fecha UTC, estado
  `complete`/`partial` de la última consulta y limitaciones. `complete` sólo
  indica éxito de las consultas de esta etapa, no exhaustividad metodológica.
- `collection_errors`: conserva los errores anteriores y añade fallos de
  timeline, issue o comentarios con `source`, `endpoint`, `error` y fecha UTC;
  una candidata inaccesible guarda también sus relaciones para consulta manual.

Timeline y comentarios de issues se consultan con paginación completa. Un 404,
falta de permisos o fallo de API queda registrado y permite continuar con otras
issues y PRs. Los fallos transitorios reconocidos por el cliente se reintentan.
Las candidatas no verificadas no se añaden como issues nuevas.

La extracción es **reanudable**: los JSON antiguos se enriquecen automáticamente
sin volver a descargar la evidencia del PR. Se reintentan etapas de issues
parciales y se reutilizan las completas. Para consultar otra vez todas las
relaciones, añadir `--refresh-linked-issues` al comando anterior. Se preservan
las issues recuperadas anteriormente aunque una consulta posterior falle o deje
de exponer su relación, con sus fechas de recolección y procedencias. Los errores
son históricos; el estado de la última consulta está en `linked_issues_collection`.
Cada checkpoint se reemplaza atómicamente. `--no-resume` reconstruye la salida
desde cero; un archivo de reanudación ilegible produce un error para evitar
sobrescribir evidencia silenciosamente.

### Alcance e interpretación manual

El descubrimiento es de un solo salto, sin recorrer recursivamente las issues,
sin buscar menciones en todo GitHub ni inspeccionar enlaces en logs/CI. No cubre
todos los formatos de enlace, vínculos privados o eliminados ni todas las
relaciones de la interfaz de GitHub. Los textos del PR reutilizados corresponden
a la captura original; la nueva consulta del timeline puede incluir referencias
posteriores al cierre, incluso referencias al estudio mismo. Las fechas y fuentes
permiten evaluar esa diferencia temporal durante la revisión manual. Una lista
vacía no prueba ausencia de relaciones: el JSON registra esa limitación.

Para `dotnet/runtime#134186`, GitHub expone un evento `cross-referenced` desde
`dotnet/runtime#134305`, que este procedimiento conserva junto al contenido de
la issue. Si deja de estar disponible, los errores/limitaciones quedan registrados
y sigue siendo necesaria la consulta manual documentada en el CSV.

Una mención o relación verificable demuestra **vinculación**, no causalidad.
Un diagnóstico del agente, una alerta de seguridad o un fallo de CI son
**evidencia técnica**; sólo una fuente que explique su vínculo con la decisión
puede respaldar una **explicación del cierre**. Seleccionar pasajes pertinentes,
evaluar autoría/cronología y codificar las razones sigue siendo trabajo manual.

### Pruebas reproducibles sin red

```bash
python -m unittest discover -s ICC760/tests -v
```

Las pruebas simulan GitHub (relaciones, ausencia, duplicados, otros repositorios,
paginación, errores y reanudación) y verifican conteos/denominadores del CSV,
incluido un fixture con un número distinto de casos codificados `yes`.

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
| `pr_evidence.json` | Evidencia de PRs, issues vinculadas con procedencia y errores de recolección | `collect_pr_evidence.py` |
| `preliminary_summary.md` | Conteos, cruces, distribución de razones y tabla por PR del CSV piloto | `summarize_coding.py` |
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
