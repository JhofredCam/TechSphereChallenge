# Spec: Operacion, rollout y rollback del RAG en produccion

**ID:** `RAG-OPS-001`  
**Estado:** `PROPOSED`; runbook objetivo, sin despliegue real en este checkout  
**Version:** `0.1.0`  
**Fecha:** `2026-08-08`  
**Depende de:** [`14_rag_vector_store_chromadb_specification.md`](14_rag_vector_store_chromadb_specification.md), [`15_rag_chunking_embedding_benchmark_specification.md`](15_rag_chunking_embedding_benchmark_specification.md), [`17_rag_observability_langsmith_specification.md`](17_rag_observability_langsmith_specification.md)

## Objective

Definir como se construye, publica, monitorea, repara y revierte un indice RAG versionado sin
interrumpir una llamada de voz ni perder las garantias de conocimiento vivo, citas, revision,
delete y fallback.

La operacion debe ser segura para un monolito local y extensible a un despliegue con Chroma server:

```text
manifest -> build shadow -> validate -> dual-write -> canary -> promote
                                      |                    |
                                      +---- rollback <-----+
```

La implementacion debe conservar el modo `challenge-local` levantable en 15 minutos. Un modelo
pesado o un servicio externo no puede ser una descarga oculta que rompa G2.

## Supuestos y decisiones

1. El indice es inmutable despues de validado; cambios de chunking/embedding/metrica crean otro
   `index_version`.
2. SQLite y el indice vectorial tienen consistencia eventual operada por estados y reconciliacion,
   pero SQLite autoriza toda evidencia inmediatamente.
3. El puntero activo se puede mover a la version anterior o a FTS5 sin borrar el candidato nuevo.
4. El rollback es una decision operacional, no una mutacion clinica del historial: fuentes ya
   citadas permanecen historicas y no vuelven a ser evidencia nueva si fueron eliminadas.
5. La aplicacion se ejecuta con un solo worker en Chroma embedded. Multiples workers requieren
   Chroma server, almacenamiento persistente, autenticacion, TLS y pruebas de concurrencia.
6. No se declara production publico sin autenticacion admin, MIME independiente, control de acceso,
   backup, retencion y un canal de incidentes aprobados.

## Tech Stack

| Area | Contrato |
|---|---|
| Runtime | FastAPI/Uvicorn actual |
| State authority | SQLite + uploads + events |
| Vector index | ChromaDB versionado |
| Baseline | FTS5 para fallback/rollback |
| Job operations | CLI idempotente y reconciliador |
| Observability | eventos locales + LangSmith opcional |
| Deployment | perfil local embedded o server con volumen |
| Secrets | entorno/secret manager, nunca Git |

## Commands

### Preflight y build

```text
python -m scripts.validate_dataset
python -m scripts.check_rag_config --profile staging --show-effective --redact-secrets
python -m app.bootstrap --data-dir <temp>/rag-ops-bootstrap
python -m scripts.build_rag_index --index-version <new-version> --profile staging --data-dir <temp>/rag-ops-index
python -m scripts.validate_rag_index --index-version <new-version> --strict
python -m scripts.reconcile_rag_index --index-version <new-version> --dry-run
```

### Pruebas antes de promover

```text
python -m pytest tests/test_vector_store.py tests/test_rag_consistency.py -q --basetemp <temp>/rag-ops-vector
python -m pytest tests/test_live_knowledge.py tests/test_admin_lifecycle.py -q --basetemp <temp>/rag-ops-live
python -m pytest tests/test_agent.py tests/test_calls.py tests/test_metrics.py -q --basetemp <temp>/rag-ops-agent
python -m scripts.benchmark_rag --matrix configs/rag_benchmark.yaml --gate --output <temp>/rag-ops-bench.json
ruff check .
git diff --check
```

### Rollback

```text
python -m scripts.promote_rag_index --index-version <previous-version> --reason <incident-code>
python -m scripts.reconcile_rag_index --index-version <previous-version> --strict
python -m scripts.rag_status --json --redact-secrets
```

Cada comando debe registrar actor, commit, version anterior/nueva, razon, resultado y trace de
operacion. No se borran versiones anteriores con un comando de rollback.

## Project Structure

