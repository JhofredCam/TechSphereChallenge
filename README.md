# Tech Sphere Challenge 2026 | MVP de seguimiento postoperatorio

MVP web local para seguimiento postoperatorio por voz en español colombiano. Expone una
consola de conocimiento y una interfaz de llamada browser/API. Las respuestas clínicas usan
fuentes recuperadas, registran citas y se abstienen cuando el corpus no alcanza.

> Los datos del reto son sintéticos y no están validados clínicamente. Este proyecto no es una
> herramienta diagnóstica ni asistencial.

## Inicio en 15 minutos

Requisitos: Python 3.11 o superior, navegador Chrome o Edge para el camino de voz, y los
archivos locales de `dataset/` que ya vienen en este repositorio. No se descarga el dataset ni
un modelo durante el bootstrap.

```text
python -m venv .venv
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m app.bootstrap
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Abrir:

- `http://127.0.0.1:8000/admin` para subir, listar y eliminar documentos.
- `http://127.0.0.1:8000/call` para iniciar una llamada, hablar y escuchar al agente.
- `http://127.0.0.1:8000/health` para comprobar backend RAG, indice, corpus, voz y modelo declarado.

Para detener el servidor, presiona `Ctrl+C`. El estado generado queda en `data/`, ignorado por
Git. Si la máquina no permite crear el directorio temporal por defecto de pytest, usa un
directorio temporal con permisos, por ejemplo:

```text
python -m pytest -q --basetemp C:\temp\techsphere-pytest
```

### LLM y voz del servidor

El MVP no exige credenciales para bootstrap, pruebas ni fallback extractivo. Para activar el
razonamiento remoto y Whisper, define la clave antes de iniciar Uvicorn:

```text
GROQ_API_KEY=tu_clave
GROQ_MODEL=llama-3.1-8b-instant
GROQ_WHISPER_MODEL=whisper-large-v3
```

Usa el formato de variables de tu sistema (`$env:GROQ_API_KEY="..."` en PowerShell o
`export GROQ_API_KEY="..."` en bash). `.env.example` documenta los valores sin contener
secretos. La demo básica de navegador usa `SpeechRecognition` `es-CO` y `SpeechSynthesis`,
por lo que mantiene entrada por micrófono y audio aun sin una clave. La disponibilidad del
modelo exacto debe comprobarse antes de la demo; si Groq retira el ID, usa un sucesor vigente
de la misma familia Meta Llama y actualiza el informe.

## Qué funciona

### Consola de administración

1. Entra a `/admin`.
2. Sube un `.pdf`, `.txt` o `.md`.
3. Confirma `Disponible` o `Necesita OCR` en el inventario.
4. Usa `Previsualizar` para inspeccionar el texto extraido como texto plano no ejecutable.
5. Usa `Deshabilitar` para conservar el documento y excluirlo del RAG; `Habilitar` lo publica de
   nuevo sin reprocesarlo.
6. Usa `Eliminar` para borrar paginas, chunks, filas FTS5 y vectores Chroma cuando el upgrade este
   activo, conservar el snapshot historico y retirar el archivo sin reiniciar el servidor.

Los documentos se identifican por SHA-256, se procesan de forma síncrona y conservan página,
chunk, cita y revisión del corpus. Un PDF sin texto no se presenta como disponible.

### Llamada de voz

1. Entra a `/call`, completa nombre/procedimiento y pulsa `Iniciar llamada`.
2. Permite el micrófono y pulsa `Hablar`; el idioma configurado es `es-CO`.
3. El agente muestra la transcripción, consulta el corpus, muestra fuentes y reproduce la
   respuesta con la voz del navegador.
4. El timeout total de cada intento llega desde `/health` (`PATIENT_LISTEN_TIMEOUT_MS`, default
   30000 ms). Un parcial es solo borrador; timeout, no respuesta o error ofrecen reintento/texto
   y no crean un turno clinico.
