# Sesion de trabajo - 2026-08-08

## Alcance

Completar la implementacion local y actualizar la documentacion del MVP. Se conserva el
dataset y la documentacion canonica en sus rutas originales y se preserva el README anterior
al fork en `readme/01_repositorio_base_pre_fork/`.

## Estado observado

- `HEAD` es `595989d`, el commit del repositorio base indicado para el snapshot pre-fork.
- El checkout contiene especificacion, plan y tareas bajo `specs/`, implementacion local en
  `app/`, pruebas en `tests/`, dependencias y scripts de validacion/bootstrap.
- `dataset/` contiene los insumos locales y `docs/` contiene la rubrica y el stack canonicos;
  ambos se conservan en sus rutas originales.
- El README raiz ahora es la puerta de entrada ejecutable; el contenido pre-fork se conserva
  en el snapshot con manifest.

## Implementacion observada

- FastAPI/Uvicorn expone `/admin`, `/call`, `/health`, `/api/admin/documents`, `/api/calls`
  y `/api/metrics`.
- SQLite con FTS5 guarda documentos, paginas, chunks, fuentes, llamadas, turnos, auditoria
  y la revision del corpus.
- `python -m app.bootstrap` valida los XLSX y procesa `dataset/textos` por hash, con estados
  `available` y `needs_ocr`.
- El agente usa `llama-3.1-8b-instant` via Groq cuando hay credencial y un fallback
  extractivo local cuando no la hay. El triaje es determinista y no degrada senales rojas.
- La llamada web usa SpeechRecognition `es-CO`, texto de respaldo y SpeechSynthesis; el
  endpoint de audio puede usar Whisper remoto opcional.
- La interfaz registra la latencia percibida de voz desde fin de reconocimiento hasta inicio
  de SpeechSynthesis cuando el navegador emite ambos eventos.

## Decisiones documentadas

1. Organizar el MVP en `mvp/` con seis fases CRISP-DM ordenadas y nombres explicitos.
2. Implementar FastAPI/Uvicorn, SQLite FTS5, PyMuPDF, openpyxl y Web Speech API para un
   camino local-first de 24 horas.
3. Declarar `llama-3.1-8b-instant` via Groq como seleccion del MVP, familia Meta Llama
   permitida. El identificador esta fijado y los modelos no reconocidos caen al ID declarado.
4. Tratar `whisper-large-v3` como STT opcional, no como modelo de razonamiento; usar
   `SpeechSynthesis` para la salida prevista del navegador.
5. Separar pruebas automatizadas de evidencia de gates: G2 queda pendiente de cronometraje
   limpio, G4 de smoke manual con microfono/audio y G5 de un documento externo en demo.
6. Mantener dataset y docs canonicos y enlazarlos desde la documentacion, sin copiar su
   contenido.

## Evidencia de la sesion

- Se cargaron y aplicaron las skills `spec-driven-development` y `git-commit`.
- Se revisaron `README.md`, `AGENTS.md`, la rubrica, el stack tecnico y el historial local.
- `python -m pytest -q --basetemp <temp>`: 38 tests pasaron.
- `ruff check .`: paso sin hallazgos.
- `node --check app/web/app.js`: paso sin salida.
- `python -m scripts.validate_dataset`: valido, con filas `3991/40/40/160`.
- Bootstrap completo: 104 documentos, 103 `available` y 1 `needs_ocr`; segunda ejecucion con
  104 documentos omitidos por hash y la misma revision.
- Smoke HTTP local: upload, uso con cita, delete, nueva consulta abstentiva y resumen cerrado.

## Pendientes

- Cronometrar el setup desde un entorno limpio para G2 y conservar version, commit y horas.
- Ejecutar smoke manual de `/call` en Chrome/Edge con microfono, transcripcion y audio para G4.
- Demostrar G5 con un documento externo al corpus durante la demo evaluada.
- Capturar logs de una llamada real para completar P50/P95, tokens, invocaciones, consultas
  RAG y costo; no inferirlos desde tests.
- Completar capturas, video, las preguntas de cierre y el cierre de G1.
