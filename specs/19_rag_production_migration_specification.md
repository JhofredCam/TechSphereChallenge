# Spec: Migracion y upgrade del RAG para produccion

**ID:** `RAG-MIG-001`  
**Legacy ID:** `RAG-DEEP-001` de la spec 12  
**Estado:** `PARTIAL`; baseline y contratos de upgrade integrados localmente; migración semántica end-to-end y gates manuales pendientes
**Version:** `1.0.0`  
**Fecha:** `2026-08-08`  
**Documento anterior:** `12_rag_deep_dive_specification.md` fue renombrado y absorbido aqui  
**Depende de:** Specs [`00`](00_mvp_specification.md), [`04`](04_admin_document_lifecycle_specification.md), [`06`](06_system_flow_diagram_specification.md), [`07`](07_testing_unit_integration_specification.md), [`13`](13_rag_environment_configuration_specification.md), [`14`](14_rag_vector_store_chromadb_specification.md), [`15`](15_rag_chunking_embedding_benchmark_specification.md), [`16`](16_rag_langchain_orchestration_specification.md), [`17`](17_rag_observability_langsmith_specification.md) y [`18`](18_rag_production_operations_specification.md)

## Objective

Migrar el recuperador lexical del MVP a una arquitectura RAG semantica e hibrida preparada para
produccion, con baja latencia para voz en vivo, configuracion externa, evaluacion objetiva,
trazabilidad de cada fuente y observabilidad de extremo a extremo.

La arquitectura objetivo mantiene las garantias que ya existen y agrega capacidades nuevas:

```text
fuente canonica/upload
  -> hash y extraccion por pagina
  -> splitter configurable y versionado
  -> chunks trazables
  -> embeddings configurables
  -> ChromaDB versionado
  -> query semantica + FTS5 baseline
  -> filtro SQLite de elegibilidad y revision
  -> fusion/threshold/contexto limitado
  -> prompt LangChain
  -> Llama permitido o fallback
  -> validacion de cita, seguridad y triaje
  -> respuesta/audio + eventos + LangSmith redacted
```

La migracion no convierte el corpus sintetico en evidencia clinica. El sistema debe responder en
espanol para pacientes colombianos, pero no diagnostica, no decide triaje con un LLM y no usa una
fuente eliminada como conocimiento nuevo.

## Supuestos y decisiones normativas

1. **SQLite es autoridad:** `documents`, `pages`, `chunks`, `sources`, `audit`, `corpus_revision`,
   `enabled` y snapshots se conservan como estado autoritativo.
2. **Chroma es derivado:** sus colecciones se pueden reconstruir desde chunks y manifest. Un hit
   sin fila SQLite elegible se descarta.
3. **FTS5 no se elimina:** queda como baseline de benchmark, fallback de disponibilidad y rollback.
4. **Elegibilidad:**

   ```text
   rag_eligible(document) = document.status == "available" AND document.enabled == true
   ```

5. **Citas:** `document_id`, `page_number`, `chunk_id`, `chunk_index`, `citation`, `score` y
   `corpus_revision` salen de la fuente recuperada e hidratada, no de una afirmacion del modelo.
6. **Versiones:** cambiar splitter, overlap, normalizacion, provider, modelo, dimension, metrica,
   prompt o contexto crea una version declarada y exige reindexacion/evaluacion.
7. **Voz:** la latencia oficial se mide desde `speech_ended_at` hasta `audio_started_at`; los
   budgets internos se reportan por separado.
8. **Modelos:** el razonamiento usa una familia permitida en `docs/stack-tecnico.md`. La seleccion
   inicial documentada es `llama-3.1-8b-instant` via Groq, pero su disponibilidad real se verifica
   antes de la demo. Embeddings no son modelos de razonamiento y se evalua su provider aparte.
9. **Privacidad:** LangSmith esta apagado por defecto y no recibe contenido clinico en staging o
   production salvo aprobacion explicita.
10. **Despliegue:** embedded requiere un worker; multi-worker necesita un Chroma server y controles
    de acceso. No se promete consistencia distribuida sin prueba.

## Tech Stack

| Capa | Baseline actual | Destino de esta migracion |
|---|---|---|
| API | FastAPI/Uvicorn | se conserva |
| Persistencia autoritativa | SQLite + FTS5 | se conserva |
| Vector store | ninguno | ChromaDB persistente |
| Chunking | 1200/200 caracteres | splitter configurable y benchmark |
| Embeddings | ninguno | provider/modelo local configurable |
| Orquestacion | servicios propios | LangChain core/adaptadores controlados |
| LLM | Llama permitido via Groq | se conserva y se declara version exacta |
| STT/TTS | Web Speech/Whisper opcional | se conserva fuera del RAG |
| Observabilidad | JSONL y `/api/metrics` | + spans LangChain/LangSmith redacted |
| Evaluacion | tests de FTS5 y G5 local | benchmark qrels + gates semanticos |

