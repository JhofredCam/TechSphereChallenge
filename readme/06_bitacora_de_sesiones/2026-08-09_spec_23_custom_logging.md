# Sesion: especificacion de logging propio y trazabilidad

**Fecha:** 2026-08-09

**Rama:** `spec/23-custom-logging`
**Alcance:** redactar `specs/23_custom_logging_system.md` conforme al contrato oficial, al
runtime Python actual y a las guias de planificacion/ejecucion.

## Archivos tocados

- `specs/23_custom_logging_system.md`
- esta entrada de bitacora y su indice

No se modificaron `dataset/`, `data/`, `.env`, credenciales ni codigo de runtime.

## Decisiones y supuestos

- La ultima spec existente es la 22; el logger propio recibe el numero 23.
- El modulo objetivo es `app/services/logger.py`, no un logger JavaScript: el checkout es
  Python/FastAPI.
- `MetricsService` conserva `data/events.jsonl` para metricas; el logger propio propone
  `data/app.log.jsonl` para diagnostico y stack traces redacted.
- La consola queda como sink complementario. La trazabilidad minima exige JSONL local,
  correlacion por llamada/turno/VAD/RAG y fail-open del sink.
- Se registran tipos, estados, tamanos, hashes y conteos; no se registran audio, transcript,
  prompts, chunks, secretos ni PII.

## Fuentes y comandos ejecutados

- Se leyeron las skills `spec-driven-development` y `git-commit`.
- Se leyeron `AGENTS.md`, las dos guias de agente, el snapshot oficial del reto, rubrica,
  stack tecnico, README, specs 00/02/07/17/19/22, plan/tareas y la bitacora.
- `git status --short --branch`: checkout inicial limpio en `main`.
- `git switch -c spec/23-custom-logging`: rama dedicada creada antes del cambio.
- Inspeccion del runtime: `observability.py`, `metrics.py`, `calls.py`, `agent.py`, `rag.py`,
  `voice.py`, `config.py`, `main.py` y pruebas existentes.

## Verificacion y pendientes

- La spec contiene objetivo, supuestos, comandos, estructura, contrato de niveles, sinks,
  redaccion, puntos de instrumentacion, testing, limites y criterios `LOG-AC-*`.
- No se ejecutaron pruebas de runtime porque esta sesion crea contrato y no implementa el
  logger.
- Siguiente accion: integrar la spec 23 en la matriz de batches y crear la spec 24 en su rama
  dedicada de testing fail-detect; despues implementar y verificar el contrato.
