# Codebook: razones documentadas de no integración de PRs de GHAW

**Primera versión:** 0.1 (05-10-2026)
**Segunda versión:** 0.2 (23-10-2026)
**Versión actual:** 0.3 (27-10-2026).
**Datos:** `unmerged_prs.json`, `pr_evidence.json` (82 PRs).

## 1. Objetivo y alcance

Responder la pregunta: **¿Cuáles son las principales razones documentadas que explican la no integración de PRs generados por GitHub Agentic Workflows (GHAW)?** La unidad de análisis es un PR creado por un workflow GHAW y posteriormente cerrado sin integración.

Se aplica *card sorting* abierto e iterativo, no una lista cerrada de fallos prefijados. Cada PR constituye una tarjeta compuesta por su identificación, fragmentos de evidencia verificables y contexto. Los casos se agrupan por explicaciones conceptualmente equivalentes sólo cuando hay un vínculo documentado con el cierre.

## 2. Reglas de codificación: nivel de evidencia

| Valor en `evidencia_disponible` | Criterio operacional                                                                                                                                                                                                  | `razon_principal`                        | `senales_contextuales`                                              |
| ------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------- | ------------------------------------------------------------------- |
| `explícita`                     | Un comentario, revisión, cuerpo del PR o aviso de automatización **vincula directamente** una condición o decisión con el cierre/no integración (p. ej. «not needed», «cierro porque ...», «cerrado por expiración»). | Obligatoria y exactamente una categoría. | Opcionales, nunca aportan una segunda ocurrencia de la razón.       |
| `ambigua`                       | Hay uno o más indicios técnicos o de discusión que podrían ser relevantes, **sin que se documente que originaron el cierre**.                                                                                         | Vacía.                                   | Registrar sólo los indicios efectivamente descritos en las fuentes. |
| `ausente`                       | No hay explicación ni indicio pertinente que permita proponer una relación con el cierre. La ausencia de comentarios y un `CI=success` no constituyen por sí solos una razón o indicio causal.                        | Vacía.                                   | Vacías.                                                             |

**Importante:** `closed` más CI fallido, una alerta de *threat detection*, la edición de un archivo protegido o la falta de actividad no prueban la causa del cierre. Un fallo de tests tampoco demuestra un `fallo_orquestacion`: podría ser una falla de compilación o test de otro origen. La proximidad temporal no sustituye una explicación. Del mismo modo, «cierre sin explicación» es una descripción de la evidencia faltante y no una categoría de razón principal.

No es necesario que la explicación la emita una persona: un bot que declare expresamente que cerró el PR por una política de expiración puede aportar evidencia explícita. En cambio, un bot que sólo advierte de un riesgo o de revisión obligatoria es una señal contextual, salvo que documente que tal advertencia fue la causa del cierre.

## 3. Categorías confirmadas de razón principal

| Identificador | Definición operacional | Incluir cuando… | Excluir cuando… |
| --- | --- | --- | --- |
| `datos_obsoletos` | La información/datos del cambio han perdido actualidad o validez, y esta circunstancia es citada para descartar el PR. | Una explicación de cierre refiere expresamente *stale data*, flakiness no vigente o datos superados. | Únicamente cambió la rama, se considera innecesaria una documentación o un workflow quedó inactivo. |
| `cambio_no_necesario` | Una persona vinculada al cierre declara que la modificación propuesta no es necesaria. | Comentarios como «not needed» o «no requiere documentación» referidos a la decisión de descartar el PR. | Hay obsolescencia comprobada de datos, insuficiencia funcional, o sólo ausencia de explicación. |
| `continuacion_manual` | Se cierra el PR porque el trabajo se continuará o realizará manualmente, según declaración explícita. | El autor o responsable comunica esa decisión en conexión con el cierre. | Se solicita simplemente una revisión humana o se detectan archivos protegidos. |
| `expiracion_automatica` | Un proceso automatizado indica que cerró el PR por alcanzar un plazo/condición de expiración. | Aviso de cierre por expiración claramente asociado al PR. | Un marcador de expiración en el cuerpo que no confirme que esa fue la causa del cierre. |
| `implementacion_insuficiente` | Se rechaza el cambio por no cubrir una necesidad o comportamiento funcional esperado. | Un comentario de cierre documenta insuficiencia funcional. | Sólo falla CI sin explicación causal, o el cambio se descarta como innecesario. |
| `destino_incorrecto` | La decisión de no integrar se explica porque el PR apunta a una rama o destino equivocado. | El comentario de cierre señala explícitamente una rama de release inadecuada. | Problemas de push, tamaño del diff u obsolescencia de contenido. |

## 4. Vocabulario de señales contextuales no causales

El campo `senales_contextuales` admite vacío o más etiquetas separadas por `;`. No son categorías de razón principal y nunca se cuentan en la respuesta cuantitativa a RQ. La etiqueta se registra sólo si hay una señal descrita en el material proporcionado.