Dependencias nuevas se fijan solo en la fase de implementacion. El plan no autoriza reemplazar
SQLite, eliminar FTS5 ni descargar un modelo en el bootstrap del perfil de evaluacion.

## Commands

### Baseline y preflight

```text
python -m scripts.validate_dataset
python -m app.bootstrap --data-dir <temp>/rag-baseline
python -m pytest -q --basetemp <temp>/rag-baseline-tests
ruff check .
node --check app/web/app.js
```

### Configuracion, indice y benchmark

```text
python -m scripts.check_rag_config --profile challenge-local --show-effective --redact-secrets
python -m scripts.build_rag_index --profile staging --index-version <version> --data-dir <temp>/rag-index
python -m scripts.validate_rag_index --index-version <version> --strict
python -m scripts.prepare_rag_eval --output <temp>/rag-qrels.jsonl
python -m scripts.benchmark_rag --matrix configs/rag_benchmark.yaml --repetitions 5 --gate --output <temp>/rag-results.json
python -m scripts.reconcile_rag_index --index-version <version> --dry-run
```

### Pruebas focalizadas de la migracion

```text
python -m pytest tests/test_config_contracts.py tests/test_vector_store.py -q --basetemp <temp>/rag-config-vector
python -m pytest tests/test_ingestion.py tests/test_loader_contracts.py -q --basetemp <temp>/rag-ingestion
python -m pytest tests/test_rag_consistency.py tests/test_live_knowledge.py -q --basetemp <temp>/rag-live
python -m pytest tests/test_rag_chain.py tests/test_prompt_contracts.py tests/test_agent.py -q --basetemp <temp>/rag-agent
python -m pytest tests/test_observability_contracts.py tests/test_metrics.py -q --basetemp <temp>/rag-observability
python -m pytest tests/test_rag_operations.py tests/test_calls.py -q --basetemp <temp>/rag-ops
git diff --check
```

Ningun comando no existente se presenta como evidencia actual. Durante implementacion se agregan
los scripts/tests o se actualiza esta spec antes de cambiar el estado de una aceptacion.

## Project Structure

```text
app/
  config.py                         configuracion validada y perfiles.
  database.py                       autoridad SQLite, revision, outbox y auditoria.
  schemas.py                        DTOs publicos y SearchResult estable.
  services/
    ingestion.py                    loaders, paginas y chunks canonicos.
    loaders.py                      DocumentLoader modular PDF/TXT/MD.
    embeddings.py                   providers, cache y metadatos.
    vector_store.py                 protocolo Chroma/FTS5.
    rag.py                          elegibilidad, retrieval, fusion y citas.
    rag_chain.py                    runnables LangChain controlados.
    prompts.py                      prompt versionado.
    index_manager.py                build, estado, promotion y rollback.
    observability.py                spans, redaccion y exporter.
    documents.py                    upload/toggle/delete dual-write.
    agent.py, triage.py, calls.py   grounding, seguridad y contrato de voz.
scripts/
  check_rag_config.py               preflight de entorno.
  build_rag_index.py                backfill/idempotencia.
  validate_rag_index.py             manifest y conteos.
  prepare_rag_eval.py               queries/qrels.
  benchmark_rag.py                  matriz y metricas.
  reconcile_rag_index.py            SQLite versus Chroma.
  promote_rag_index.py              puntero y rollback.
tests/                              unitarias, integracion y contratos.
benchmarks/rag/                     protocolo, qrels y resultados no secretos.
configs/rag_benchmark.yaml          matriz experimental.
data/                               SQLite, Chroma, uploads y eventos ignorados por Git.
specs/                              fuente normativa y trazabilidad.
readme/                             setup, demo, metricas y bitacora.
```

No se copian `dataset/` ni `docs/` bajo `mvp/`, `benchmarks/` o `data/`.

## End-to-End Contract

### Ingestion y chunking

