# Spec: Observabilidad RAG y trazabilidad con LangSmith

**ID:** `RAG-OBS-001`  
**Estado:** `PROPOSED`; metricas locales existentes, LangSmith no integrado  
**Version:** `0.1.0`  
**Fecha:** `2026-08-08`  
**Depende de:** [`13_rag_environment_configuration_specification.md`](13_rag_environment_configuration_specification.md), [`16_rag_langchain_orchestration_specification.md`](16_rag_langchain_orchestration_specification.md), [`07_testing_unit_integration_specification.md`](07_testing_unit_integration_specification.md)

## Objective

Instrumentar el recorrido completo de una consulta RAG y de una llamada de voz para responder, con
evidencia, estas preguntas:

- donde se consume el presupuesto de latencia;
- que backend y version de indice produjeron cada fuente;
- por que se obtuvo una respuesta grounded, fallback o abstencion;
- si hubo un vector stale, una revision concurrente o una fuga de documento;
- si LangChain, Chroma, embeddings, LLM o voz degradaron el intercambio.

LangSmith sera el destino opcional de trazas LangChain. La fuente durable local continua siendo
`data/events.jsonl`, SQLite y `/api/metrics`. Desactivar LangSmith no debe quitar metrica minima ni
impedir una respuesta segura.

## Supuestos y decisiones

1. `LANGCHAIN_TRACING_V2=false` es el default local y de cualquier ambiente sin politica de
   privacidad aprobada.
2. En staging/production `LANGSMITH_CAPTURE_CONTENT=false` y `LANGSMITH_REDACT_PII=true` son
   obligatorios. Por defecto se envian nombres de nodo, duraciones, conteos, hashes truncados y
   razones, no transcripts, audio, chunks, nombres de paciente ni prompts completos.
3. `trace_id`, `run_id`, `retrieval_id`, `call_id` y `turn_id` se correlacionan, pero cada destino
   aplica pseudonimizacion y retencion propia.
4. El callback/cliente externo tiene un presupuesto fijo y es best-effort. Un fallo de red o API
   key no modifica el resultado del RAG ni bloquea la voz.
5. Las metricas de voz de la rubrica siguen siendo `speech_ended_at -> audio_started_at`; una
   traza de servidor no reemplaza esos timestamps.
6. No se afirma cumplimiento legal o clinico por integrar LangSmith. La configuracion de privacidad
   debe ser revisada antes de exponer el sistema fuera de localhost.

## Tech Stack

| Area | Seleccion |
|---|---|
| Tracing de nodos | callbacks de `langchain-core` |
| Backend opcional | LangSmith |
| Eventos locales | `events.jsonl` y `MetricsService` existente |
| Correlacion | `trace_id`, `run_id`, `retrieval_id`, `call_id`, `turn_id` |
| Redaccion | middleware de metadata y filtros de contenido |
| Dashboards | consultas de LangSmith y agregacion local |
| Alertas | metricas y thresholds documentados, no texto generativo |

## Commands

```text
python -m pytest tests/test_observability_contracts.py tests/test_metrics.py -q --basetemp <temp>/rag-observability
python -m pytest tests/test_agent.py tests/test_calls.py -q --basetemp <temp>/rag-trace-contract
python -m scripts.check_observability --redacted --offline
python -m scripts.export_rag_metrics --input <temp>/events.jsonl --output <temp>/rag-metrics.json
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Con LangSmith habilitado solo en un entorno controlado:

```text
python -m scripts.check_observability --online --project techsphere-rag-staging
```

El comando online no se ejecuta en CI ni se presenta como evidencia si no conserva fecha,
commit, entorno, politica de captura y resultado de redaccion.

## Project Structure

```text
app/services/observability.py       -> contexto, spans, redaccion y exporters.
app/services/metrics.py             -> eventos locales y agregados existentes.
app/services/rag.py                 -> retrieval_id, backend y latencias.
app/services/agent.py               -> prompt/model spans sin contenido por defecto.
app/services/calls.py               -> correlacion de call/turn/voice timing.
scripts/check_observability.py      -> valida flags, secrets y redaccion.
scripts/export_rag_metrics.py       -> metricas reproducibles desde JSONL.
tests/test_observability_contracts.py -> redaction, no-op y fallos del exporter.
readme/04_metricas_y_evidencia.md   -> resultados verificables y limites.
```

## Trace Model

### Jerarquia

```text
trace: call/{call_id}
  span: voice.stt
  span: turn/{turn_id}
    span: triage
    span: rag.retrieve
      span: rag.embed_query
      span: rag.fts5
      span: rag.chroma
      span: rag.fusion
      span: rag.hydrate_sqlite
      span: rag.citation_validation
    span: prompt.compose
    span: llm.generate
    span: response.validate
  span: voice.tts