5. Si Web Speech API no está disponible, usa el campo de texto; sigue siendo el mismo endpoint
   auditable. El endpoint `/api/calls/{id}/audio` acepta audio para Whisper cuando hay clave.
6. Pulsa `Finalizar llamada` para guardar el resumen estructurado.

El triaje determinista no delega la seguridad al LLM:

- `rojo`: escala inmediatamente y nunca baja de nivel.
- `amarillo`: crea alerta persistente para contacto oportuno con el equipo clínico.
- `verde`: no se detecta alarma en la información disponible.
- `unknown`: pide aclaración antes de concluir.

### Prueba de conocimiento vivo

Usa una frase que no exista en el corpus, por ejemplo `La señal lunar exige llamar al equipo
azul`, en un archivo de texto:

1. Súbelo en `/admin` y confirma `Disponible`.
2. Pregunta por `señal lunar` en `/call`; la respuesta debe mostrar la cita del archivo.
3. Elimina el archivo en `/admin` sin reiniciar.
4. Repite la pregunta; el agente debe abstenerse y no mostrar esa fuente.

La prueba automatizada equivalente es:

```text
python -m pytest tests/test_live_knowledge.py -q
```

## Arquitectura

```text
Navegador
  ├── /admin: upload, listado, preview, enable/disable, delete
  └── /call: SpeechRecognition + timeout -> API -> SpeechSynthesis
                         │
                         ▼
                    FastAPI monolito
      ┌────────────────┼──────────────────┐
      │                │                  │
  DocumentService   CallService       VoiceService
      │                │                  │
       └──── SQLite authority + FTS5 fallback ────┘
                          │
          RagService + Chroma + fusion + triaje
                          │
              LangChain + Llama / fallback
```

El diagrama detallado y el flujo de decisión están en [`docs/arquitectura.md`](docs/arquitectura.md).
La API está documentada por OpenAPI en `http://127.0.0.1:8000/docs` cuando el servidor está
levantado.

La fuente normativa integradora de este flujo es
[`specs/06_system_flow_diagram_specification.md`](specs/06_system_flow_diagram_specification.md).
Depende de las specs de estructura, administracion documental y timeout; por eso cualquier cambio
en esas tres debe reflejarse primero en el ASCII, los subdiagramas Mermaid y la matriz `TRZ-*`.
La spec 06 esta integrada con el runtime aplicado: preview, habilitar/deshabilitar, filtro
`available + enabled`, snapshots y timeout configurable tienen pruebas locales. La vista formal
derivada esta en [`mvp/deliverables/02_architecture/architecture.md`](mvp/deliverables/02_architecture/architecture.md).

## Especificaciones y estado sincronizado

- [`03_mvp_structure_specification.md`](specs/03_mvp_structure_specification.md): entregables
  bajo `mvp/` y fases bajo `mvp/crisp-dm/`.
- [`04_admin_document_lifecycle_specification.md`](specs/04_admin_document_lifecycle_specification.md):
  preview textual, publicacion independiente, filtro RAG, snapshots y delete implementados.
- [`05_patient_listening_timeout_specification.md`](specs/05_patient_listening_timeout_specification.md):
  timeout total configurable, estados, eventos, reintento y fallback implementados.
- [`06_system_flow_diagram_specification.md`](specs/06_system_flow_diagram_specification.md):
  diagrama integrador sincronizado con codigo, contratos y pruebas.
- [`07_testing_unit_integration_specification.md`](specs/07_testing_unit_integration_specification.md):
  estrategia de pruebas unitarias, integracion, cobertura y evidencia manual.
- [`08_admin_inventory_ux_specification.md`](specs/08_admin_inventory_ux_specification.md):
  inventario `/admin` full-width, responsive, con estados humanos y sin identidad tecnica visible;
  implementado localmente. El contrato estatico se verifica con
  `tests/test_admin_ui_contracts.py`; el smoke visual sigue siendo manual.
