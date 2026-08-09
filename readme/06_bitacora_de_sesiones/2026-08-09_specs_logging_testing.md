# Sesion: specs 23/24 de logging propio y testing fail-detect

**Fecha:** 2026-08-09

**Ramas:** `spec/23-custom-logging` y `spec/24-testing-suite`

**Objetivo:** integrar dos especificaciones tecnicas nuevas, mantener la fuente de verdad
del reto y dejar actualizado el plan de batches sin mezclar cambios de runtime.

## Alcance y archivos

- `specs/23_custom_logging_system.md`: contrato del logger propio, JSONL, niveles, correlacion,
  redaccion, stack traces y puntos de instrumentacion.
- `specs/24_testing_suite.md`: suite fail-detect unitaria/integracion, fixtures, mocks,
  cobertura, contratos de voz/RAG/admin/render y frontera manual.
- `specs/00_mvp_specification.md` y `specs/01_implementation_plan.md`: dependencias y orden.
- `tasks/plan.md` y `tasks/todo.md`: grafo, fases y tareas ejecutables.
- `README.md`: matriz de batches y estado `SPECIFIED`.
- `readme/06_bitacora_de_sesiones/`: registro e indice.

No se modificaron `dataset/`, `data/`, `.env`, credenciales ni codigo de runtime.

## Decisiones y supuestos

- La ultima spec numerada es la 22; las nuevas son 23 y 24.
- La spec 23 se ejecuta primero como Batch 8, con ownership del logger y su instrumentacion.
- La spec 24 es Batch 9, secuencial de validacion: puede preparar fixtures en paralelo, pero
  no se declara verde hasta estabilizar nombres, redaccion y correlacion de los eventos.
- `data/events.jsonl` continua siendo fuente de metricas. `data/app.log.jsonl` es el artefacto
  diagnostico propuesto; ninguno se versiona.
- El modelo declarado no cambia: `llama-3.1-8b-instant` via Groq, familia Meta Llama permitida.
- G2/G4/G5 y la voz real siguen siendo evidencia manual; los mocks solo verifican contratos.

## Matriz de ejecucion actualizada

| Batch | Specs incluidas | Tipo | Subagente | Scopes / directorios afectados | Estado |
|---|---|---|---|---|---|
| 1 | 11, 13 | Paralelo por modulos | UX/RAG | `app/services/agent.py`, `messages.py`, config RAG | integrado |
| 2 | 14, 20 | Paralelo por modulos | Vector/Frontend | `app/services/rag.py`, `app/web/`, rutas | integrado |
| 3 | 15, 21 | Paralelo por modulos | Benchmark/Portal | `configs/`, `benchmarks/`, `/call` | integrado |
| 4 | 16, 22 | Paralelo con dependencias | Chain/VAD | loaders, prompts, `voice-loop.js`, tests VAD | integrado |
| 5-6 | 17, 18 | Secuencial por dependencias | Observabilidad/Operaciones | `observability.py`, metricas, rollout, backup | parcial/documentado |
| 7 | 19 | Integrador secuencial | Integrador | README, arquitectura, estados, bitacora | integrado |
| 8 | 23 Custom Logger | Paralelo / aislado | Subagente Logger | `app/services/logger.py`, `app/config.py`, `app/main.py`, `app/services/*` | especificado; pendiente |
| 9 | 24 Testing | Secuencial / validacion | Subagente Tester | `tests/*`, `pyproject.toml`, contratos UI y datos | especificado; depende de Batch 8 |

## Comandos y resultados observables

- Se leyeron `AGENTS.md`, las dos guias de agente, las skills SDD/Git-Commit, el snapshot
  oficial (`README`, rubrica y stack), README/docs/specs/MVP y la bitacora.
- `git status --short --branch`: inicio limpio en `main`.
- Se creo `spec/23-custom-logging`, se commitio y se hizo push; commit de spec: `60a112c`.
- Merge explicito de la rama 23 a `main`: `31e8a59`, push de `main` completado.
- Se creo `spec/24-testing-suite` desde el `main` actualizado.
- `git diff --check`: debe permanecer sin whitespace errors antes del commit final.
- No se ejecutaron pruebas de runtime: el cambio de esta sesion es documental y las specs
  declaran los comandos de implementacion y verificacion futura.

## Riesgos y siguiente accion

- Instrumentar muchos servicios puede introducir logs duplicados o PII: resolverlo con un
  adapter central, allowlist y pruebas negativas antes de ampliar la cobertura.
- La suite no debe declarar G4/G5 por mocks ni convertir una cobertura alta en evidencia de
  voz real.
- Siguiente accion verificable: implementar Batch 8, ejecutar focused tests de logger y luego
  Batch 9 con suite completa, coverage, Ruff, Node check y validacion de dataset.
