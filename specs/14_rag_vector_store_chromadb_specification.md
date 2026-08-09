# Spec: Persistencia vectorial con ChromaDB y contrato de recuperacion

**ID:** `RAG-PROD-001`  
**Estado:** `PROPOSED`; arquitectura objetivo, FTS5 actual sigue operativo  
**Version:** `0.1.0`  
**Fecha:** `2026-08-08`  
**Depende de:** [`13_rag_environment_configuration_specification.md`](13_rag_environment_configuration_specification.md), [`04_admin_document_lifecycle_specification.md`](04_admin_document_lifecycle_specification.md)

## Objective

Introducir ChromaDB como indice vectorial principal del RAG de produccion sin convertirlo en la
autoridad del sistema. SQLite continua siendo la fuente de verdad para documentos, paginas,
chunks originales, `status`, `enabled`, `corpus_revision`, auditoria, snapshots y citas. Chroma
solo acelera la seleccion semantica de candidatos y puede reconstruirse.

La migracion debe soportar:

1. escritura idempotente de vectores con IDs deterministas;
2. colecciones versionadas por chunker, embedding, dimension y metrica;
3. filtro de elegibilidad antes de usar un resultado como evidencia;
4. disable, enable y delete sin reinicio y sin fugas de conocimiento;
5. fallback FTS5 y rollback sin perder el contrato actual de `SearchResult`;
6. lectura rapida para una conversacion de voz y diagnostico de latencias por etapa.

## Supuestos y decisiones

1. `document_id` sigue siendo el SHA-256 de los bytes originales.
2. `chunk_id` sigue siendo determinista y se usa como ID de Chroma, no el nombre del archivo.
3. Un vector almacenado no es una cita. La cita se hidrata desde SQLite despues de verificar el
   estado actual y la revision.
4. La coleccion activa se identifica por un puntero de configuracion/metadata inmutable; cambiar
   el puntero es la unidad de rollout y rollback.
5. `cosine` es la primera metrica. Los embeddings se normalizan cuando el proveedor lo permite y
   el score normalizado se define antes de compararlo con un threshold.
6. El modo embebido requiere un solo worker/proceso escritor. Multiples workers usan un servicio
   Chroma compatible y un volumen persistente; no se promete consistencia distribuida con SQLite.
7. Los snapshots de fuentes historicas nunca se vectorizan.

## Tech Stack

| Componente | Contrato objetivo |
|---|---|
| Vector store | ChromaDB persistente, coleccion por version |
| Fuente de verdad | SQLite existente con FTS5 como baseline/fallback |
| IDs | `chunk_id` determinista y `document_id` como metadata |
| Metadatos vectoriales | documento, pagina, offsets, revision, chunker, embedding, namespace |
| Orquestacion | retriever controlado detras de `RagService` |
| Distancia | cosine inicialmente; no cambiar sin reindexar |
| Escritura | batches idempotentes y reconciliacion auditable |
| Recuperacion | Chroma candidates + filtro SQLite + orden/fusion estable |

No se autoriza exponer objetos Chroma o LangChain por la API publica. El limite externo continua
siendo el `SearchResult` que ya consume `AgentService` y `CallService`.

## Commands

```text
python -m scripts.validate_dataset
python -m app.bootstrap --data-dir <temp>/rag-chroma-bootstrap
python -m scripts.build_rag_index --backend chroma --index-version <version> --data-dir <temp>/rag-chroma
python -m scripts.reconcile_rag_index --index-version <version> --dry-run
python -m pytest tests/test_vector_store.py tests/test_live_knowledge.py -q --basetemp <temp>/rag-chroma
python -m pytest tests/test_admin_lifecycle.py tests/test_database.py -q --basetemp <temp>/rag-lifecycle
python -m pytest tests/test_calls.py tests/test_agent.py -q --basetemp <temp>/rag-contract
```

El preflight debe verificar que la coleccion activa coincide con el manifiesto antes de servir
consultas semanticas. Si no coincide, el proceso inicia en FTS5 o falla de forma explicita segun
el perfil, nunca consulta una coleccion incompatible en silencio.

## Project Structure

```text
app/services/vector_store.py       -> protocolo y adaptador Chroma/FTS5.
app/services/rag.py                -> elegibilidad, fusion, score y SearchResult.
app/services/documents.py          -> dual-write, toggle, delete y reconciliacion.
app/database.py                    -> metadata de indice, revision y estado de sincronizacion.
app/schemas.py                     -> SearchResult y estado seguro de health/API.
scripts/build_rag_index.py         -> backfill reproducible.
scripts/reconcile_rag_index.py     -> detecta ausentes, huerfanos y metadatos invalidos.
tests/test_vector_store.py         -> persistencia, filtros y fallos del backend.
tests/test_rag_consistency.py      -> revision, delete, rollback y paridad FTS5.
```

