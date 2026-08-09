# CRISP-DM del MVP

Este directorio contiene las seis fases del proceso del MVP. Las fases son documentacion de
proceso; no contienen copias de `dataset/`, `docs/`, runtime, pruebas ni estado generado.

## Fases

1. [Business Understanding](01_business_understanding/README.md)
2. [Data Understanding](02_data_understanding/README.md)
3. [Data Preparation](03_data_preparation/README.md)
4. [Modeling](04_modeling/README.md)
5. [Evaluation](05_evaluation/README.md)
6. [Deployment](06_deployment/README.md)

## Fuentes

- [Especificacion del MVP](../../specs/00_mvp_specification.md)
- [Tareas ejecutables](../../specs/02_implementation_tasks.md)
- [Estructura de entregables](../../specs/03_mvp_structure_specification.md)
- [README operativo de la raiz](../../README.md)

Los comandos se ejecutan desde la raiz. Las fuentes canonicas `dataset/` y `docs/` permanecen
en sus rutas originales y las fases solo las enlazan.

## Upgrade RAG

El upgrade de produccion se desglosa en las Specs 13-19: configuracion externa, ChromaDB,
chunking/embeddings, benchmark, LangChain, LangSmith y operaciones de rollout/rollback. El
baseline FTS5 sigue siendo el camino ejecutable hasta que el benchmark, la reconciliacion y el
rollback tengan evidencia fechada.