- [`09_admin_source_preview_specification.md`](specs/09_admin_source_preview_specification.md):
  modal implementado para distinguir archivo original y texto extraído; el smoke de navegador
  sigue pendiente de evidencia manual.
- [`10_architecture_explorer_specification.md`](specs/10_architecture_explorer_specification.md):
  explorador HTML offline implementado en `docs/architecture_explorer.html`; verifica con
  `python -m pytest tests/test_architecture_explorer.py -q --basetemp <temp>` y `node --check docs/architecture_explorer.js`.
- [`11_conversational_ux_writing_specification.md`](specs/11_conversational_ux_writing_specification.md):
  catálogo aplicado en backend y `/call`: copy `voice_text`/`display_text`, triaje sticky,
  errores seguros, preguntas de una intención y trazabilidad separada en `source_display`.
- [`13_rag_environment_configuration_specification.md`](specs/13_rag_environment_configuration_specification.md):
   variables, defaults, perfiles y secretos redacted del pipeline.
- [`14_rag_vector_store_chromadb_specification.md`](specs/14_rag_vector_store_chromadb_specification.md):
   ChromaDB, metadata, lifecycle, reconciliacion y fallback FTS5.
- [`15_rag_chunking_embedding_benchmark_specification.md`](specs/15_rag_chunking_embedding_benchmark_specification.md):
   benchmark de chunkers, providers, embeddings, calidad y latencia.
- [`16_rag_langchain_orchestration_specification.md`](specs/16_rag_langchain_orchestration_specification.md):
   loaders, runnables, prompt grounded y limites de LangChain.
- [`17_rag_observability_langsmith_specification.md`](specs/17_rag_observability_langsmith_specification.md):
   spans, redaccion, metricas y LangSmith fail-open.
- [`18_rag_production_operations_specification.md`](specs/18_rag_production_operations_specification.md):
   manifest, rollout, rollback, backup y seguridad operacional.
- [`19_rag_production_migration_specification.md`](specs/19_rag_production_migration_specification.md):
   contrato integrador de la migracion RAG y su operacion de produccion.

## Previsualizacion de fuentes en `/admin`

`Previsualizar` abre una ventana accesible con dos modos: `Archivo original`, que sirve el
PDF/TXT/MD recibido como contenido no ejecutable, y `Texto extraido`, que conserva la preview
por pagina de la ingestion. El endpoint de solo lectura es
`GET /api/admin/documents/{id}/source`; usa MIME canonico, `no-store` y nunca expone rutas.

## Modelo permitido

| Componente | Selección | Justificación |
|---|---|---|
| Razonamiento | `llama-3.1-8b-instant` vía Groq | Meta Llama está permitida; ofrece baja latencia y evita descargar un modelo local en 24 horas. |
| STT opcional | `whisper-large-v3` vía Groq | La voz está abierta por la rúbrica; centraliza el camino de audio remoto. |
| TTS principal | `SpeechSynthesis` del navegador, idioma `es-CO` | Cero descarga y audio real en la superficie browser. |
| Fallback local | Extractivo FTS5 y reglas deterministas | Permite probar grounding, abstención y triaje sin credenciales ni modelo no autorizado. |
| Vector store target | ChromaDB persistente y versionado | Especificado; implementacion/benchmark PENDIENTE. |
| Embeddings | provider/modelo local configurable | Candidatos BGE-M3/E5; ganador PENDIENTE. |
| Orquestacion | LangChain core/adaptadores controlados | Especificado; implementacion PENDIENTE. |
| Observabilidad RAG | JSONL + LangSmith redacted opcional | JSONL existente; LangSmith PENDIENTE. |

La familia del modelo de razonamiento es la restricción cerrada del reto. No se usa ningún
modelo alternativo fuera de `docs/stack-tecnico.md`. Los embeddings son una capa separada y se
seleccionan por el benchmark de la Spec 15.

## Datos y bootstrap

