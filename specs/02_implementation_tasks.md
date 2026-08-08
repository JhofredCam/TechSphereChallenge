# Tareas ejecutables del MVP

- [ ] Crear configuracion y esquema SQLite
  - Aceptacion: `init_database()` crea tablas, FTS5 y directorios locales sin secretos.
  - Verificar: `python -m pytest tests/test_database.py -q`.
  - Archivos: `app/config.py`, `app/database.py`, `app/schemas.py`.

- [ ] Implementar ingestion y ciclo de vida documental
  - Aceptacion: PDF/TXT/MD se procesan por pagina, se generan chunks y se registra
    `available`, `needs_ocr` o `error`.
  - Verificar: `python -m pytest tests/test_ingestion.py -q`.
  - Archivos: `app/services/ingestion.py`, `app/services/documents.py`.

- [ ] Implementar recuperacion y trazabilidad
  - Aceptacion: cada resultado contiene documento, pagina, chunk, cita y revision del corpus;
    borrar elimina los resultados futuros.
  - Verificar: `python -m pytest tests/test_live_knowledge.py -q`.
  - Archivos: `app/services/rag.py`, `app/database.py`.

- [ ] Implementar dataset foundation
  - Aceptacion: valida hojas, encabezados, filas, JSON embebido y joins sin mezclar capas.
  - Verificar: `python -m scripts.validate_dataset`.
  - Archivos: `app/dataset.py`, `scripts/validate_dataset.py`.

- [ ] Implementar triaje, llamada y resumen
  - Aceptacion: rojo no baja, amarillo crea alerta, ambiguo pregunta y cierre persiste
    resumen estructurado.
  - Verificar: `python -m pytest tests/test_triage.py tests/test_calls.py -q`.
  - Archivos: `app/services/triage.py`, `app/services/calls.py`.

- [ ] Integrar respuesta grounded y metricas
  - Aceptacion: modo Groq usa modelo permitido configurado; sin fuente hay abstencion; cada
    turno registra latencia, tokens, invocaciones y consultas RAG.
  - Verificar: `python -m pytest tests/test_agent.py tests/test_metrics.py -q`.
  - Archivos: `app/services/agent.py`, `app/services/metrics.py`.

- [ ] Exponer API y superficies web
  - Aceptacion: `/admin` soporta upload/list/delete y `/call` soporta microfono, respuesta
    hablada y fallback textual.
  - Verificar: `python -m pytest tests/test_api.py -q` y smoke manual.
  - Archivos: `app/main.py`, `app/web/`.

- [ ] Cerrar bootstrap, documentacion y evidencia
  - Aceptacion: README reproduce setup en <=15 minutos, incluye modelo, diagrama, metricas,
    informe y checklist G1-G5.
  - Verificar: ejecutar todos los comandos del README desde un entorno limpio.
  - Archivos: `README.md`, `readme/`, `mvp/`, `docs/arquitectura.md`, `docs/informe-final.md`.