```

Los nombres de span son estables. Una etapa omitida se marca `not_run` y no se interpreta como
latencia cero.

### Atributos tecnicos permitidos

```text
trace_id
run_id
retrieval_id
call_id_hash
turn_id_hash
retrieval_backend
index_version
chunking_version
embedding_provider
embedding_model_name
embedding_dimension
distance_metric
corpus_revision_before
corpus_revision_after
candidate_count
returned_count
source_count
rag_queries
cache_hit
fallback_reason
triage_level
model_family
model_version
prompt_version
status
error_class
latency_ms
```

`call_id` y `turn_id` completos pueden permanecer en la persistencia local auditada, pero el
exporter externo usa hashes o IDs de baja sensibilidad. `source_ids` externos son hashes
truncados; la cita legible se conserva localmente para el administrador autorizado.

### Metricas nuevas

| Metrica | Definicion |
|---|---|
| `rag_requests_total` | consultas recibidas por backend/resultado |
| `rag_query_latency_ms` | embedding + backend + hydration, separado de LLM |
| `rag_embedding_latency_ms` | tiempo de embedding de query/documento |
| `chroma_query_latency_ms` | acceso a coleccion activa |
| `rag_fusion_latency_ms` | fusion y orden estable |
| `rag_empty_total` | consultas sin evidencia suficiente |
| `rag_fallback_total` | uso de FTS5/fallback por razon |
| `rag_citation_invalid_total` | candidatos o salidas sin cita valida |
| `rag_revision_mismatch_total` | evidencia invalidada por cambio de revision |
| `rag_disabled_document_leak_total` | hit de disabled antes de filtro |
| `rag_deleted_document_leak_total` | hit de eliminado antes de filtro |
| `rag_index_upsert_errors_total` | fallos de escritura vectorial |
| `rag_index_lag_seconds` | diferencia entre SQLite disponible y vector listo |
| `rag_embedding_cache_hit_ratio` | hits de cache compatible |
| `voice_turn_e2e_latency_ms` | `speech_ended_at` a `audio_started_at` |

`rag_queries` sigue contando consultas logicas del agente. Las llamadas internas a FTS5, Chroma o
callbacks se registran en campos separados y no se suman artificialmente.

## Redaction and Privacy

El filtro debe eliminar o reemplazar:

- nombre, `patient_id`, procedimiento y datos demograficos;
- transcript completo, audio, prompt completo y texto de chunks;
- API keys, Authorization headers, rutas absolutas y contenido de archivos;
- tokens de acceso, errores de proveedor con payload o respuestas no filtradas.

Se permiten:

- clases de error, conteos, duraciones, estados, razones y hashes truncados;
- `triage_level` si la politica de despliegue lo aprueba, sin sintomas textuales;
- version de modelo, indice, chunker y dimension;
- tamaño de contexto y numero de fuentes, no el contexto.

Un modo local de debugging puede guardar contenido en un directorio temporal fuera de Git solo con
un flag explicito, vencimiento corto y advertencia. Ese modo no se activa por defecto ni se usa
para afirmar cumplimiento de production.

## SLOs and Alerting

Targets iniciales:

| Indicador | Umbral de alerta |
|---|---:|
| Error de Chroma | `> 1%` durante 5 minutos |
| Timeout de RAG | `> 0.5%` |
| RAG P95 | `> 500 ms` |
| Query Chroma P95 | `> 100 ms` |
| Citation invalid | cualquier P0; objetivo `0` |
| Revision mismatch | cualquier caso en respuesta |
| Documento deleted/disabled leak | cualquier caso |
| Fallback sobre baseline | `+5 puntos porcentuales` sostenidos |
| Index lag | superior al objetivo de upload publicado |
| Exporter tracing | no puede bloquear solicitudes |

Una alerta clinica roja no depende de estos dashboards. Si la observabilidad falla, triaje,
grounding seguro, fallback y persistencia local deben seguir funcionando.

## `/health` and API Safety

`GET /health` puede exponer:

```text
rag_backend
rag_index_version
embedding_model_name
embedding_dimension
distance_metric
corpus_revision
index_lag_seconds
fallback_available
langsmith_enabled
llm_family
llm_model_version
voice_mode
```

No expone API keys, endpoints privados, rutas absolutas, prompts, contenido de fuentes, pacientes
ni trazas completas. Un estado `degraded` debe incluir una razon codificada segura y no un stack
trace.

## Code Style

El exporter se invoca como efecto lateral protegido, no como parte de la decision:

```python
def record_span(event: SpanEvent, exporter: TraceExporter) -> None:
    local_events.append(redact_for_local(event))
    try:
        exporter.send(redact_for_external(event))
    except TraceExportError:
        metrics.increment("trace_export_error")
