# Protocolo de benchmark RAG

Este directorio contiene el contrato reproducible para comparar el baseline lexical FTS5 con
variantes semánticas. `queries.jsonl` y `qrels.jsonl` son un conjunto semilla revisable; no son
una validación clínica ni resultados de producción. Las consultas se mantienen separadas por
documento fuente y no contienen `label_ground_truth`, transcripciones completas ni PII.

La matriz declarada en [`configs/rag_benchmark.yaml`](../../configs/rag_benchmark.yaml) fija
chunking, provider, modelo, métrica, `k`, threshold, warmups y repeticiones. El runner no descarga
modelos: un provider ausente se reporta como `SKIPPED` explícito. `builtin_hash` solo sirve para
pruebas deterministas del contrato y nunca es una recomendación de embedding clínico.

Ejemplo:

```text
python -m scripts.prepare_rag_eval --output-dir .pytest-tmp/rag-eval
python -m scripts.benchmark_rag --matrix configs/rag_benchmark.yaml --repetitions 5 --output .pytest-tmp/rag-results.json
python -m scripts.compare_rag_runs --baseline .pytest-tmp/fts5.json --candidate .pytest-tmp/rag-results.json
```

Para resultados con métricas se entrega un corpus de chunks JSONL con `chunk_id`, `text`,
`source_document_id`, `page`, `start_offset` y `end_offset` mediante `--corpus`. Sin corpus, el
runner aún valida el protocolo y marca las variantes como `SKIPPED`; nunca fabrica scores.

Las latencias se separan en `embedding_query`, `vector_query`, `fts5_query`, `fusion_hydration`,
`validation` y `retrieval_total`. La corrida guarda el `index_version`, revisión de corpus,
configuración de variante y un `run_id` determinista; no escribe dentro de `dataset/`.
