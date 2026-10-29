# ICC760 — Paquete de réplica del análisis final

Estudio de las razones documentadas de no integración de PRs generados por
GitHub Agentic Workflows. La pregunta, reglas de evidencia y seis categorías
están definidas en el [codebook](codebook.md).

## Reproducir las tablas del artículo sin red

Desde la raíz de este repositorio, con Python 3.11 o posterior:

```bash
python3 ICC760/scripts/summarize_coding.py \
  --input ICC760/analisis_cualitativo.csv \
  --output ICC760/output/final_summary.md
python3 -m unittest discover -s ICC760/tests -v
```

Estos comandos usan sólo la biblioteca estándar: no requieren `gh`, credenciales,
instalación de dependencias ni volver a consultar GitHub. El CSV final del
proyecto está versionado aquí como `analisis_cualitativo.csv`.

La salida esperada es: 82 PRs únicos de 17 repositorios; 9 con evidencia
explícita (11,0 %), 37 ambigua (45,1 %) y 36 ausente (43,9 %).
Entre los nueve explícitos: cambio no necesario (3), datos obsoletos (2),
continuación manual (1), expiración automática (1), implementación insuficiente
(1) y destino incorrecto (1). Hay 15 nombres de workflow y 17 pares
repositorio–workflow. De los 37 ambiguos, 25 tienen `ci_fallido`.

El resumen valida identificadores, duplicados y las reglas de codificación.
Cuenta una razón principal únicamente por PR explícito; las señales contextuales
no se cuentan como razones. La interpretación y clasificación son manuales:
el programa no prueba causalidad ni genera el CSV desde la evidencia.

## Materiales conservados

| Archivo en `ICC760/` | Contenido |
| --- | --- |
| `analisis_cualitativo.csv` | Codificación final de los 82 PRs |
| `codebook.md` | Definiciones y criterios de inclusión/exclusión |
| `output/repositories.json` | 262 repositorios del dataset |
| `output/repo_markdown_lock_pairs.json` | Un par Markdown/lock por cada uno de 118 repositorios seleccionados |
| `output/selected_runs.json` | 81 ejecuciones seleccionadas; una ejecución puede crear más de un PR |
| `output/unmerged_prs.json` | 82 PRs únicos cerrados y no integrados, con su ejecución de origen |
| `output/pr_evidence.json` | Cuerpo, comentarios, revisiones, CI e issues vinculadas, con procedencia y errores |
| `output/final_summary.md` | Tablas y enlaces de los nueve casos explícitos, generados desde el CSV |
| `output/preliminary_summary.md` | Salida histórica del piloto de Etapa 2; no representa los resultados finales |

Los JSON son evidencia del estudio, no archivos temporales. La consulta de issues
vinculadas del 27 de octubre de 2026 registra 64 casos `complete` y 18 `partial`;
los errores están en `collection_errors`. `complete` indica éxito de esa consulta,
no exhaustividad de la evidencia. Los nueve localizadores explícitos del CSV
están presentes en los comentarios guardados.

## Ejecutar una nueva extracción

Una extracción nueva consulta servicios cambiantes y **no garantiza recuperar
la muestra histórica**: GitHub puede eliminar o expirar artefactos, modificar
comentarios y exponer otras ejecuciones recientes. Además, `scripts/utils.py`
descarga `pavtch/GHAW-H` desde la revisión mutable `main`; la extracción conservada
no registra el commit de Hugging Face ni su fecha inicial de descarga. La versión
0.1.2 declarada en el artículo no puede comprobarse sólo con esas salidas.
Para reproducir exactamente los recuentos, usar los archivos conservados arriba.

Ejecutar la nueva minería en **otra copia del repositorio**, porque sobrescribe
las salidas de `ICC760/output/`. Requiere Python 3.12, conexión a Hugging Face y
GitHub, y GitHub CLI autenticado con acceso a las ejecuciones y sus artefactos:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r ICC760/requirements.txt
gh auth status
```

Si no existe una sesión de GitHub CLI, configurar primero `gh auth login`.
Las dependencias de `ICC760/requirements.txt` son para la minería; el archivo
`requirements.txt` de la raíz incluye además herramientas de los notebooks de GHAW-H.

Ejecutar desde la raíz, en este orden:

```bash
python ICC760/scripts/extract_repo_info.py
python ICC760/scripts/pair_markdown_locks.py
python ICC760/scripts/fetch_prs_from_artifacts.py --max-runs-scan 100 --all-runs
python ICC760/scripts/collect_pr_evidence.py \
  --input ICC760/output/unmerged_prs.json \
  --output ICC760/output/pr_evidence.json --no-resume
```

1. Se descargan las tablas Parquet y se enumeran los repositorios.
2. Se seleccionan configuraciones con `safe-outputs.create-pull-request`,
   conservando el par Markdown/lock más reciente entre los elegibles por repositorio.
3. Se examinan hasta 100 ejecuciones recientes por workflow; se leen entradas
   `create_pull_request` de `safe-output-items.jsonl` dentro de `safe-outputs-items`.
   Se excluyen URLs de issues y se retienen PRs `closed` con `merged_at=null`.
   Se deduplican por repositorio de destino y número de PR.
4. Se recopila evidencia y contexto de issues vinculadas. Revisar los errores
   de recolección antes de interpretar ausencias.
5. Se revisa y codifica manualmente cada PR siguiendo el codebook. Sólo después
   se ejecuta `summarize_coding.py` para calcular las tablas de la nueva muestra.

`python ICC760/main.py` ejecuta únicamente los tres primeros pasos y reutiliza
la caché de runs. No recopila evidencia ni realiza el análisis cualitativo.

### Reanudación y límites

- `fetch_prs_from_artifacts.py --reuse-runs` reutiliza `output/_runs_raw.json`;
  `--reset` ignora `output/_artifact_attempts.json`. Para renovar ambos, usar
  `--reset` sin `--reuse-runs`. `--max-runs-selected N` limita la selección;
  no combinarlo con `--all-runs`, que tiene prioridad.
- `collect_pr_evidence.py` reanuda por defecto, conserva evidencia previa y
  reintenta consultas de issues parciales. `--refresh-linked-issues` actualiza
  esas relaciones; `--no-resume` reconstruye la salida y se reserva a la nueva copia.
- El descubrimiento de issues es de un salto. Una relación o fallo de CI no
  demuestra el motivo del cierre; deben revisarse fuente, autoría y cronología.
- El extractor de artefactos puede convertir fallos de API/descarga en resultados
  vacíos y guardarlos en caché. Un comando terminado sin error no acredita una
  extracción completa. Esta limitación del recolector afecta nuevas muestras;
  las pruebas del resumen verifican los archivos conservados.

## Temporales y versión archivada

`.cache/`, `output/_*.json`, `.venv/`, `__pycache__/` y `*.py[cod]` están excluidos
por las reglas de Git. `output/*.tmp` son checkpoints transitorios de escritura.
No se deben eliminar los JSON de evidencia ni las pruebas como si fueran temporales.

El depósito [Zenodo 10.5281/zenodo.23178074](https://doi.org/10.5281/zenodo.23178074)
está identificado en este repositorio como **Etapa 2**, tag `icc760-stage-2`,
commit `5209bb1471d6bee13c5ea349b9def8266f897b2d`. No se presenta como una
publicación del análisis final. Antes de entregar, archivar una nueva versión
con los materiales finales y actualizar en el artículo el DOI de esa versión.
