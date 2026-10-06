# Codebook para el análisis cualitativo de razones de cierre de PRs

## Propósito y unidad de análisis

Este codebook documenta la codificación manual de las razones por las que se
cerraron sin merge los pull requests (PRs) recogidos en
`analisis_cualitativo.csv`. La unidad de análisis es un PR. Se codifica la
explicación mejor respaldada por la evidencia disponible en GitHub (cuerpo,
comentarios, reviews y, como contexto, información de CI); no se infiere una
motivación que la evidencia no permita sostener.

El campo `razon_principal` representa la causa o explicación predominante del
cierre. `razon_secundaria` recoge un factor concurrente distinto que contribuye
a explicar el cierre. Ambos campos deben contener los identificadores de las
categorías de este documento o quedar vacíos si no hay evidencia suficiente.
Las categorías de razón describen fenómenos de niveles distintos (p. ej., una
causa técnica y la decisión de cierre): se permite más de una cuando la
evidencia apoya explícitamente esa combinación, pero no se debe rellenar una
categoría secundaria por mera especulación.

## Categorías de razón

| Identificador | Definición operacional | Incluir cuando… | No incluir cuando… |
| --- | --- | --- | --- |
| `cierre_silencioso` | No hay una explicación explícita de una persona mantenedora/revisora que justifique la decisión de cerrar el PR. Describe la falta de explicación humana observable, no una causa técnica subyacente. | No hay comentario o review que explique por qué se cerró; puede haber una pregunta posterior sin respuesta. Puede coexistir con un diagnóstico técnico del agente (p. ej., un bloqueo de red) si ese diagnóstico no explica explícitamente la decisión de cierre. | Un mantenedor/revisor sí explica el cierre. Un mensaje automático que sólo informa un fallo técnico no cuenta, por sí solo, como explicación humana de la decisión. |
| `error_red_agente` | El agente o workflow informa que no pudo acceder a una fuente o dominio debido a restricciones de red, firewall o allowlist. | El cuerpo, log o comentario del PR atribuye el bloqueo a firewall, red o dominio no permitido. | El fallo es de parsing, ejecución, validación u orquestación y no se menciona una restricción de red. |
| `modificacion_archivo_protegido` | El PR modifica uno o más archivos protegidos y la política resultante exige revisión o escrutinio manual antes del merge. | La evidencia señala expresamente archivos protegidos modificados y una exigencia de aprobación/revisión humana asociada. | Sólo hay una alerta genérica de seguridad/amenaza sin identificar la regla de archivo protegido. |
| `abandono_revisor` | Un revisor o mantenedor deja de avanzar el PR, lo cierra o lo considera no vigente; la evidencia atribuye la decisión a abandono, obsolescencia o falta de seguimiento. | Un comentario indica que el PR está stale/obsoleto, que se cierra por falta de actividad o que ya no se continuará. | El cierre se explica por una duplicación o reemplazo concreto sin señal de abandono; en tal caso codificar sólo la categoría específica respaldada. |
| `datos_obsoletos` | El contenido o los datos del PR ya no son válidos o actuales, por lo que el cambio dejó de ser necesario o correcto. | La explicación menciona datos stale/desactualizados, fuentes superadas o cambios que ya no reflejan el estado actual. | Sólo hay inactividad del autor/revisor sin evidencia de obsolescencia del contenido. |
| `amenaza_agente` | Una detección de seguridad o de amenaza agéntica señala que el contenido generado por el agente requiere escrutinio antes de poder integrarse. | La salida de threat detection o una política equivalente emite explícitamente una alerta sobre el PR o su contenido. | El único problema es una regla concreta de archivos protegidos; usar `modificacion_archivo_protegido` cuando esa sea la explicación identificada. |
| `error_parseo` | Un fallo de análisis sintáctico/estructural impide interpretar correctamente una entrada o salida del agente/workflow. | La evidencia identifica parsing, parse error o error equivalente como el fallo. | La ejecución falla por una clave/condición de control del workflow; considerar `fallo_orquestacion`. |
| `fallo_orquestacion` | Un defecto en la coordinación o lógica de control del workflow/agente impide completar correctamente una operación o validación. | Se identifica un error en ramas, deduplicación, secuenciación, prefijos o lógica de orquestación. | El problema es exclusivamente un error de parseo de contenido; usar `error_parseo`. |
| `pr_huerfano` | El workflow deja un PR creado o actualizado en estado huérfano: no queda asociado/registrado correctamente con la ejecución o se produce una condición explícita de orphaning. | La evidencia describe directamente un PR huérfano, duplicado como huérfano o una pérdida de asociación causada por el workflow. | Se observa únicamente una falla interna sin evidencia de que el PR haya quedado huérfano. |

Las categorías se derivan de los valores efectivamente usados en la hoja de
análisis. Si aparece una razón nueva, no debe forzarse dentro de una categoría
existente: anotar la evidencia y proponer un identificador nuevo con definición
antes de continuar la codificación.
