Resumen de codificación: ICC760/analisis_cualitativo.csv

PRs inspeccionados (una fila por PR): 10
PRs codificados: 7
PRs pendientes: 3
Calidad de evidencia en todos los inspeccionados: yes=3, ambiguous=4, no=3
PRs codificados con evidencia explícita (yes): 3
PRs codificados sin evidencia suficiente (ambiguous/no): 4

Inspeccionado significa examinado y registrado en el CSV; codificado puede incluir clasificación contextual sin causa confirmada.

## Cruce de estado de codificación y calidad de evidencia

| Estado | yes | ambiguous | no | Total |
| --- | ---: | ---: | ---: | ---: |
| Codificado | 3 | 4 | 0 | 7 |
| Pendiente | 0 | 0 | 3 | 3 |
| Total | 3 | 4 | 3 | 10 |

## Distribución de razones respaldadas según la codificación manual

Sólo casos codificados con evidencia explícita yes. La extracción no valida automáticamente la atribución causal.
(N=3; categorías no excluyentes)

| Categoría | PRs | Porcentaje |
| --- | ---: | ---: |
| `abandono_revisor` | 1 | 33.3% |
| `amenaza_agente` | 1 | 33.3% |
| `datos_obsoletos` | 1 | 33.3% |
| `error_parseo` | 1 | 33.3% |
| `fallo_orquestacion` | 1 | 33.3% |
| `pr_huerfano` | 1 | 33.3% |

## Tabla cualitativa de los PRs seleccionados

Esta tabla se genera desde el CSV fuente y sustenta la tabla cualitativa del paper.
Las categorías con evidencia ambiguous son anotaciones contextuales o hipótesis originales, no causas confirmadas; se excluyen de los porcentajes anteriores.

| PR | Evidencia | Estado | Categoría principal | Categoría secundaria | Alcance de las categorías |
| --- | --- | --- | --- | --- | --- |
| advanced-security #108 | No | Pendiente | --- | --- | Sin causa respaldada |
| advanced-security #111 | Ambigua | Codificado | Cierre silencioso | --- | Contexto/hipótesis; causa no confirmada |
| elastic-docs-skills #129 | Ambigua | Codificado | Cierre silencioso | Error de red del agente | Contexto/hipótesis; causa no confirmada |
| elasticstack #4603 | Ambigua | Codificado | Cierre silencioso | Error de red del agente | Contexto/hipótesis; causa no confirmada |
| FSharp.Formatting #1332 | No | Pendiente | --- | --- | Sin causa respaldada |
| copilot-sdk #2001 | Ambigua | Codificado | Archivo protegido | Abandono del revisor | Contexto/hipótesis; causa no confirmada |
| gpui-unofficial #306 | No | Pendiente | --- | --- | Sin causa respaldada |
| msbuild #14646 | Sí | Codificado | Abandono del revisor | Datos obsoletos | Respaldadas según codificación manual |
| elasticstack #4386 | Sí | Codificado | Amenaza del agente | Error de parseo | Respaldadas según codificación manual |
| runtime #134186 | Sí | Codificado | Fallo de orquestación | PR huérfano | Respaldadas según codificación manual |
