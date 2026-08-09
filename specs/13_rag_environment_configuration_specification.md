# Spec: Configuracion externa del pipeline RAG

**ID:** `RAG-ENV-001`  
**Estado:** `PROPOSED`; contrato de migracion, aun no aplicado al runtime  
**Version:** `0.1.0`  
**Fecha:** `2026-08-08`  
**Depende de:** [`00_mvp_specification.md`](00_mvp_specification.md), [`04_admin_document_lifecycle_specification.md`](04_admin_document_lifecycle_specification.md)

## Objective

Definir una unica superficie de configuracion externa para todos los parametros editables de
ingestion, chunking, embeddings, vector store, retrieval, orquestacion y observabilidad. El
pipeline no debe esconder hiperparametros en `rag.py`, en un constructor de servicio o en una
constante que obligue a cambiar codigo para experimentar.

El contrato debe permitir tres perfiles sin duplicar logica:

1. `challenge-local`: FTS5, sin descarga de modelos y sin credenciales.
2. `staging`: ChromaDB y embeddings locales precargados, con benchmark y trazas redactadas.
3. `production`: indice versionado, dual-read o canary, fallback FTS5, secretos gestionados y
   un backend Chroma compatible con el numero de workers.

El exito no es que todas las variables tengan valores optimos desde el primer dia. El exito es
que cada valor sea explicito, validado, observable sin secretos y reproducible en un manifiesto
de indice.

### Supuestos que se hacen explicitos

1. La configuracion de entorno tiene precedencia sobre defaults de codigo, pero nunca sobre una
   politica de seguridad fija, como no usar snapshots como evidencia.
2. Los nombres canonicos nuevos son los nombres sin prefijo de proveedor solicitados por el reto
   (`CHUNK_SIZE`, `EMBEDDING_MODEL_NAME`, `TOP_K`, etc.). Los nombres `APP_*` existentes solo se
   mantienen durante la migracion cuando ya forman parte de un contrato persistido o probado.
3. Los secretos se leen del entorno o de un secret manager; `.env.example` solo contiene nombres,
   defaults seguros y marcadores sin valor real.
4. Un cambio de chunker, embedding, dimension, metrica o normalizacion crea una nueva version de
   indice y no muta silenciosamente una coleccion existente.
5. El modelo de razonamiento sigue siendo `llama-3.1-8b-instant` via Groq, familia Meta Llama
   permitida, salvo una decision posterior documentada dentro de la misma familia permitida.
6. El corpus local, el dataset y `docs/` no se copian ni se descargan como parte de la
   configuracion.

## Tech Stack

| Area | Seleccion objetivo | Regla |
|---|---|---|
| Configuracion | `app/config.py` y parser tipado existente | validacion fail-fast, sin side effects |
| Vector store | ChromaDB persistente | `VECTOR_STORE_TYPE=chroma` en perfiles no-baseline |
| Orquestacion | `langchain-core` y adaptadores pequenos | no usar agentes autonomos |
| Embeddings | proveedor local configurable | el ganador lo decide `RAG-BENCH-001` |
| Observabilidad | LangChain callbacks + LangSmith opcional | nunca bloquea una respuesta segura |
| Modelo LLM | Meta Llama via Groq | solo familias de `docs/stack-tecnico.md` |
| Persistencia de autoridad | SQLite existente | documentos, elegibilidad, revision y citas |

Las versiones exactas de ChromaDB, `langchain-core`, integracion Chroma y proveedor de embeddings
se fijaran en `requirements.txt` solo durante la implementacion. Esta spec no autoriza agregar
dependencias sin actualizar el plan, la prueba de setup y el informe.

## Commands

Los comandos siguientes son el contrato previsto. Los scripts de migracion aun no existen y no se
deben presentar como ejecutados:

```text
python -m pytest tests/test_config_contracts.py -q --basetemp <temp>/rag-config
python -m pytest tests/test_ingestion.py tests/test_live_knowledge.py -q --basetemp <temp>/rag-config-rag
python -m scripts.validate_dataset
python -m app.bootstrap --data-dir <temp>/rag-config-bootstrap
python -m scripts.build_rag_index --profile challenge-local --data-dir <temp>/rag-index
python -m scripts.check_rag_config --profile staging
ruff check .
git diff --check
```

Para inspeccionar la configuracion efectiva sin exponer secretos:

```text
python -m scripts.check_rag_config --show-effective --redact-secrets
```

El comando debe fallar si una variable invalida se combina con un backend que la requiere, pero
debe permitir el perfil local que no necesita un modelo de embedding.

## Project Structure

```text
app/config.py                         -> Settings tipado y validacion de entorno.
app/services/rag.py                   -> consume una configuracion ya validada.
app/services/ingestion.py             -> consume el perfil de chunking versionado.
app/services/vector_store.py          -> adaptador Chroma/FTS5 segun configuracion.
app/services/embeddings.py            -> proveedor, modelo, cache y limites.
scripts/check_rag_config.py           -> preflight sin secretos.
scripts/build_rag_index.py            -> manifiesto e indice reproducible.
tests/test_config_contracts.py        -> defaults, rangos, perfiles y secretos.
.env.example                           -> nombres y defaults no secretos.
tasks/plan.md                          -> orden de implementacion y checkpoints.
```

`data/` continua siendo estado local ignorado por Git. La ruta de Chroma se deriva de
`APP_DATA_DIR` cuando se usa el modo embebido y nunca se escribe dentro de `dataset/`, `docs/` o
el arbol de codigo.

## Variables de entorno

### Base y perfil

| Variable | Default | Validacion / uso |
|---|---:|---|
| `APP_DATA_DIR` | `data` | ruta local de estado |
| `RAG_PROFILE` | `challenge-local` | `challenge-local`, `staging` o `production` |
| `RAG_BACKEND` | `fts5` | `fts5`, `chroma`, `hybrid` |
| `RAG_SHADOW_BACKEND` | `none` | backend que se consulta sin cambiar respuesta |
| `RAG_FALLBACK_TO_FTS5` | `true` | obligatorio en canary y production |
| `RAG_INDEX_VERSION` | `baseline-fts5-v1` | identificador inmutable de indice |
| `RAG_CONFIG_VERSION` | `1` | version del contrato de configuracion |

### Chunking

| Variable | Default | Validacion / uso |
|---|---:|---|
| `SPLITTER_TYPE` | `recursive_es_v2` | `character`, `recursive_es_v2`, `structure_es_v1` |
| `CHUNK_SIZE` | `1200` | unidad definida por `CHUNK_UNIT`; mayor que overlap |
| `CHUNK_OVERLAP` | `200` | entero no negativo, menor que `CHUNK_SIZE` |
| `CHUNK_UNIT` | `characters` | `characters` o `tokens` |
| `CHUNK_MIN_SIZE` | `80` | evita fragmentos triviales |
| `CHUNK_MAX_SIZE` | `1600` | limite duro por pagina |
| `CHUNK_SEPARATORS` | `heading,paragraph,sentence,space` | lista segura, sin codigo ejecutable |
| `CHUNK_PRESERVE_PAGE_BOUNDARIES` | `true` | no cruzar paginas del PDF |
| `CHUNK_NORMALIZE_WHITESPACE` | `true` | versionar si cambia offsets |
| `CHUNKING_VERSION` | `recursive_es_v2` | parte de la identidad del indice |

El baseline actual `APP_CHUNK_SIZE=1200` y `APP_CHUNK_OVERLAP=200` se mapea de forma explicita
durante la migracion. No se deben aceptar dos valores efectivos distintos para el mismo proceso.

### Embeddings