```text
scripts/build_rag_index.py          -> construye indice inmutable.
scripts/validate_rag_index.py       -> valida manifest, conteos y qrels de smoke.
scripts/reconcile_rag_index.py      -> compara SQLite y Chroma.
scripts/promote_rag_index.py        -> mueve puntero activo con lock.
scripts/rag_status.py               -> estado seguro de operacion.
app/services/index_manager.py       -> estados, locks, dual-write y puntero.
app/services/documents.py           -> lifecycle admin y eventos de index.
app/database.py                     -> metadata, auditoria, revision y outbox.
tests/test_rag_operations.py        -> rollout, rollback, fallo y reconciliacion.
readme/02_setup_local.md            -> perfiles y setup sin descargas ocultas.
readme/03_demo_funcional.md         -> G5 con upload/delete y estado vectorial.
```

## Index Manifest and State

Cada version debe tener un manifest firmado o hash verificable con:

```text
index_version
created_at
corpus_snapshot_hash
corpus_revision_start
corpus_revision_end
document_count
chunk_count
chunking_version
chunk_size
chunk_overlap
splitter_type
embedding_provider
embedding_model_name
embedding_model_revision
embedding_dimension
embedding_normalize
distance_metric
collection_name
package_versions
hardware_profile
build_command
```

Estados operativos:

| Estado | Puede responder | Accion |
|---|---:|---|
| `building` | no | construir fuera del puntero activo |
| `validating` | no | ejecutar checks y benchmark |
| `shadow` | no como respuesta | observar desacuerdos |
| `canary` | porcentaje controlado | vigilar gates |
| `active` | si | version oficial |
| `degraded` | fallback | incidentar y reconciliar |
| `rolled_back` | no | conservar para analisis |
| `failed` | no | no promover |

El estado del indice no sustituye `documents.status` ni `enabled`. Un documento `available` puede
estar `index_pending`; solo el backend listo/fallback autorizado puede usarlo.

## Rollout Plan

1. **Baseline:** medir FTS5 y guardar manifest de comportamiento, latencia y seguridad.
2. **Shadow:** consultar Chroma sin alterar la respuesta; comparar hits, citas y latencia.
3. **Dual-write:** mantener FTS5 y Chroma sincronizados en upload, enable, disable y delete.
4. **Canary 5%:** al menos 100 llamadas o 24 horas, lo que sea mas exigente.
5. **Canary 25%:** al menos 500 llamadas sin P0.
6. **Canary 50%:** al menos 1000 llamadas y revision de metricas.
7. **100%:** solo despues de revisar benchmark, smoke de voz, G5 externo y rollback probado.

El porcentaje se asigna fuera de las reglas de triage y no debe cambiar el nivel por paciente. La
respuesta conserva `retrieval_backend`, `index_version`, `source_ids` y `reason`.

## Rollback and Incident Rules

Rollback inmediato ante cualquiera de estos eventos:

- fuga de documento eliminado o disabled;
- cita no existente o revision obsoleta usada como evidencia;
- rojo/amarillo degradado o timeout convertido en verde;
- respuesta clinica sin grounding cuando la ruta lo exige;
- Chroma con error mayor al 1% durante cinco minutos;
- timeout RAG mayor al 0.5% o P95 mayor a 500 ms;
- incremento de abstencion/fallback mayor a 5 puntos porcentuales frente a baseline;
- LangSmith recibe contenido no permitido;
- corrupcion, dimension o manifest incompatibles.

El rollback:

1. congela la promocion y conserva eventos;
2. cambia el puntero a la version anterior o `fts5`;
3. verifica `health`, elegibilidad, fuentes y una pregunta marcador;
4. reconcilia en modo solo lectura;
5. abre un incidente con commit, configuracion redacted, trazas y metricas;
6. no borra la version fallida hasta completar analisis.

Target operativo inicial: menos de un minuto para cambiar el puntero, sin reiniciar llamadas
activas. Si el backend embebido no permite ese target, se documenta y se usa fallback por request.

## Backup and Recovery

El plan debe cubrir conjuntamente:

- SQLite y su schema version;
- directorio Chroma y manifest;
- uploads originales;
- `events.jsonl` y auditoria;
- puntero de coleccion activa;
- versiones de modelos y cache local si se permiten.

Se prueba restauracion en un directorio temporal, se verifica hash/conteo, se ejecuta una consulta
con cita y se confirma que snapshots no vuelven a ser fuentes. Los backups no se commitean.

## Security and Deployment

