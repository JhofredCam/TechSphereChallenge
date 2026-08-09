# Spec: Benchmark de chunking, embeddings y retrieval

**ID:** `RAG-BENCH-001`  
**Estado:** `PROPOSED`; no existen aun runner ni resultados de benchmark  
**Version:** `0.1.0`  
**Fecha:** `2026-08-08`  
**Depende de:** [`13_rag_environment_configuration_specification.md`](13_rag_environment_configuration_specification.md), [`14_rag_vector_store_chromadb_specification.md`](14_rag_vector_store_chromadb_specification.md)

## Objective

Crear una evaluacion experimental reproducible para seleccionar una combinacion de splitter,
proveedor de embeddings, modelo y parametros de retrieval que maximice la calidad del contexto sin
romper el presupuesto de una conversacion de voz en vivo.

La seleccion no se hara por popularidad del modelo ni por una sola respuesta de ejemplo. Cada
variante se medira con el mismo corpus local, consultas, qrels, hardware, `k`, prompts y numero de
repeticiones. Los resultados se publicaran con versiones, latencias y limitaciones.

La evaluacion mide calidad de recuperacion y grounding de un corpus sintetico/local. No valida la
verdad clinica de los documentos ni autoriza un uso asistencial.

## Supuestos y decisiones

1. FTS5 actual es el baseline lexical `E0`; no se descarta aunque un embedding gane.
2. Los PDF sin texto siguen `needs_ocr` y no se vectorizan ni entran a qrels positivos.
3. Cada chunk conserva documento, pagina, offsets y `chunk_id` trazables; cambiar el splitter
   invalida el indice anterior.
4. Las consultas de evaluacion se separan por documento fuente para evitar fuga entre ajuste y
   prueba.
5. La latencia critica es la consulta caliente, pero se reportan por separado cold start,
   embedding, Chroma, fusion, validacion y RAG completo.
6. Los modelos de razonamiento no forman parte de la comparacion de embeddings. El modelo LLM
   sigue la familia permitida del reto y se prueba solo despues de fijar el contexto recuperado.
7. El ganador es una decision condicionada a los umbrales y al perfil de despliegue; puede haber un
   ganador de calidad y otro de latencia.

## Tech Stack

| Elemento | Candidatos iniciales |
|---|---|
| Baseline | SQLite FTS5, sin embedding |
| Chunker C0 | actual: 1200 caracteres, overlap 200 |
| Chunker C1 | recursive Spanish, objetivo 320 tokens, overlap 48 |
| Chunker C2 | estructural: encabezados, parrafos, listas y tablas, 250-400 tokens |
| Provider P1 | `sentence_transformers` local CPU |
| Provider P2 | `fastembed`/ONNX local CPU, sujeto a compatibilidad |
| Provider P3 | endpoint remoto opcional, solo prueba controlada y redactada |
| Modelo E1 | `BAAI/bge-m3`, dimension esperada 1024 |
| Modelo E2 | `intfloat/multilingual-e5-small`, dimension esperada 384 |
| Modelo E3 | `intfloat/multilingual-e5-base`, dimension esperada 768 |
| Vector DB | ChromaDB con `cosine` |
| Orquestacion de prueba | runner Python determinista; LangSmith opcional |

Las dimensiones son expectativas que se verifican contra el modelo cargado. Un manifest debe
guardar revision o digest del modelo, tokenizer, provider, device, dimension y normalizacion. No se
descargan modelos durante el bootstrap de evaluacion; el entorno debe precargarlos o fallar de
forma explicita.

## Commands

```text
python -m scripts.validate_dataset
python -m app.bootstrap --data-dir <temp>/rag-benchmark-bootstrap
python -m scripts.build_rag_index --profile benchmark --index-version <version> --data-dir <temp>/rag-benchmark
python -m scripts.prepare_rag_eval --output <temp>/rag-qrels.jsonl
python -m scripts.benchmark_rag --matrix configs/rag_benchmark.yaml --repetitions 5 --output <temp>/rag-results.json
python -m scripts.compare_rag_runs --baseline <temp>/fts5.json --candidate <temp>/rag-results.json
python -m pytest tests/test_benchmark_contracts.py tests/test_ingestion.py -q --basetemp <temp>/rag-bench-tests
```

Los comandos de benchmark deben devolver codigo distinto de cero si faltan qrels, si una variante
no reporta latencias por etapa o si se comparan indices con metadatos incompatibles.

## Project Structure

```text
benchmarks/rag/README.md             -> protocolo y limitaciones.
benchmarks/rag/qrels.jsonl           -> relevancias versionadas, sin PII.
benchmarks/rag/queries.jsonl         -> consultas y transformaciones.
benchmarks/rag/matrices/             -> combinaciones de chunker/provider/modelo.
benchmarks/rag/results/              -> artefactos locales ignorados o exportados sin secretos.
configs/rag_benchmark.yaml           -> parametros del experimento.
scripts/prepare_rag_eval.py         -> genera consultas/qrels reproducibles.
scripts/benchmark_rag.py             -> ejecuta matriz y mediciones.
scripts/compare_rag_runs.py          -> calcula deltas y gates.
tests/test_benchmark_contracts.py    -> schema y no-fuga de datos.
```