| Variable | Default | Validacion / uso |
|---|---:|---|
| `EMBEDDING_PROVIDER` | `none` | `none`, `sentence_transformers`, `fastembed`, `http` |
| `EMBEDDING_MODEL_NAME` | `BAAI/bge-m3` | nombre visible en el manifiesto |
| `EMBEDDING_MODEL_REVISION` | `unset` | revision o digest obligatorio fuera de local |
| `EMBEDDING_DIMENSION` | `1024` | debe coincidir con el modelo real |
| `EMBEDDING_DEVICE` | `cpu` | `cpu` por defecto; GPU requiere evidencia de despliegue |
| `EMBEDDING_BATCH_SIZE` | `16` | entero positivo y limitado por memoria |
| `EMBEDDING_MAX_LENGTH` | `512` | limite de tokens del proveedor |
| `EMBEDDING_NORMALIZE` | `true` | obligatorio al usar cosine comparable |
| `EMBEDDING_QUERY_PREFIX` | `` | `query:` para modelos E5 cuando corresponda |
| `EMBEDDING_DOCUMENT_PREFIX` | `` | `passage:` para modelos E5 cuando corresponda |
| `EMBEDDING_ALLOW_DOWNLOAD` | `false` | nunca descargar durante bootstrap de evaluacion |
| `EMBEDDING_CACHE_DIR` | `data/models` | ruta fuera de fuentes canonicas |
| `EMBEDDING_TIMEOUT_MS` | `350` | presupuesto de consulta, no ingestion completa |
| `EMBEDDING_ENDPOINT` | `` | requerido solo para provider `http`, HTTPS fuera de local |
| `EMBEDDING_API_KEY` | `` | secreto; nunca se imprime ni se commitea |

`EMBEDDING_PROVIDER=http` requiere un endpoint y credencial separados, pero no es el default. El
corpus clinico y los transcripts no se envian a un proveedor remoto de embeddings sin aprobacion,
redaccion y prueba de privacidad.

### Vector store y metrica

| Variable | Default | Validacion / uso |
|---|---:|---|
| `VECTOR_STORE_TYPE` | `chroma` | `chroma` como destino de produccion; `fts5` solo baseline |
| `VECTOR_STORE_MODE` | `embedded` | `embedded` o `server` |
| `VECTOR_STORE_PATH` | `${APP_DATA_DIR}/chroma` | ruta persistente embebida |
| `VECTOR_STORE_HOST` | `127.0.0.1` | solo modo server; no publicar por defecto |
| `VECTOR_STORE_PORT` | `8001` | entero valido |
| `COLLECTION_NAME` | `techsphere_rag` | nombre estable sin texto de paciente |
| `COLLECTION_PREFIX` | `clinical_es` | parte del nombre versionado |
| `DISTANCE_METRIC` | `cosine` | primera metrica evaluada; no mezclar colecciones |
| `VECTOR_SPACE_VERSION` | `cosine-v1` | cambia cuando cambia normalizacion/metrica |
| `VECTOR_UPSERT_BATCH_SIZE` | `64` | limite de escritura |
| `VECTOR_QUERY_TIMEOUT_MS` | `100` | timeout del acceso Chroma |
| `VECTOR_DELETE_TIMEOUT_MS` | `1000` | limpieza asincrona solo con auditoria |
| `VECTOR_STORE_TLS` | `false` | obligatorio en modo server fuera de localhost |
| `VECTOR_STORE_AUTH_TOKEN` | `` | secreto requerido por Chroma server protegido |

### Timeouts de proveedores existentes

Estos valores se separan de la escucha del paciente y de los budgets RAG:

| Variable | Default | Uso |
|---|---:|---|
| `GROQ_CHAT_TIMEOUT_MS` | `12000` | timeout del LLM de razonamiento |
| `GROQ_WHISPER_TIMEOUT_MS` | `30000` | timeout de STT remoto |
| `GROQ_WHISPER_URL` | URL oficial de Groq | endpoint configurable sin incluir credenciales |
| `SQLITE_BUSY_TIMEOUT_MS` | `5000` | espera de lock SQLite |

### Recuperacion y contexto