- bind local `127.0.0.1` en perfil challenge;
- Chroma server solo con autenticacion, TLS, ACL y volumen persistente;
- autenticacion/autorizacion admin antes de exposicion publica;
- validacion MIME real, limite de paginas/texto, parser aislado y proteccion de paths;
- cifrado de volumen o politica equivalente para SQLite, Chroma y uploads;
- no enviar corpus/transcripts a embeddings remotos por default;
- LangSmith redactado y retencion limitada;
- no usar datos sinteticos como validacion clinica;
- un solo worker en embedded y prueba explicita de locks;
- health/readiness distingue `active`, `degraded`, `index_pending` y `fallback`.

## Code Style

Las operaciones de indice deben ser idempotentes y auditables:

```python
def promote(index: IndexManifest, state: IndexState, reason: str) -> None:
    validate_manifest(index)
    with state.lock():
        previous = state.active_version()
        state.set_active(index.index_version)
        audit("rag_promote", previous=previous, current=index.index_version, reason=reason)
```

El puntero no se cambia si la validacion falla. El lock no se usa para ocultar trabajo largo de
embedding; los builds ocurren fuera de la ruta de voz.

## Testing Strategy

### Unitarias

- manifest completo e incompatibilidades;
- maquina de estados y transiciones permitidas;
- puntero atomico y razon de promotion/rollback;
- backoff, lock y operaciones idempotentes;
- thresholds P0 y calculo de deltas;
- redaccion de comandos, paths y configuracion.

### Integracion

- build -> validate -> shadow -> canary -> active;
- rollback a version previa y FTS5 sin perder contrato;
- dual-write de upload/toggle/delete;
- fallo de Chroma despues de commit SQLite y reconciliacion;
- reinicio con volumen persistente;
- restauracion de backup;
- dos procesos no escriben embedded simultaneamente;
- G5 externo con delete sin reinicio;
- `/health` y `/api/metrics` reflejan estado y lag.

### Manual

- cronometraje G2 desde entorno limpio;
- smoke G4 en Chrome y Edge con microfono, transcripcion y audio;
- G5 con documento que no pertenece al corpus;
- revisar rollback durante una llamada de prueba;
- verificar permisos, autenticacion y retencion si se sale de localhost.

## Boundaries

- **Always:** promover indices inmutables, probar rollback, mantener FTS5, auditar cambios,
  reconciliar, separar builds de voz y marcar evidencia como local/manual.
- **Ask first:** despliegue publico, multiples workers, Chroma server externo, autenticacion
  empresarial, backup cifrado gestionado, cambiar SLOs o eliminar fallback.
- **Never:** promover sin benchmark, borrar la version anterior primero, afirmar G2/G4/G5 con
  mocks, dejar un vector stale citable, commitear modelos/secretos/datos generados.

## Success Criteria

- **OPS-AC-01:** cada indice se construye con manifest completo, version inmutable y validacion
  antes de promocion.
- **OPS-AC-02:** shadow, dual-write, canary y rollback estan definidos con comandos y umbrales.
- **OPS-AC-03:** rollback cambia a una version sana o FTS5 sin romper API, fuentes, triaje o
  llamadas activas.
- **OPS-AC-04:** fallos entre SQLite y Chroma no permiten fugas y son detectables por reconciliacion.
- **OPS-AC-05:** el perfil local conserva setup sin red/descargas ocultas y el objetivo G2 puede
  medirse desde entorno limpio.
- **OPS-AC-06:** backup/restauracion recupera SQLite, Chroma, manifest, uploads y eventos sin
  reintroducir snapshots.
- **OPS-AC-07:** los SLOs de latencia, error, lag, fuga, citas y fallback generan una decision
  operacional documentada.
- **OPS-AC-08:** no se declara production publico sin controles de seguridad y evidencia manual.

## Trazabilidad

| Requisito | Evidencia | Gate |
|---|---|---|
| Rollout seguro | manifests, canary y rollback | criterio repositorio |
| Baja latencia | SLOs y voz real | G4 |
| Aprender/olvidar | dual-write y G5 externo | G5 |
| Reproducibilidad | setup, perfiles y backups | G2 |
| Modelo | informe y allowlist | G3 |

## Open Questions

1. Confirmar la plataforma de despliegue y si se requiere Chroma server en vez de embedded.
2. Confirmar el volumen, frecuencia y responsable de backups.
3. Confirmar la herramienta de lock/outbox para mas de un proceso.
4. Confirmar quien aprueba la promocion y que ventana de observacion se exige.
5. Confirmar si el target de rollback menor a un minuto es realista en el entorno evaluado.