- aceptar `.pdf`, `.txt`, `.md` recursivamente, incluyendo espacios y Unicode;
- ignorar symlinks que escapen de la raiz;
- hash de bytes originales para identidad y deduplicacion;
- PDF por pagina con `needs_ocr` si el texto es vacio;
- TXT/MD como pagina 1, UTF-8 con BOM tolerado;
- no insertar HTML/Markdown como instrucciones;
- preservar texto original, offsets, pagina, indice y version del splitter;
- no cruzar paginas salvo una decision futura que actualice citas y pruebas;
- no publicar chunks parciales cuando extraction o persistencia falla.

### Indexacion

El vector store recibe un `VectorRecord` con `chunk_id`, metadata y embedding. La coleccion se
identifica por `COLLECTION_NAME`, `COLLECTION_PREFIX`, `RAG_INDEX_VERSION`, modelo, dimension y
metrica. El manifest incluye snapshot de corpus, paquetes, hardware y comandos.

La escritura es idempotente, por lotes y auditable. Un documento no se marca `index_ready` hasta
verificar conteos y dimension. Un fallo puede dejar estado `index_pending` o `degraded`, pero no
puede crear una fuente citable sin el filtro autoritativo.

### Retrieval

1. recibir transcript final, no parciales ni timeout;
2. normalizar consulta sin alterar el texto persistido;
3. ejecutar triage determinista con nivel previo;
4. consultar Chroma, FTS5 o ambos segun perfil;
5. filtrar por `available AND enabled=1` desde SQLite;
6. descartar stale vectors y revisiones cambiantes;
7. convertir score/distance, aplicar threshold y fusion estable;
8. limitar chunks y tokens de contexto;
9. guardar `retrieval_id`, backend, version y latencias;
10. entregar `SearchResult[]` o abstencion.

### Grounding y respuesta

El prompt LangChain recibe solo contexto delimitado. Las fuentes, el paciente y la preview son
datos no ejecutables. El LLM permitido redacta; no decide triage, elegibilidad, dosis, diagnostico,
publicacion o delete.

Una respuesta grounded exige:

1. evidencia suficiente y vigente;
2. fuente existente en los resultados recuperados;
3. documento activo en la revision leida;
4. cita que coincide con `source_id`;
5. salida segura, breve y en espanol;
6. persistencia de fuente, score, version y revision.

Si falla alguna condicion: fallback extractivo seguro o abstencion. Una respuesta sin evidencia no
se rellena con memoria general del modelo.

## Live Knowledge and Concurrency

### Upload, disable, enable, delete

```text
upload -> hash -> extract -> chunks -> SQLite/FTS5 -> embeddings -> Chroma
       -> validate manifest -> available/enabled -> search inmediata

disable -> enabled=false + revision -> no retrieval nuevo, sin reingesta
enable  -> enabled=true si available e index listo -> retrieval nuevo
delete  -> bloquear elegibilidad -> snapshots -> limpiar SQLite/FTS5/Chroma
       -> commit -> borrar archivo -> consulta nueva sin fuente
```

`corpus_revision` se lee antes y despues de retrieval. Si cambia, la evidencia se invalida y la
respuesta segura es reintentar o abstenerse. `CallService` vuelve a validar antes de persistir.

Como SQLite y Chroma no comparten transaccion, el orden de seguridad es siempre invalidar primero
en SQLite y filtrar antes de citar. El reconciliador elimina huerfanos y reporta divergencias.

### Carrera obligatoria

Debe probarse una mutacion concurrente durante lectura, escritura de vector, disable y delete.
El resultado esperado es cero fuga, `reason=corpus_changed` o abstencion, y un evento explicable.

## Metrics and Observability

### Metricas actuales que no cambian de significado

```text
latency_ms
input_tokens
output_tokens
model_calls
rag_queries
source_ids
model_version
call_id
turn_id
speech_ended_at
audio_started_at
```

### Metricas nuevas

```text
trace_id
run_id
retrieval_id
retrieval_backend
index_version
chunking_version
embedding_provider
embedding_model_name
embedding_dimension
corpus_revision_before
corpus_revision_after
embedding_latency_ms
chroma_latency_ms
fts5_latency_ms
fusion_latency_ms
retrieval_latency_ms
candidate_count
returned_count
cache_hit
fallback_reason
index_lag_seconds
abstention_reason
citation_valid
```

LangSmith recibe solo metadata redactada y no es requisito para probar el benchmark o el fallback.
P50/P95 de voz se publica solo con timestamps reales del navegador. Tokens estimados por fallback
se marcan como estimacion; costo requiere proveedor, modelo, precios, fecha y tokens reales.

## Initial Performance and Quality Gates

Los siguientes valores son targets de aceptacion inicial y deben sustituirse por resultados
fechados, no por intencion:

| Gate | Target |
|---|---:|
| Recall@5 | `>= 0.85` y mejora minima de 5 pp sobre FTS5 |
| Context precision | `>= 0.80` |
| Citation valid rate | `>= 99.5%` |
| disabled/deleted leak | `0` |
| revision mismatch citado | `0` |
| Chroma query P95 caliente | `<= 100 ms` |
| retrieval RAG P95 caliente | `<= 500 ms` |
| regresion de retrieval vs FTS5 | `<= 10%` |
| upload pequeno index ready P95 | `<= 10 s` |
| voz P50/P95 | `<= 2000/4000 ms`, solo browser real |
| triage parity | `100%` frente a reglas baseline |
| prompt injection que cambia mision | `0` |

Un promedio que oculta un dominio, provider o cold start fallido no pasa el gate.

## Rollout and Rollback

1. baseline FTS5 con resultados y latencia;
2. Chroma shadow sin cambiar respuestas;
3. dual-write de mutaciones;
4. canary 5%, 25%, 50% y 100% con ventanas y conteos definidos;
5. promotion solo tras benchmark, reconciliacion, smoke de voz y G5 externo.

Rollback inmediato ante leak, cita invalida, downgrade de triage, grounding inseguro, errores
Chroma >1%, timeout >0.5%, P95 >500 ms, regresion de abstencion/fallback o fuga a LangSmith.
El puntero vuelve a la version anterior o FTS5 en menos de un minuto objetivo y conserva la version
fallida para analisis.

## Code Style

Las fronteras de autoridad se ven en interfaces pequenas:

```python
    triage = services.triage.classify(query, services.call_level)
    candidates = services.rag.retrieve(query, limit=services.settings.top_k)
    evidence = services.rag.validate_revision_and_citations(candidates)
    draft = services.chain.invoke(build_context(query, triage, evidence)) if evidence else None
    return services.agent_validator.finalize(draft, evidence, triage)
```

No se agregan `useMemo`/callbacks de frontend ni abstracciones sin necesidad; el cambio se centra
en contratos de backend, persistencia, evaluacion y observabilidad. Los comentarios explican solo
fronteras no obvias, como la invalidacion SQLite antes de borrar Chroma.

## Testing Strategy

### Unitarias

- configuracion y `.env.example`;
- hash, loader, OCR, chunkers, offsets e IDs;
- providers, dimension, prefijos, normalizacion y cache;
- Chroma adapter, distancia, threshold, orden y manifest;
- filtro `available + enabled`, revision y stale vectors;
- RRF/hybrid, context precision y limites de contexto;
- prompt injection, citas inventadas, dosis/diagnostico y abstencion;
- spans, redaccion, metricas y no-op de LangSmith.

### Integracion

- bootstrap y backfill reproducibles;
- reinicio con Chroma persistente;
- upload/search/disable/enable/delete sin reinicio;
- fallo de cada orden entre SQLite y Chroma;
- reconciliacion, backup/restauracion y rollback;
- benchmark matriz y gates;
- llamadas, resumen, timeout, fuentes, metricas y `source_ids` estables.

### Evidencia manual

- G2: entorno limpio y <=15 minutos siguiendo solo README;
- G3: modelo LLM exacto, familia, provider y log real coherentes;
- G4: microfono, transcript y audio en Chrome/Edge;
- G5: documento externo subido, usado, eliminado y olvidado sin reinicio;
- revision de trazas redacted y dashboard de latencias;
- si se publica fuera de localhost, seguridad, autenticacion, backup y retencion.

La suite local no aprueba gates manuales. Cada resultado conserva fecha, commit, entorno, comando,
artefacto y estado `TESTED`, `MANUAL_PENDING`, `PROPOSED` o `FAILED`.

## Boundaries

- **Always:** conservar FTS5 fallback, SQLite authority, elegibilidad, revision, citas, snapshots
  no consultables, triaje externo al LLM, configuracion versionada, benchmark y evidencia honesta.
- **Ask first:** cambiar modelo/proveedor, exponer Chroma o admin publicamente, agregar OCR,
  cambiar schema persistido, enviar contenido a servicios externos, modificar qrels/targets o
  eliminar fallback.
- **Never:** commitear secretos/modelos/data, mezclar corpus o capas XLSX, citar deleted/disabled,
  aceptar vector stale, usar score como certeza, dejar que el LLM baje alertas, fabricar metricas
  o llamar produccion a un prototipo sin rollback.

## Success Criteria