| Variable | Default | Validacion / uso |
|---|---:|---|
| `TOP_K` | `5` | resultados finales entregados al contrato RAG |
| `VECTOR_TOP_K` | `8` | candidatos Chroma |
| `VECTOR_FETCH_K` | `32` | margen para filtrar elegibilidad |
| `LEXICAL_TOP_K` | `8` | candidatos FTS5 |
| `SIMILARITY_THRESHOLD` | `0.35` | score normalizado, calibrado por benchmark |
| `RAG_RRF_K` | `60` | constante de Reciprocal Rank Fusion |
| `RAG_CONTEXT_MAX_TOKENS` | `1800` | limite antes del prompt |
| `RAG_MAX_CHUNKS_TO_PROMPT` | `4` | acota latencia y superficie de ataque |
| `RAG_QUERY_TIMEOUT_MS` | `500` | presupuesto total de retrieval |
| `RAG_RETRY_COUNT` | `0` | no reintentar en vivo sin presupuesto explicito |
| `RAG_CACHE_QUERY_TTL_SECONDS` | `600` | cache solo de embedding de consulta, nunca de elegibilidad |
| `RAG_CACHE_QUERY_MAX_ENTRIES` | `1024` | limite de memoria |

El `SIMILARITY_THRESHOLD` no se interpreta como probabilidad clinica. El benchmark debe calibrarlo
por perfil de chunker y embedding; una configuracion que no puede distinguir falta de evidencia
debe abstenerse.

### Observabilidad y trazabilidad

| Variable | Default | Regla |
|---|---:|---|
| `LANGCHAIN_TRACING_V2` | `false` | habilitar solo con redaccion en staging/production |
| `LANGCHAIN_API_KEY` | `` | secreto, nunca commitear ni devolver por `/health` |
| `LANGCHAIN_PROJECT` | `techsphere-rag` | nombre no clinico |
| `LANGCHAIN_ENDPOINT` | `https://api.smith.langchain.com` | configurable, validar HTTPS |
| `LANGSMITH_SAMPLE_RATE` | `0.10` | entre `0` y `1` |
| `LANGSMITH_CAPTURE_CONTENT` | `false` | default seguro, no guardar transcripts/chunks |
| `LANGSMITH_REDACT_PII` | `true` | obligatorio fuera de desarrollo local |
| `LANGSMITH_TRACE_RETENTION_DAYS` | `7` | politica de retencion documentada |
| `OBSERVABILITY_ENV` | `local` | `local`, `staging`, `production` |
| `TRACE_LATENCY_BUDGET_MS` | `20` | tracing no bloquea el camino principal |

Estas variables conviven con `GROQ_API_KEY`, `GROQ_MODEL`, `GROQ_WHISPER_MODEL` y
`PATIENT_LISTEN_TIMEOUT_MS`. Los timeouts de voz, Groq, Whisper, SQLite, Chroma y embeddings son
independientes y se reportan por separado.

## Code Style

La configuracion se parsea una vez al construir el servicio, se valida antes de abrir Chroma y se
inyecta en las dependencias. No se llama `os.getenv()` disperso en cada consulta.

```python
def build_rag_settings(env: Mapping[str, str]) -> RagSettings:
    settings = RagSettings(
        backend=parse_choice(env.get("RAG_BACKEND", "fts5"), {"fts5", "chroma", "hybrid"}),
        top_k=parse_positive_int(env.get("TOP_K", "5")),
        similarity_threshold=parse_float(env.get("SIMILARITY_THRESHOLD", "0.35")),
        embedding_model=env.get("EMBEDDING_MODEL_NAME", "BAAI/bge-m3"),
    )
    validate_cross_field_rules(settings)
    return settings
```

Los nombres de variables, perfiles y valores efectivos se registran en un manifiesto sin secretos.
Las rutas se normalizan con `pathlib`; no se crean directorios al solo parsear configuracion.

## Testing Strategy

### Unitarias