No se crean copias de los PDF o de los XLSX en la coleccion. El texto necesario para responder
se recupera del chunk original y se limita al contexto del prompt.

## Data Model and Contracts

### Vector metadata minima

Cada registro de Chroma debe contener, como minimo:

```text
id = chunk_id
page_id
page_number
chunk_index
start_char
end_char
filename
sha256
corpus_revision
chunking_version
embedding_provider
embedding_model_name
embedding_model_revision
embedding_dimension
distance_metric
index_version
published = true|false
```

`published` es una ayuda de filtrado, no reemplaza `documents.status` y `documents.enabled` en
SQLite. Metadata con nombres, paths o texto de paciente no se agrega si no es necesaria para
reconstruir el resultado.

### Protocolo interno

```python
class VectorStore(Protocol):
    def upsert(self, records: Sequence[VectorRecord]) -> None: ...
    def query(self, vector: Sequence[float], limit: int, fetch_k: int) -> list[VectorHit]: ...
    def delete_by_document(self, document_id: str) -> None: ...
    def delete_by_ids(self, chunk_ids: Sequence[str]) -> None: ...
    def collection_manifest(self) -> IndexManifest: ...
```

La salida se mapea a:

```text
SearchResult(
  document_id, filename, page_number, chunk_id, chunk_index,
  text, score, citation, corpus_revision
)
```

El texto, filename y citation finales se hidratan desde SQLite por `chunk_id`. Si SQLite ya no
encuentra el chunk, el hit se descarta y se registra `stale_vector`, no se responde con metadata
huérfana.

### Score y orden

Chroma puede devolver distancia. El adaptador debe declarar una conversion determinista, por
ejemplo `similarity = 1 - cosine_distance` cuando la version configurada lo garantice. El score:

- se conserva como relevancia relativa, nunca probabilidad clinica;
- se calibra por modelo y chunker en `RAG-BENCH-001`;
- se compara con `SIMILARITY_THRESHOLD` solo despues de fijar la conversion;
- no se ordena directamente junto a BM25 sin fusion normalizada.

El desempate final es estable por `document_id`, `page_number`, `chunk_index`, `chunk_id`.

## Lifecycle and Consistency

### Upload y bootstrap

1. Validar extension, bytes, hash, extraccion y chunks canonicos.
2. Persistir `documents/pages/chunks` y FTS5 en SQLite como baseline.
3. Generar embeddings fuera de la transaccion larga, con estado `indexing` auditable.
4. Upsert de todos los chunks del documento con `index_version` y metadata completa.
5. Verificar conteo, dimension y manifest.
6. Publicar `available`/`enabled` y actualizar `corpus_revision` solo cuando el contrato de
   disponibilidad se cumpla.
7. Si Chroma falla, mantener el documento fuera del backend semantico y usar FTS5/fallback segun
   perfil; no declarar `index_ready` sin evidencia.

### Disable y enable

- `disable` cambia `enabled=false` y aumenta la revision en SQLite.
- La consulta siempre vuelve a filtrar SQLite; no depende de cache o metadata vieja de Chroma.
- Se puede conservar el vector para habilitar de nuevo sin re-embedding, pero su metadata debe
  estar marcada como no publicada o el filtro autoritativo debe impedir su uso.
- `enable` exige `status=available` y un vector compatible; si falta, queda `index_pending` y no
  entra a respuestas hasta reconciliarse.

### Delete y olvido

1. Bloquear elegibilidad en SQLite e incrementar `corpus_revision`.
2. Capturar snapshots minimos de fuentes de llamadas cerradas.
3. Borrar pages, chunks y FTS5 en la transaccion actual.
4. Eliminar vectores por `document_id` o IDs deterministas y registrar el resultado.
5. Eliminar archivo fisico despues del commit.
6. Revalidar una consulta nueva y confirmar cero hits citables del documento.

No existe una transaccion ACID unica entre SQLite y Chroma. La seguridad se consigue con el filtro
autoritario de SQLite, un estado de sincronizacion, una cola/reconciliacion auditable y pruebas de
fallo en ambos ordenes. Un vector huerfano no puede convertirse en evidencia.

### Reconciliacion

El reconciliador compara SQLite contra la coleccion activa y reporta:

- chunks disponibles sin vector;
- vectores sin chunk autoritativo;
- dimension/modelo/metrica/version incorrectos;
- documentos deshabilitados o eliminados aun recuperables;
- conteos y hashes de manifest divergentes.

La reparacion es explicita, idempotente y no borra snapshots. Un indice `stale` no se promueve.

## Code Style