- **RAG-MIG-AC-01:** la arquitectura target se puede explicar desde upload/transcript hasta cita,
  audio, evento y trace sin nodos ocultos.
- **RAG-MIG-AC-02:** ChromaDB es el vector store configurado para production, con colecciones,
  metadata, manifests y dimension/metrica verificables.
- **RAG-MIG-AC-03:** todos los parametros editables del pipeline aparecen en `.env.example`, se
  validan y se reflejan en `index_version`/manifest.
- **RAG-MIG-AC-04:** existen benchmark de al menos tres chunkers y varias combinaciones de
  provider/modelo con recall, context precision y latencias objetivas.
- **RAG-MIG-AC-05:** el ganador se selecciona por gates de calidad, latencia, memoria y seguridad,
  no por una preferencia no medida.
- **RAG-MIG-AC-06:** LangChain ensambla loader, retriever, contexto y prompt; no controla triaje,
  elegibilidad, citas o seguridad.
- **RAG-MIG-AC-07:** LangSmith puede observar el flujo completo con redaccion y sin bloquear el
  camino, manteniendo eventos locales y `/api/metrics`.
- **RAG-MIG-AC-08:** upload, disable, enable y delete cambian el conocimiento sin reinicio; un
  documento eliminado o disabled no aparece en consultas nuevas y no deja vector citable.
- **RAG-MIG-AC-09:** una carrera de revision o falla de sincronizacion produce abstencion/fallback
  seguro y reconciliacion auditable.
- **RAG-MIG-AC-10:** rollback a indice anterior/FTS5 es ejecutable, probado y no borra evidencia
  historica ni degrada alertas.
- **RAG-MIG-AC-11:** la API conserva `SearchResult`, `sources`, `source_ids`, `corpus_revision`,
  resumen, voz, timeout e idempotencia existentes.
- **RAG-MIG-AC-12:** no se declara G2/G3/G4/G5 por una prueba local; cada gate tiene evidencia
  del tipo que exige la rubrica.

## Trazabilidad

| Requisito | Spec especializada | Fuente/runtime a actualizar | Evidencia |
|---|---|---|---|
| Configuracion y `.env.example` | 13 | `app/config.py`, README | config tests/preflight |
| Chroma y lifecycle | 14 | `rag.py`, `documents.py`, `database.py` | vector/live tests |
| Chunking/embeddings | 15 | `ingestion.py`, scripts benchmark | qrels/resultados |
| LangChain/prompt | 16 | `rag_chain.py`, `prompts.py`, `agent.py` | chain/prompt tests |
| LangSmith/metricas | 17 | `observability.py`, metrics/docs | redaction + traces |
| Rollout/rollback | 18 | index manager, scripts, deployment docs | ops runbook |
| Flujo integrador | 06 revisada | `docs/arquitectura.md`, mvp | diagramas/TRZ |
| Suite | 07 revisada | `tests/`, requirements-dev | pytest/benchmark |
| Gates | rubrica | README/informe/video | evidencia manual |

## Open Questions

1. Confirmar modelo/proveedor de embeddings despues de `RAG-BENCH-001`; BGE-M3 es hipotesis de
   calidad y E5-small hipotesis de latencia, no una seleccion cerrada.
2. Confirmar si el indice Chroma se ejecuta embedded o server en el entorno de evaluacion.
3. Confirmar version exacta de paquetes y politica de cache/modelos para mantener G2.
4. Confirmar qrels, revision de anotaciones y umbrales definitivos por dominio.
5. Confirmar politica de retencion/redaccion de LangSmith y cualquier autorizacion externa.
6. Confirmar estrategia de MIME independiente, OCR y multi-worker antes de declarar production.

## Orden de implementacion

1. Congelar contrato de configuracion y actualizar `.env.example`.
2. Extraer interfaces de loader, embeddings, vector store y `SearchResult` sin cambiar FTS5.
3. Implementar Chroma dual-write y reconciliacion con SQLite authority.
4. Implementar variantes de chunking y providers de embedding detras de config.
5. Crear qrels, runner y benchmark; seleccionar candidato con evidencia.
6. Ensamblar LangChain/prompt y validar seguridad/latencia.
7. Instrumentar spans y LangSmith redacted sin dependencia bloqueante.
8. Ejecutar shadow, canary, G5 y rollback; actualizar diagrama, pruebas, README e informe.

No se implementa una fase posterior si el checkpoint anterior no tiene comando, resultado y estado
explicito. Esta spec sustituye la spec 12 anterior como fuente integradora del RAG.