El corpus canonicamente permanece en `dataset/textos/`. El benchmark puede leerlo, pero no lo
duplica en `benchmarks/` ni escribe resultados dentro de `dataset/` o `docs/`.

## Dataset de evaluacion

El conjunto debe contener, como minimo, consultas positivas, parafrasis, errores de voz y consultas
fuera de corpus:

| Grupo | Cantidad inicial | Objetivo |
|---|---:|---|
| Literal por dominio | 200 | recuperar evidencia directa |
| Parafrasis en espanol | 100 | probar semantica y sinonimia |
| Errores de ASR/acentos | 100 | tolerar voz realista |
| Fuera de corpus | 50 | abstencion y no evidencia |
| Injection paciente/documento | 50 | seguridad de contexto |
| Casos derivados de conversaciones | 50 | lenguaje postoperatorio, sin labels clinicos |

Los dominios se distribuyen sobre las carpetas disponibles, sin usar una carpeta como garantia
clinica. Para reconstruir conversaciones del XLSX:

- filtrar primero `capa1_limpia` o `capa2_ruidosa`;
- respetar sufijos `_c2` y `_c2_tercero`;
- unir trayectoria y conversacion con `caso_id = "caso_" + trayectoria_id`;
- no mezclar capas ni insertar `label_ground_truth`, demografia o comorbilidades en el prompt.

Cada qrel usa:

```text
2 = chunk contiene evidencia directa y suficiente para la pregunta
1 = chunk relacionado, pero incompleto o contextual
0 = irrelevante
```

La anotacion debe conservar `query_id`, `chunk_id`, `relevance`, `source_document_id` y
`annotation_version`. Si una consulta no tiene un chunk suficiente, su resultado esperado es
abstencion y no se fuerza un positivo.

## Experimental Matrix

La matriz minima es:

```text
C0 + FTS5 baseline
C0/C1/C2 x P1/P2 x E1/E2/E3
best semantic variant + Chroma
best semantic variant + FTS5/Chroma hybrid
```

Cada corrida fija:

- mismo snapshot de corpus y misma revision;
- mismo conjunto de queries y qrels;
- mismo `TOP_K`, `VECTOR_FETCH_K`, threshold y contexto maximo;
- cinco repeticiones por consulta despues de veinte warmups;
- concurrencia 1 y 4 en un host de referencia;
- tracing desactivado para la medicion primaria y una corrida secundaria con LangSmith redactado;
- registro de CPU, RAM, sistema operativo, Python, paquetes, modelo, revision, device y batch.

Se separan estas mediciones:

1. cold start del proceso y del modelo;
2. embedding de documento durante indexacion;
3. embedding de query, con cache hit y miss;
4. query Chroma;
5. query FTS5;
6. fusion, hydration SQLite y validacion de elegibilidad;
7. tiempo total de retrieval;
8. tiempo de prompt/LLM y latencia oficial de voz cuando existan timestamps reales.

## Metrics and Targets

### Calidad primaria

- `recall@k`: proporción de qrels relevantes recuperados;
- `hit_rate@k`: al menos un chunk suficiente en los primeros `k`;
- `precision@k`: proporcion de candidatos relevantes;
- `MRR@k`: posicion del primer resultado suficiente;
- `nDCG@k`: calidad ordenada con relevancias 0/1/2;
- `context_precision`: cuanto del contexto enviado al LLM es pertinente;
- `citation_valid_rate`: citas que existen en el conjunto recuperado y SQLite;
- `empty_rate` y `abstention_rate_by_reason` en consultas fuera de corpus.

### Latencia y operacion

- `embedding_query_p50/p95_ms`;
- `chroma_query_p50/p95_ms`;
- `retrieval_total_p50/p95_ms`;
- `index_build_seconds` y `index_lag_seconds`;
- `memory_rss_mb`;
- `cache_hit_ratio`;
- errores y timeouts por provider.

### Targets iniciales

Son gates de diseño, no resultados existentes:

| Metrica | Target inicial |
|---|---:|
| Recall@5 | `>= 0.85` y `>= +5 puntos porcentuales` sobre FTS5 |
| Recall@5 por dominio | `>= 0.80` |
| MRR@10 | `>= 0.70` |
| nDCG@5 | `>= 0.80` |
| Precision@5 | no bajar mas de 2 puntos porcentuales frente a baseline |
| Context precision | `>= 0.80` |
| Citation valid rate | `>= 99.5%` |
| Documento disabled/deleted recuperable | `0` |
| Revision mismatch citado | `0` |
| RAG caliente P95 | `<= 500 ms` |
| Chroma query caliente P95 | `<= 100 ms` |
| Regresion de latencia frente a FTS5 | `<= 10%` |
| Upload pequeno hasta index ready | P95 `<= 10 s` |

Los targets de voz P50 `<= 2000 ms` y P95 `<= 4000 ms` se calculan solo desde
`speech_ended_at` hasta `audio_started_at` en navegador real. No se infieren desde benchmark de
texto, TestClient o mocks.

## Decision Rule

Una variante puede proponerse como candidata primaria solo si:

1. pasa todos los gates P0 de seguridad, revision y delete;
2. cumple calidad minima por dominio y no solo el promedio;
3. cumple presupuesto de latencia en modelo caliente y concurrencia objetivo;
4. mantiene o mejora precision y tasa de abstencion segura;
5. tiene un provider reproducible, modelo fijado y memoria compatible;
6. conserva FTS5 como fallback funcional.

El reporte debe mostrar una tabla de deltas contra FTS5 y una decision separada para `quality-first`,
`latency-first` y `balanced`. No se elige BGE-M3 o E5 solo por documentacion del proveedor.

## Code Style

El runner debe separar datos de configuracion y no tener estado global oculto:

```python
def evaluate_variant(variant: Variant, queries: list[Query], runner: RetrieverRunner) -> Run:
    started = monotonic()
    metrics = [runner.run(variant, query) for query in queries]
    elapsed = (monotonic() - started) * 1000
    return summarize_run(variant, metrics, elapsed_ms=elapsed)
```

Cada fila de resultado incluye `run_id`, `variant_id`, `query_id`, `index_version`,
`chunking_version`, `embedding_model_name`, `embedding_model_revision`, `provider`, `k`, score, hit IDs,
latencias y razon de abstencion. Los resultados no guardan transcripts completos ni secretos.

## Testing Strategy

### Unitarias

- schema de queries, qrels, variants y resultados;
- calculo de recall, precision, MRR, nDCG, context precision y percentiles;
- split train/test por documento;
- deteccion de qrels faltantes, duplicados y chunks fuera del snapshot;
- conversion de prefijos E5 y normalizacion de vectors;
- rechazo de dimension/metrica/version incompatibles;
- no-fuga de `label_ground_truth`, PII y texto clinico innecesario.

### Integracion

- matriz C0/C1/C2 crea indices reproducibles;
- provider ausente produce `SKIPPED` explicito, no un score fabricado;
- resultados de FTS5 y Chroma tienen el mismo contrato de cita;
- benchmark se puede repetir sobre el mismo snapshot y genera los mismos IDs;
- una variante que devuelve un documento disabled/deleted falla P0;
- una corrida con LangSmith apagado no hace red.

### Evidencia y revision

- publicar manifest, qrels versionados, hardware y comandos;
- registrar commit y fecha de cada corrida;
- separar resultados de ajuste de resultados de prueba;
- revisión humana antes de promover una variante;
- ejecutar G5 con documento externo despues del benchmark, porque el corpus de benchmark no lo
  sustituye.

## Boundaries

- **Always:** comparar contra FTS5, medir calidad y latencia, fijar versiones, registrar qrels,
  medir abstencion, usar corpus local y no llamar clinica a una precision de retrieval.
- **Ask first:** cambiar qrels, agregar un provider remoto, descargar modelos durante setup,
  usar datos reales, alterar targets o promover el ganador a produccion.
- **Never:** fabricar resultados, mezclar train/test por documento, usar `label_ground_truth`,
  medir solo promedio, ocultar consultas fuera de corpus o declarar G3/G4/G5 por benchmark.

## Success Criteria

- **BENCH-AC-01:** existe una matriz reproducible de al menos tres estrategias de chunking y tres
  opciones de embedding/modelo o provider, incluyendo FTS5 baseline.
- **BENCH-AC-02:** cada variante se ejecuta con el mismo corpus, qrels, `k`, hardware y protocolo
  de warmup/repeticiones.
- **BENCH-AC-03:** el reporte incluye recall, precision, hit rate, MRR/nDCG, context precision,
  citas validas, abstencion, latencia por nodo y memoria.
- **BENCH-AC-04:** se puede distinguir cold start, modelo caliente, cache hit/miss, Chroma,
  fusion y retrieval completo.
- **BENCH-AC-05:** una variante no se promueve si fuga documentos, rompe revision/citas, degrada
  triaje o supera el presupuesto P95.
- **BENCH-AC-06:** los resultados no usan ni exponen `label_ground_truth`, PII o documentos fuera
  de las rutas canonicas.
- **BENCH-AC-07:** el ganador y los descartes quedan justificados por datos y conservan fallback
  FTS5.

## Trazabilidad

| Requisito | Artefacto | Gate |
|---|---|---|
| precision de retrieval | qrels, `benchmark_rag.py`, reporte | criterio RAG |
| baja latencia | percentiles por nodo y voz | criterio voz |
| conocimiento vivo | casos disable/delete fuera del benchmark | G5 |
| modelo permitido | informe solo para LLM, embeddings separados | G3 |
| proceso reproducible | manifest, commit, entorno y comandos | repositorio |

## Open Questions

1. Confirmar el conjunto final de qrels y quien revisa la relevancia 0/1/2.
2. Confirmar si se permite instalar `fastembed`/ONNX dentro del limite de setup de 15 minutos.
3. Confirmar el hardware de referencia y si se reportara una variante GPU.
4. Confirmar el threshold operativo despues de observar distribuciones por dominio.
5. Confirmar si el provider remoto se mide solo como referencia de latencia o queda fuera por
   privacidad y costo.
