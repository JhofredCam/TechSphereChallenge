# Plan de implementacion del MVP

## Orden tecnico

1. Crear configuracion, esquema SQLite y contratos de API.
2. Implementar ingestion recursiva, validacion XLSX y ciclo de vida de documentos.
3. Implementar FTS5, fuentes, revision del corpus y prueba de aprender/olvidar.
4. Implementar triaje determinista, llamadas, turnos, resumen y metricas.
5. Integrar el adaptador Groq opcional y la abstencion segura.
6. Servir consola admin e interfaz de voz sin bundler.
7. Agregar bootstrap, pruebas de compuertas, README, diagrama e informe inicial.

## Componentes y dependencias

| Componente | Depende de | Riesgo | Mitigacion |
|---|---|---|---|
| Configuracion | Ninguno | Rutas distintas por SO | `pathlib`, `.env.example`, valores locales |
| SQLite/FTS5 | Python | Build sin FTS5 | Health check y prueba de preflight |
| Ingestion | PyMuPDF | PDF sin capa de texto | Estado `needs_ocr`, no fingir disponibilidad |
| Dataset | openpyxl | XLSX sin dimensiones declaradas | Iterar filas y validar encabezados |
| LLM | httpx, API key | Cuota/modelo retirado | Modelo en entorno, fallback extractivo auditable |
| Voz | Chrome/Edge | API Web Speech variable | texto, MediaRecorder/STT como fallback |
| Frontend | API | permiso de microfono | instrucciones visibles y estado de error |

## Paralelismo

- La documentacion CRISP-DM, el frontend estatico y los tests de contratos pueden avanzar en
  paralelo una vez fijado este plan.
- Ingestion/RAG y base de datos deben coordinar sus nombres de tablas antes de integrarse.
- Voz y triaje pueden desarrollarse en paralelo sobre el contrato `POST /api/calls/{id}/turns`.
- README y el informe deben cerrarse despues de ejecutar los comandos reales, no antes.

## Checkpoints

1. `pytest` pasa para base, chunking y triaje sin credenciales.
2. Bootstrap procesa un directorio fixture y marca un PDF sin texto como `needs_ocr`.
3. Upload/delete pasa con el servidor real y la busqueda cambia sin reinicio.
4. `/call` funciona con texto y con `SpeechRecognition` en navegador compatible.
5. `python -m pytest -q` y la prueba de preflight quedan documentados en README.
