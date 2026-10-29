# Resumen de codificación final: analisis_cualitativo.csv

PRs únicos: 82; repositorios: 17; nombres de workflow: 15; pares repositorio–workflow: 17.

## Disponibilidad de evidencia

| Nivel | PRs | Porcentaje del total |
| --- | ---: | ---: |
| explícita | 9 | 11,0% |
| ambigua | 37 | 45,1% |
| ausente | 36 | 43,9% |

## Razones principales documentadas

Denominador: 9 PRs con evidencia explícita; una razón por PR.
Las señales contextuales no aportan causas. La atribución causal requiere revisión manual.

| Razón | PRs |
| --- | ---: |
| `cambio_no_necesario` | 3 |
| `datos_obsoletos` | 2 |
| `continuacion_manual` | 1 |
| `expiracion_automatica` | 1 |
| `implementacion_insuficiente` | 1 |
| `destino_incorrecto` | 1 |

PRs ambiguos con `ci_fallido`: 25/37.

## Fuentes de los casos explícitos

| PR | Razón principal | Fuente |
| --- | --- | --- |
| [dotnet/macios#26373](https://github.com/dotnet/macios/pull/26373) | `continuacion_manual` | [Fuente](https://github.com/dotnet/macios/pull/26373#issuecomment-5168742319) |
| [dotnet/msbuild#14607](https://github.com/dotnet/msbuild/pull/14607) | `datos_obsoletos` | [Fuente](https://github.com/dotnet/msbuild/pull/14607#issuecomment-5542674558) |
| [dotnet/msbuild#14646](https://github.com/dotnet/msbuild/pull/14646) | `datos_obsoletos` | [Fuente](https://github.com/dotnet/msbuild/pull/14646#issuecomment-5542721830) |
| [fideus-labs/ngff-zarr#609](https://github.com/fideus-labs/ngff-zarr/pull/609) | `expiracion_automatica` | [Fuente](https://github.com/fideus-labs/ngff-zarr/pull/609#issuecomment-5067162140) |
| [fsprojects/FSharp.Formatting#1337](https://github.com/fsprojects/FSharp.Formatting/pull/1337) | `implementacion_insuficiente` | [Fuente](https://github.com/fsprojects/FSharp.Formatting/pull/1337#issuecomment-5864704518) |
| [microsoft/aspire.dev#1766](https://github.com/microsoft/aspire.dev/pull/1766) | `cambio_no_necesario` | [Fuente](https://github.com/microsoft/aspire.dev/pull/1766#issuecomment-5894681458) |
| [microsoft/aspire.dev#1771](https://github.com/microsoft/aspire.dev/pull/1771) | `destino_incorrecto` | [Fuente](https://github.com/microsoft/aspire.dev/pull/1771#issuecomment-5876229627) |
| [microsoft/aspire.dev#1799](https://github.com/microsoft/aspire.dev/pull/1799) | `cambio_no_necesario` | [Fuente](https://github.com/microsoft/aspire.dev/pull/1799#issuecomment-5918670572) |
| [vaadin/docs#6067](https://github.com/vaadin/docs/pull/6067) | `cambio_no_necesario` | [Fuente](https://github.com/vaadin/docs/pull/6067#issuecomment-5726893483) |