```

La excepcion de tracing no se propaga al agente. Las funciones de redaccion son puras y tienen
tests con textos que intentan filtrar secretos o instrucciones.

## Testing Strategy

### Unitarias

- jerarquia y nombres de spans;
- correlacion de IDs y hashes;
- redaccion de PII, audio, transcripts, prompts, chunks, keys y paths;
- flags de captura y sample rate;
- no-op cuando LangSmith esta desactivado;
- exporter caido o lento no bloquea ni cambia respuesta;
- metricas por nodo, percentiles y valores ausentes;
- `/health` sin secretos.

### Integracion

- turno completo genera eventos locales con retrieval, citas, fallback y razones;
- Chroma/FTS5/hybrid reportan backend, version y latencias separadas;
- revision cambiada produce `corpus_changed` y span de invalidacion;
- upload/delete actualiza lag y estado de indexacion;
- `/api/metrics` concuerda con `events.jsonl` sin duplicar consultas;
- LangSmith fake recibe metadata redactada y ningun contenido cuando la flag esta apagada.

### Manual

- revisar una traza de staging con un documento marcador sin PII;
- verificar dashboard P50/P95 contra logs de voz reales;
- comprobar retencion y borrado de trazas;
- capturar evidencia sin incluir API key o transcript completo.

## Boundaries

- **Always:** trazas por nodo, redaccion default, exporter best-effort, eventos locales, campos de
  version/revision y separacion de latencias.
- **Ask first:** habilitar contenido en LangSmith, cambiar retencion, enviar datos fuera de la
  red local, añadir alertas externas o cambiar los campos publicos de `/health`.
- **Never:** registrar audio o secretos, usar LangSmith como fuente clinica, bloquear la respuesta
  por una API de observabilidad, fabricar P50/P95 o marcar G4 por una traza sin audio real.

## Success Criteria

- **OBS-AC-01:** cada nodo RAG y voz tiene trace/span con nombre, estado, latencia y correlacion.
- **OBS-AC-02:** LangSmith se puede activar por entorno sin ser requisito del camino local ni de
  las pruebas.
- **OBS-AC-03:** staging/production no envian contenido clinico, PII, audio, prompts completos,
  secrets ni paths al exporter.
- **OBS-AC-04:** eventos locales y `/api/metrics` conservan latencia de voz, tokens, llamadas,
  consultas RAG, sources y versiones.
- **OBS-AC-05:** se observan separadamente embedding, Chroma, FTS5, fusion, LLM y audio.
- **OBS-AC-06:** un fallo del exporter no cambia triaje, grounding, fallback, abstencion o audio.
- **OBS-AC-07:** los dashboards permiten detectar leak, mismatch, lag, errores y regresion de
  latencia con thresholds documentados.

## Trazabilidad

| Requisito | Evidencia | Gate |
|---|---|---|
| Metricas obligatorias | `events.jsonl`, `/api/metrics`, dashboard | repositorio |
| Latencia de voz | timestamps browser reales | G4 y rubrica |
| Trazabilidad de fuentes | `source_ids`, version, revision y citation | criterio RAG |
| Privacidad | tests de redaccion y config | seguridad |
| Diagnostico de fallos | spans por nodo y fallback_reason | operacion |

## Open Questions

1. Confirmar cuenta/proyecto de LangSmith, region, retencion y responsable de acceso.
2. Confirmar si se permite hash de IDs de llamada en el destino externo o se requiere correlacion
   solo local.
3. Confirmar el backend de metricas de production si `events.jsonl` no es suficiente para varios
   workers.
4. Confirmar si el panel de costos incluira embeddings y almacenamiento, ademas de LLM/STT/TTS.
