# Plan de implementacion del MVP

## Orden tecnico

1. Crear configuracion, esquema SQLite y contratos de API.
2. Implementar ingestion recursiva, validacion XLSX y ciclo de vida de documentos.
3. Implementar FTS5, fuentes, revision del corpus y prueba de aprender/olvidar.
4. Implementar triaje determinista, llamadas, turnos, resumen y metricas.
5. Integrar el adaptador Groq opcional y la abstencion segura.
6. Servir consola admin e interfaz de voz sin bundler.
7. Agregar bootstrap, pruebas de compuertas, README, diagrama e informe inicial.

## Extensiones planificadas por dependencia

Antes de implementar cambios nuevos, se deben revisar las specs en este orden:

1. `specs/03_mvp_structure_specification.md`: ownership y rutas objetivo bajo `mvp/`.
2. `specs/04_admin_document_lifecycle_specification.md`: preview, `enabled`,
   `rag_eligible`, enable, disable y delete.
3. `specs/05_patient_listening_timeout_specification.md`: `PATIENT_LISTEN_TIMEOUT_MS` y
   estados seguros de escucha.
4. `specs/06_system_flow_diagram_specification.md`: diagrama ASCII/Mermaid, matriz de
   trazabilidad y reflejo de las tres specs anteriores.
5. `specs/07_testing_unit_integration_specification.md`: pruebas unitarias/integracion,
   fixtures, cobertura y evidencia manual asociada a los contratos.

La cuarta spec es un checkpoint de arquitectura: no se debe comenzar la implementacion de una
extension si el diagrama no muestra su bloque, transiciones, estado y verificacion. La quinta
spec debe revisarse antes de implementar cada contrato para evitar pruebas desconectadas del flujo.

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
| Admin documental | documentos procesados | toggle y preview pueden divergir del RAG | bandera `enabled`, filtro activo y pruebas de revision |
| Escucha paciente | navegador | no existe timer propio en el baseline | variable de entorno, estados y fallback textual |

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
6. La migracion documental no inicia hasta que los enlaces y el ownership de `mvp/` esten
   verificados.
7. El admin y el timeout se prueban de forma independiente antes de actualizar el diagrama
   publicado.
8. Las pruebas unitarias y de integracion deben aislar proveedores, datos y estado generado antes
   de servir como evidencia de los gates.