La logica de elegibilidad y seguridad vive fuera de Chroma. El adaptador solo traduce vectores y
distancias; `RagService` decide si un resultado puede ser evidencia.

```python
def hydrate_active_hits(db: Database, hits: list[VectorHit]) -> list[SearchResult]:
    results = []
    for hit in stable_sort(hits):
        row = db.get_eligible_chunk(hit.chunk_id)
        if row is None:
            metrics.record("stale_vector", document_id=hit.document_id)
            continue
        results.append(to_search_result(row, score=hit.similarity))
    return results
```

No se aceptan filtros Chroma construidos concatenando texto del paciente. El query del paciente
solo produce un vector y parametros validados por la aplicacion.

## Testing Strategy

### Unitarias

- IDs y metadata deterministas;
- conversion de distancia a score y threshold;
- orden estable y deduplicacion;
- filtros de `status`, `enabled`, `index_version` y revision;
- dimension incorrecta y manifest incompatible;
- fallo de upsert, query y delete;
- vector huerfano descartado;
- snapshots no consultables;
- paridad del DTO con FTS5.

### Integracion

- persistencia Chroma despues de reiniciar proceso;
- bootstrap e indexacion idempotentes;
- upload -> search -> disable -> abstencion -> enable -> search;
- upload -> search -> delete -> cero hits sin reinicio;
- fallo entre commit SQLite y delete vectorial, seguido de reconciliacion;
- coleccion activa anterior tras rollback;
- consulta concurrente durante toggle/delete no devuelve fuente obsoleta;
- fallback FTS5 ante timeout o backend no disponible.

### Performance y evidencia manual

- P50/P95 de embedding de query, query Chroma, hidratacion, fusion y RAG completo;
- cold start separado de modelo caliente;
- memoria y tiempo de rebuild del corpus local;
- smoke de `/admin` y `/call` con conocimiento vivo externo para G5;
- no declarar produccion por un test con un Chroma falso.

## Boundaries

- **Always:** SQLite autoriza, Chroma indexa, IDs son deterministas, colecciones son versionadas,
  delete es verificable, FTS5 permite rollback y toda cita se hidrata desde el chunk original.
- **Ask first:** cambiar la autoridad de SQLite, usar Chroma server publico, agregar multi-worker,
  introducir una transaccion distribuida, cambiar metrica o eliminar FTS5.
- **Never:** citar metadata huérfana, consultar snapshots, mezclar dimensiones, filtrar solo por
  cache, borrar el indice anterior antes de validar el nuevo o presentar distancia como certeza.

## Success Criteria

- **VECTOR-AC-01:** ChromaDB persiste en la ruta configurada y sobrevive reinicio en el perfil
  correspondiente.
- **VECTOR-AC-02:** cada vector tiene ID, metadata, modelo, dimension, metrica y version de indice
  compatibles con el manifest.
- **VECTOR-AC-03:** `RagService` conserva el `SearchResult` existente y las citas provienen de
  SQLite, no de texto no validado devuelto por Chroma.
- **VECTOR-AC-04:** `available AND enabled=true` se verifica antes de retornar cualquier resultado.
- **VECTOR-AC-05:** disable excluye sin re-embedding; enable recupera solo con vector compatible;
  delete elimina conocimiento nuevo en caliente aunque la limpieza vectorial falle temporalmente.
- **VECTOR-AC-06:** un vector huerfano, stale o de otra version nunca llega al prompt.
- **VECTOR-AC-07:** FTS5 es fallback y rollback probado, no una ruta eliminada durante el canary.
- **VECTOR-AC-08:** reconciliacion detecta y repara divergencias sin modificar `dataset/` o `docs/`.
- **VECTOR-AC-09:** la latencia de Chroma y del RAG completo queda separada en metricas y tiene
  presupuesto configurable.

## Trazabilidad

| Requisito | Contrato | Verificacion |
|---|---|---|
| Persistencia vectorial | `VectorStore`, manifest y path | `test_vector_store.py` |
| Conocimiento vivo | upload/disable/enable/delete | `test_rag_consistency.py`, G5 manual |
| Seguridad de citas | hydration SQLite y revision | `test_agent.py`, `test_calls.py` |
| Baja latencia | spans y budgets | benchmark de Spec 15 |
| Rollback | puntero de coleccion + FTS5 | pruebas de operaciones |

## Open Questions

1. Confirmar version exacta de ChromaDB y si el entorno objetivo admite persistencia embebida sin
   multiples workers.
2. Confirmar si los toggles deben conservar vectores o marcarlos como no publicados y rehidratar
   al habilitar.
3. Definir la cola de reconciliacion: proceso local, job externo o comando operativo manual.
4. Confirmar backup/restauracion del directorio Chroma junto con SQLite y uploads.