- defaults del perfil `challenge-local` y mapeo de `APP_CHUNK_*` durante la transicion;
- enteros, floats, booleanos, listas y rutas invalidas;
- `CHUNK_OVERLAP < CHUNK_SIZE` y limites de memoria;
- dimension, prefijos y revision de embedding coherentes;
- `DISTANCE_METRIC=cosine` y `EMBEDDING_NORMALIZE=true` como pareja valida;
- `TOP_K`, `VECTOR_FETCH_K`, threshold y timeouts dentro de rangos seguros;
- prohibicion de `LANGSMITH_CAPTURE_CONTENT=true` en production sin flag de aprobacion;
- redaccion de `LANGCHAIN_API_KEY` y endpoints secretos en el dump efectivo.

### Integracion

- `RAG_BACKEND=fts5` conserva la suite baseline sin red;
- el perfil Chroma falla con mensaje accionable si falta el modelo local o la coleccion;
- el perfil staging crea el directorio derivado de `APP_DATA_DIR`, nunca `dataset/`;
- `/health` expone backend, version, dimension y metrica, pero no claves, rutas absolutas ni
  texto clinico;
- cambiar una variable de chunker/embedding cambia `RAG_INDEX_VERSION` requerido y bloquea un
  arranque con coleccion incompatible.

### Evidencia manual

- levantar `challenge-local` desde entorno limpio en menos de 15 minutos;
- levantar `staging` con modelos precargados sin descarga accidental;
- comprobar que LangSmith no recibe contenido cuando la captura esta desactivada.

## Boundaries

- **Always:** validar toda variable, registrar configuracion no secreta, versionar el indice,
  separar timeouts, mantener FTS5 como fallback y no crear side effects al parsear.
- **Ask first:** cambiar nombres canonicos, cambiar defaults que afectan recall/latencia, permitir
  descargas en bootstrap, agregar un proveedor remoto de embeddings o cambiar retencion de trazas.
- **Never:** commitear `LANGCHAIN_API_KEY`, imprimir secretos, aceptar un threshold como certeza
  clinica, mezclar colecciones con distinta dimension o leer `.env` como autoridad clinica.

## Success Criteria

- **ENV-AC-01:** cada parametro editable de chunking, embeddings, vector store, retrieval y
  observabilidad aparece en `.env.example` con default o marcador seguro.
- **ENV-AC-02:** un parser tipado rechaza valores invalidos y errores de compatibilidad entre
  variables antes de abrir el indice.
- **ENV-AC-03:** el valor efectivo se puede inspeccionar con secretos redacted y contiene perfil,
  version de indice, chunker, modelo, dimension y metrica.
- **ENV-AC-04:** los defaults de `challenge-local` mantienen pruebas y bootstrap sin red ni modelo
  descargado.
- **ENV-AC-05:** un cambio que altera IDs, vectores o ranking exige una nueva version de indice y
  no permite mezclar embeddings incompatibles.
- **ENV-AC-06:** `/health` publica solo estado operacional seguro y nunca API keys, rutas absolutas,
  prompts, transcripts o chunks.
- **ENV-AC-07:** los timeouts de paciente, LLM, STT, embedding, Chroma y retrieval tienen nombres,
  limites y metricas separados.

## Trazabilidad

| Requisito | Evidencia | Gate relacionado |
|---|---|---|
| Configuracion externa | `.env.example`, parser y dump redacted | G2, criterio repositorio |
| Baja latencia | budgets de embedding/query/RAG y benchmark | calidad de voz |
| Modelo permitido | `GROQ_MODEL`, allowlist y informe | G3 |
| Conocimiento vivo | backend, version y fallback declarados | G5 |
| Observabilidad | variables LangSmith y campos de trace | metricas obligatorias |

## Open Questions

1. Confirmar si los nombres sin prefijo (`CHUNK_SIZE`, `TOP_K`) reemplazan definitivamente a
   `APP_CHUNK_SIZE`/`APP_CHUNK_OVERLAP` o si se conserva un alias temporal probado.
2. Confirmar el proveedor local de embeddings ganador despues del benchmark, sin cambiar esta
   spec por preferencia teorica.
3. Confirmar si production usara Chroma embebido de un solo worker o Chroma server con volumen y
   autenticacion.
4. Confirmar la politica de secret manager y retencion de LangSmith fuera del checkout local.