| Etiqueta                              | Cuándo utilizarla                                                                                                                         |
| ------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| `ci_fallido`                          | Hay un test, build o check de CI fallido; sin declaración que lo conecte al cierre.                                                       |
| `archivo_protegido`                   | El PR o revisión registra una regla de archivo protegido y escrutinio manual.                                                             |
| `alerta_amenaza_agente`               | Un bot o herramienta registró aviso de amenaza; no se sabe si motivó el cierre.                                                           |
| `error_parseo`                        | Se menciona parsing defectuoso sin explicación de cierre atribuida a ese error.                                                           |
| `error_red_agente`                    | Se registra bloqueo por firewall, red o dominio no permitido sin vínculo con el cierre.                                                   |
| `cierre_sin_justificacion`            | Hay una discusión o circunstancia del cierre descrita como silenciosa, sin razón verificable. No significa «abandono» ni es razón causal. |
| `revision_manual_solicitada`          | Se pide revisión humana sin que conste decisión causal de no integrar.                                                                    |
| `instruccion_cierre_manual`           | El contenido contiene una instrucción de cierre manual, pero no está acreditada como motivo concreto.                                     |
| `aprobado_sin_merge`                  | Se documenta una aprobación del PR, aunque finalmente fue cerrado sin merge.                                                              |
| `validacion_no_concluyente`           | La información disponible menciona validación insuficiente o inconclusa, sin conexión explícita al cierre.                                |
| `posible_obsolescencia`               | Hay indicios de pérdida de vigencia, pero falta justificar la decisión de cierre.                                                         |
| `posible_redundancia`                 | Se cuestiona solapamiento con otra automatización/proceso, sin causa confirmada.                                                          |
| `revision_no_concluyente`             | Hay señales de revisión contradictorias o insuficientes para determinar motivo.                                                           |
| `otro_pr_existente`                   | Otro PR cubre al menos parte del cambio; no implica automáticamente duplicidad causal.                                                    |
| `contenido_posiblemente_ya_integrado` | El cuerpo sugiere que el contenido/fuente estaba integrado en otro lugar, sin explicar el cierre.                                         |
| `rechazo_sin_motivo_documentado`      | Hay indicación de rechazo/desestimación sin argumento que permita una razón principal.                                                    |
| `posible_reemplazo_por_otro_pr`       | Se menciona un reemplazo aparente por otro PR, sin atribución expresa del cierre.                                                         |

## 5. Esquema del CSV

| Columna                                  | Contenido y validación                                                                                                                             |
| ---------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| `repo`, `pr_id`, `pr_url`, `workflow_id` | Identificadores heredados de la extracción. Clave de unicidad recomendada: `(repo, pr_id)` o `pr_url`. No asumir unívoca la relación PR–ejecución. |
| `evidencia_disponible`                   | Enum obligatorio: `explícita`, `ambigua`, `ausente`. Se refiere a evidencia causal sobre la no integración, no a cantidad de comentarios/CI.       |
| `razon_principal`                        | Código del apartado 3; no vacío sólo si `evidencia_disponible=explícita`.                                                                          |
| `senales_contextuales`                   | Etiquetas de apartado 4 separadas por `;`; no aportan causas confirmadas.                                                                          |
| `fuente_evidencia`                       | Descripción o localizador existente de comentarios, revisiones, cuerpo o CI. Preferir ID/URL de comentario/revisión/check y tipo de fuente.        |
| `nota_revision`                          | Justificación actual de la codificación y delimitación de qué es causa y qué es señal.                                                             |
| `verificacion_fuente`                    | URL que evidencia lo descrito en `razon_principal` y `fuente_evidencia`                                                                            |

## 6. Procedimiento para la revisión

1. Verificar, en los datos de extracción, que cada URL corresponde a un PR realmente `closed`, no integrado (`merged_at=null`), y que procede de un `create_pull_request` emitido por GHAW.
2. Recuperar el cuerpo, comentarios, reviews, comentarios de revisión y CI con sus IDs, autores, fechas y URLs. Distinguir mensajes anteriores/posteriores al cierre.
3. Aplicar primero el nivel de evidencia (`explícita`, `ambigua`, `ausente`), y después la categoría principal únicamente a los explícitos. Registrar evidencias técnicas no concluyentes como señales y dejar razón vacía en los otros niveles.
4. Agrupar por similitud conceptual (*card sorting* abierto). Antes de crear/modificar/fusionar una categoría, fijar su nombre, definición y criterios de inclusión/exclusión.
5. Contrastar la causa propuesta con el texto del cierre, autor, momento temporal y otras evidencias. Ante desacuerdo o falta de vínculo explícito, mantener `ambigua`.
6. Informar separadamente: número total de PRs recuperados, distribución de niveles de evidencia, y frecuencias de `razon_principal` sólo entre casos explícitos, con denominador declarado. Ilustrar con casos verificables y no inferir conclusiones para todos los PRs de GHAW.

## 7. Resultados

| Indicador                        | Codificación final |
| -------------------------------- | -----------: |
| PRs únicos                       |           82 |
| Evidencia explícita              |            9 |
| Evidencia ambigua                |           37 |
| Evidencia ausente                |           36 |
| Razones principales registradas  |            9 |