`dataset/` y `docs/` son las copias canónicas del reto y permanecen fuera de carpetas de
implementación. El bootstrap:

- valida las cuatro hojas `result`, encabezados, conteos, JSON embebido y joins;
- respeta `paciente_id` y `caso_id = "caso_" + trayectoria_id`;
- no mezcla `capa1_limpia` con `capa2_ruidosa`;
- recorre `dataset/textos/` de forma recursiva, incluidos espacios, Unicode y duplicados;
- marca el PDF escaneado de `Appendicitis/` como `needs_ocr`;
- es idempotente por hash y no altera archivos bajo `dataset/`.

Comandos de verificación:

```text
python -m scripts.validate_dataset
python -m app.bootstrap --json
```

La última verificación local confirmó `3991` turnos, `40` perfiles clínicos, `40` perfiles
demográficos y `160` trayectorias. El corpus produjo `104` documentos únicos: `103 available`
y `1 needs_ocr`.

## Pruebas y calidad

```text
python -m pytest -q
ruff check .
python -m pytest tests/test_api.py tests/test_live_knowledge.py -q
python -m pytest tests/test_admin_lifecycle.py tests/test_timeout.py -q --basetemp <temp>
python -m pytest tests/test_admin_ui_contracts.py -q
python -m pytest -q --basetemp <temp>/coverage-pytest --cov=app --cov=scripts --cov-branch --cov-report=term-missing --cov-report=xml:<temp>/coverage.xml --cov-fail-under=80
node --check app/web/app.js
python -m scripts.validate_dataset
```

La suite baseline cubre SQLite/FTS5, extracción, PDF sin texto, validación XLSX,
upload/preview/toggle/delete, abstención, prompt injection, triaje, llamadas, resumen, API,
timeout, eventos e idempotencia. Las suites Chroma, benchmark, LangChain, LangSmith y rollback
son entregables `PROPOSED` del upgrade y no se presentan como ejecutadas.
La evidencia de la sincronización previa registró `24` pruebas enfocadas y `93` en la suite
completa; Ruff no reportó hallazgos y `node --check app/web/app.js` fue válido.

La implementación ejecutable de la spec 07 agregó 31 casos; las regresiones de concurrencia dejan
`96 passed` en la suite completa y `80.07%` de cobertura de `app` y `scripts` con ramas y umbral 80.
El XML se escribió en un
temporal fuera del repositorio. G4, G2, G5 externo y Groq/Whisper real siguen `MANUAL_PENDING`
aunque sus contratos locales estén probados; la API tampoco valida MIME de forma independiente.

## Métricas obligatorias

La API `GET /api/metrics` y `data/events.jsonl` son la fuente de medición. Cada turno registra
`latency_ms`, `input_tokens`, `output_tokens`, `model_calls`, `rag_queries`, `call_id`,
`turn_id`, `source_ids` y `model_version`.

| Métrica | Definición |
|---|---|
| P50/P95 | Desde fin de habla (`speech_ended_at`) hasta inicio de audio (`audio_started_at`); el navegador debe enviar ambos timestamps si se habilita esa medición. |
| Tokens | Entrada/salida por turno y suma por llamada; Groq aporta uso real y el fallback conserva una estimación de palabras identificada como tal. |
| Invocaciones | `model_calls` por turno y total de la llamada. |
| Consultas RAG | `rag_queries` y fuentes devueltas por turno. |
| Costo | Para Groq: `(tokens_in * precio_in + tokens_out * precio_out) + STT/TTS`; para fallback local: costo de API extrapolado con la misma fórmula y precios fechados en el informe. |

No se inventan valores de una sesión de voz que todavía no se ha cronometrado en un navegador.
Después de una demo real, copia la respuesta de `/api/metrics`, fecha, modelo y precios a
[`readme/04_metricas_y_evidencia.md`](readme/04_metricas_y_evidencia.md) y
[`docs/informe-final.md`](docs/informe-final.md).

## Estado de compuertas

| Gate | Estado en este checkout | Evidencia o pendiente |
|---|---|---|
| G1 | Pendiente de entrega final | Repositorio, diagrama e informe están presentes; falta video y sus respuestas de cierre. |
| G2 | `MANUAL_PENDING` | El setup es ejecutable; falta cronometraje desde entorno limpio siguiendo solo este README. |
| G3 | `TESTED` local; `MANUAL_PENDING` real | `llama-3.1-8b-instant` pertenece a Meta Llama permitida; falta confirmar disponibilidad y llamada efectiva antes de grabar. |
| G4 | `MANUAL_PENDING` | Micrófono `SpeechRecognition` y audio `SpeechSynthesis` viven en `/call`; falta evidencia manual con navegador. |
| G5 | `TESTED` local; `MANUAL_PENDING` externo | Tests de aprender/olvidar, preview y toggle pasan; repetir upload/uso/delete con un documento externo al corpus durante la evaluación. |

No se declara una compuerta aprobada solo por intención o por un mock.

## Organización del repositorio

- [`app/`](app/): FastAPI, SQLite, ingesta, RAG, agente, triaje, llamadas y web estática.
- [`scripts/`](scripts/): bootstrap e inspección reproducible del dataset.
- [`tests/`](tests/): pruebas unitarias e integración HTTP.
- [`specs/`](specs/): especificaciones, plan y tareas de spec-driven development; fuente
  normativa durante la migracion.
- [`tasks/`](tasks/): plan de dependencia y backlog ejecutable del upgrade RAG.
- [`mvp/`](mvp/): contenedor aplicado de entregables y fases CRISP-DM bajo `mvp/crisp-dm/`.
- [`readme/`](readme/): setup, demo, métricas, sesiones y snapshot pre-fork.
- [`docs/arquitectura.md`](docs/arquitectura.md): diagrama y flujo de decisión.
- [`docs/informe-final.md`](docs/informe-final.md): informe vivo, riesgos y evidencia pendiente.
- [`readme/01_repositorio_base_pre_fork/`](readme/01_repositorio_base_pre_fork/): README original y manifest del commit `595989d`; no duplica dataset/docs.
- [`GUIA_AGENTE_PLANIFICADOR_Y_ESPECIFICACIONES.md`](GUIA_AGENTE_PLANIFICADOR_Y_ESPECIFICACIONES.md): iniciar planificación y specs.
- [`GUIA_AGENTE_EJECUTOR_DE_TAREAS.md`](GUIA_AGENTE_EJECUTOR_DE_TAREAS.md): iniciar ejecución y verificación.

La estructura bajo `mvp/`, preview administrativa, publicación `enabled` y timeout de escucha
están implementados y probados localmente. La migracion Chroma/LangChain/LangSmith esta
especificada pero pendiente de implementacion y benchmark. La evidencia manual de voz, G2 y G5
externo sigue pendiente; las métricas de voz y costo no se inventan.

Para registrar una nueva sesión, crea `readme/06_bitacora_de_sesiones/YYYY-MM-DD_nombre.md` con
alcance, decisiones, comandos ejecutados, resultados y pendientes. Las decisiones sobre modelo exacto, OCR,
streaming de voz, despliegue público o canales de alerta deben quedar explícitas antes de
ampliar el MVP.

## Contrato original y licencia

El contrato completo del reto, sus entregables y la rúbrica original están preservados en
[`readme/01_repositorio_base_pre_fork/README.md`](readme/01_repositorio_base_pre_fork/README.md),
conservando `dataset/`, [`docs/rubrica-evaluacion.md`](docs/rubrica-evaluacion.md) y
[`docs/stack-tecnico.md`](docs/stack-tecnico.md) como fuentes canónicas.

El código y los datos sintéticos se distribuyen bajo [MIT](LICENSE). Los PDF conservan los
derechos de sus autores y se incluyen solo como material del reto.
