# Arquitectura del MVP

## Estado

Este documento describe la arquitectura implementada del MVP definido en
[`specs/00_mvp_specification.md`](../specs/00_mvp_specification.md). Al 2026-08-08 el
checkout contiene runtime en `app/`, pruebas en `tests/`, dependencias declaradas, la estructura
aplicada bajo `mvp/crisp-dm/` y `mvp/deliverables/`, y los scripts de validacion/bootstrap.
La suite automatizada, Ruff, la validacion del dataset y el bootstrap local estan verificados;
G2, el smoke manual de voz, Groq/Whisper real y la demo G5 con documento externo siguen
pendientes.

La migracion RAG de produccion esta planificada en las Specs 13-19. En este checkout ChromaDB,
embeddings, LangChain, LangSmith y el benchmark semantico siguen `PROPOSED`; el flujo FTS5 que se
describe abajo es el baseline ejecutable y el fallback obligatorio del upgrade.

## Fuente normativa y vista derivada

La especificacion completa del flujo, sus actores, etapas, submodulos, ASCII, Mermaid y matriz
de trazabilidad esta en
[`specs/06_system_flow_diagram_specification.md`](../specs/06_system_flow_diagram_specification.md).
Esta pagina es la vista publicada sincronizada. La vista formal derivada del entregable es
[`mvp/deliverables/02_architecture/architecture.md`](../mvp/deliverables/02_architecture/architecture.md).
No se deben agregar bloques nuevos aqui sin actualizar primero la spec normativa y las specs
upstream:

La version visual vigente usa estas etiquetas: `[USUARIO]` azul, `[ADMIN]` ambar, `[BOT]`
violeta, `[RAG]` turquesa, `[DATOS]` gris, `[EXTERNO]` naranja, `[SEGURIDAD]` rojo y
`[METRICAS]` verde. El color solo comunica ownership; los estados y el triaje se expresan tambien
con texto. La sintaxis se valida contra la version Mermaid fijada por la spec 06.

- [`specs/03_mvp_structure_specification.md`](../specs/03_mvp_structure_specification.md):
  entregables bajo `mvp/` y fases bajo `mvp/crisp-dm/`.
- [`specs/04_admin_document_lifecycle_specification.md`](../specs/04_admin_document_lifecycle_specification.md):
  preview, `enabled`, `rag_eligible`, enable, disable y delete.
- [`specs/05_patient_listening_timeout_specification.md`](../specs/05_patient_listening_timeout_specification.md):
  `PATIENT_LISTEN_TIMEOUT_MS` y estados de escucha.
- [`specs/08_admin_inventory_ux_specification.md`](../specs/08_admin_inventory_ux_specification.md):
  inventario `/admin` de ancho completo, responsive y sin identidad tecnica visible.
- [`specs/09_admin_source_preview_specification.md`](../specs/09_admin_source_preview_specification.md):
  propuesta de archivo original en modal, separada de `pages.text`.
- [`specs/10_architecture_explorer_specification.md`](../specs/10_architecture_explorer_specification.md):
  propuesta de vista navegable derivada, sin autoridad adicional.
- [`specs/11_conversational_ux_writing_specification.md`](../specs/11_conversational_ux_writing_specification.md):
  catálogo aplicado de copy, canales de voz/UI, triaje sticky y errores seguros.
- [`specs/13_rag_environment_configuration_specification.md`](../specs/13_rag_environment_configuration_specification.md):
  configuracion externa y perfiles.
- [`specs/14_rag_vector_store_chromadb_specification.md`](../specs/14_rag_vector_store_chromadb_specification.md):
  ChromaDB como indice derivado y lifecycle.
- [`specs/15_rag_chunking_embedding_benchmark_specification.md`](../specs/15_rag_chunking_embedding_benchmark_specification.md):
  benchmark de calidad y latencia.
- [`specs/16_rag_langchain_orchestration_specification.md`](../specs/16_rag_langchain_orchestration_specification.md):
  loader, runnables y prompt.
- [`specs/17_rag_observability_langsmith_specification.md`](../specs/17_rag_observability_langsmith_specification.md):
  spans y redaction.
- [`specs/18_rag_production_operations_specification.md`](../specs/18_rag_production_operations_specification.md):
  rollout, rollback y backup.
- [`specs/19_rag_production_migration_specification.md`](../specs/19_rag_production_migration_specification.md):
  contrato integrador y sucesor de la spec 12.

Preview, enable/disable, snapshots, el filtro de corpus activo y el timer configurable ya tienen
runtime y pruebas locales. La vista no convierte esas pruebas en evidencia manual de navegador,
G2 o G5 externo.

| Cambio dependiente | Reflejo requerido en el diagrama | Estado del baseline |
|---|---|---|
| Reestructura | `mvp/crisp-dm/` y `mvp/deliverables/` como ownership de entrega | TESTED |
| Preview admin | flujo `GET .../preview` y texto no ejecutable | TESTED |
| Enable/disable | `enabled`, `rag_eligible` y filtro FTS5 | TESTED |
| Inventario admin | grid cerrado de una columna, preview abierto de dos, fichas responsive y copy sin identidad tecnica | contrato estatico TESTED; smoke navegador MANUAL_PENDING |
| Delete | invalidacion, snapshots y olvido sin reinicio | TESTED local; G5 externo pendiente |
| Timeout paciente | `PATIENT_LISTEN_TIMEOUT_MS`, estados, eventos y reintento/texto | TESTED API; browser pendiente |

## Principios

- Monolito local con FastAPI/Uvicorn y archivos estaticos; sin telefonia real.
- Dos superficies obligatorias: `/admin` y `/call`.
- SQLite con FTS5 como recuperacion lexical inicial, con fuentes, chunks y revision trazables.
- Reglas de triaje deterministas separadas de la salida del modelo.
- Respuestas en espanol, breves, grounded o explicitamente abstentivas.
- El corpus y el dataset bajo `dataset/` y `docs/` permanecen canonicos; el estado generado
  se escribe en el directorio `data/` configurado.
- Modelo de razonamiento seleccionado: `llama-3.1-8b-instant` via Groq, familia Meta Llama
  permitida. Con `GROQ_API_KEY` se habilita el adaptador remoto; sin ella se usa el fallback
  extractivo determinista.

## Target de migracion RAG

```text
Ingestion por pagina -> splitter configurable -> embeddings locales
          |                                      |
          +-> SQLite + FTS5 baseline       ChromaDB versionado
                                                   |
Paciente -> triaje -> Chroma/FTS5 -> hydration SQLite -> fusion/threshold
                                              |
                              LangChain prompt -> Llama permitido/fallback
                                              |
                             validacion cita -> respuesta/audio
                                              |
                          JSONL + metricas + LangSmith redacted opcional
```

SQLite conserva documentos, `enabled`, `corpus_revision`, chunks, fuentes y snapshots. Chroma solo
propone candidatos; un vector sin fila elegible se descarta. El target no se considera implementado
hasta que el benchmark, el rollback y las pruebas de conocimiento vivo pasen.

## Componentes y flujo de datos

```mermaid
flowchart LR
    subgraph Browser["Navegador"]
        Admin["[ADMIN] Consola admin<br/>/admin"]:::admin
        Call["[USUARIO] Interfaz de llamada<br/>/call"]:::actor
        SpeechIn["[USUARIO] SpeechRecognition<br/>es-CO"]:::actor
        SpeechOut["[BOT] SpeechSynthesis"]:::bot
        TextFallback["[USUARIO] Entrada textual<br/>fallback"]:::actor
    end

    subgraph API["Aplicacion FastAPI / Uvicorn"]
        Routes["[BOT] Rutas HTTP y estaticos"]:::bot
        Config["[BOT] config.py<br/>timeout publico"]:::bot
        Documents["[ADMIN] documents.py<br/>upload / list / preview / toggle / delete"]:::admin
        Ingestion["[RAG] ingestion.py<br/>PDF, TXT, MD y chunks"]:::rag
        RAG["[RAG] rag.py<br/>FTS5 baseline; Chroma target<br/>available + enabled"]:::rag
        Chroma["[RAG] ChromaDB<br/>indice versionado<br/>PROPOSED"]:::rag
        Chain["[BOT] LangChain<br/>prompt y retriever<br/>PROPOSED"]:::bot
        Trace["[METRICAS] LangSmith<br/>redacted y opcional<br/>PROPOSED"]:::metrics
        Agent["[BOT] agent.py<br/>respuesta grounded"]:::bot
        Triage["[SEGURIDAD] triage.py<br/>reglas conservadoras"]:::security
        Calls["[BOT] calls.py<br/>turnos y resumen"]:::bot
        VoiceEvents["[BOT] voice-events<br/>estados e idempotencia"]:::bot
        Metrics["[METRICAS] metrics.py<br/>logs y agregacion"]:::metrics
    end

    subgraph Local["Estado local configurado"]
        DB[("[DATOS] SQLite authority + FTS5")]:::data
        JSONL[("[METRICAS] events.jsonl")]:::metrics
        Data["[DATOS] data/<br/>app.sqlite3, uploads, events.jsonl"]:::data
    end

    subgraph Sources["Fuentes canonicas"]
        Corpus["[DATOS] dataset/textos/<br/>corpus clinico"]:::data
        XLSX["[DATOS] dataset/*.xlsx<br/>casos sinteticos"]:::data
    end

    subgraph Tools["Herramientas CLI"]
        Bootstrap["[RAG] app.bootstrap<br/>scripts.bootstrap"]:::rag
        Validate["[DATOS] scripts.validate_dataset"]:::data
    end

    Groq["[EXTERNO] Groq API opcional<br/>Llama 3.1 8B Instant<br/>+ Whisper STT opcional"]:::external

    Admin --> Routes
    Call --> Routes
    SpeechIn --> Call
    TextFallback --> Call
    Call --> SpeechOut
    Routes --> Documents
    Routes --> Calls
    Routes --> Config
    Routes --> VoiceEvents
    Documents --> Ingestion
    Documents --> DB
    Corpus --> Ingestion
    Ingestion --> DB
    Bootstrap --> Validate
    Validate --> XLSX
    Bootstrap --> Ingestion
    Calls --> Triage
    Calls --> RAG
    VoiceEvents --> Calls
    Triage --> Agent
    RAG --> Agent
    RAG --> DB
    RAG -.-> Chroma
    RAG -.-> Chain
    Chain -.-> Trace
    Agent --> Groq
    Agent --> Calls
    Calls --> DB
    Calls --> Metrics
    VoiceEvents --> Metrics
    Metrics --> JSONL
    DB --> Data

    classDef actor fill:#DBEAFE,stroke:#1D4ED8,color:#1E3A8A,stroke-width:2px;
    classDef admin fill:#FEF3C7,stroke:#B45309,color:#78350F,stroke-width:2px;
    classDef bot fill:#EDE9FE,stroke:#6D28D9,color:#4C1D95,stroke-width:2px;
    classDef rag fill:#CCFBF1,stroke:#0F766E,color:#134E4A,stroke-width:2px;
    classDef data fill:#E2E8F0,stroke:#475569,color:#1E293B,stroke-width:2px;
    classDef external fill:#FFEDD5,stroke:#C2410C,color:#7C2D12,stroke-width:2px,stroke-dasharray:5 5;
    classDef security fill:#FEE2E2,stroke:#B91C1C,color:#7F1D1D,stroke-width:2px;
    classDef metrics fill:#DCFCE7,stroke:#15803D,color:#14532D,stroke-width:2px;
```

El adaptador Groq es opcional para pruebas locales: sin `GROQ_API_KEY`, el MVP conserva un
camino extractivo determinista basado en FTS5. La interfaz del navegador usa
`SpeechRecognition` con idioma `es-CO`, entrada textual de respaldo y `SpeechSynthesis`; el
endpoint de audio puede usar `whisper-large-v3` via Groq cuando hay credencial. El timer total de
cada intento llega desde `GET /health` como `patient_listen_timeout_ms` y los estados se registran
en `POST /api/calls/{id}/voice-events` sin texto clinico completo. Ninguna prueba automatizada
sustituye el smoke manual de microfono y audio.

## Superficies y rutas implementadas

- `/admin`: consola estatica para subir, listar, previsualizar texto, habilitar/deshabilitar y
  eliminar documentos. El inventario usa todo el ancho cuando el preview esta cerrado, se divide
  en dos zonas solo al abrirlo y se convierte en fichas sin scroll horizontal en pantallas
  estrechas; el SHA, IDs, rutas y codigos internos permanecen fuera de la UI visible.
- `/call`: interfaz estatica para abrir una llamada, hablar o escribir, ver triaje y fuentes,
  y guardar el resumen.
- `GET /health`: estado del modelo configurado, FTS5, documentos, revision del corpus y modo
  de voz; publica `patient_listen_timeout_ms` sin secretos.
- `GET/POST/PATCH/DELETE /api/admin/documents` y
  `GET /api/admin/documents/{id}/preview`: ciclo documental sin reiniciar el proceso.
- `POST /api/calls`, `GET /api/calls/{call_id}`, `POST /api/calls/{call_id}/turns`,
  `POST /api/calls/{call_id}/audio`, `POST /api/calls/{call_id}/voice-events`,
  `POST /api/calls/{call_id}/turns/{turn_id}/voice-timing` y
  `POST /api/calls/{call_id}/finish`: llamada browser/API.
- `GET /api/metrics`: agregacion de eventos de turnos y consumo instrumentado.

### Contrato de escucha

`PATIENT_LISTEN_TIMEOUT_MS` es una duracion maxima total por intento, con default `30000` y
rango `1000..300000`. El cliente obtiene el valor desde `/health`, usa los estados
`LISTENING`, `PARTIAL`, `PROCESSING`, `NO_RESPONSE`, `LISTEN_TIMEOUT`, `RECOGNITION_ERROR` y
`RETRY_REQUIRED`, y envia eventos acotados con `listen_id`. Un transcript final usa
`client_turn_id`; un duplicado reutiliza la respuesta y un resultado posterior a un timeout
responde `409 late_transcript`. El timeout no crea turno ni decision clinica y conserva el
fallback textual. Estos eventos no entran como P50/P95 de respuesta.

## Flujo de decision clinica

```mermaid
flowchart TD
    Start(["[USUARIO] Turno del paciente"]):::actor --> Normalize["[BOT] Normalizar texto o transcripcion"]:::bot
    Normalize --> Safety["[SEGURIDAD] Evaluar reglas de triaje<br/>con nivel previo"]:::security

    Safety -->|"rojo"| Red["[SEGURIDAD] Mantener rojo<br/>persistir alerta"]:::security
    Safety -->|"amarillo"| Yellow["[SEGURIDAD] Mantener amarillo<br/>persistir alerta"]:::security
    Safety -->|"ambiguo / unknown"| Clarify["[SEGURIDAD] Pedir aclaracion<br/>sin cerrar decision"]:::security
    Safety -->|"verde / sin alarma"| Retrieve["[RAG] Consultar SQLite FTS5"]:::rag

    Red --> Retrieve
    Yellow --> Retrieve
    Retrieve --> Evidence{"[RAG] Hay evidencia suficiente?"}:::rag
    Evidence -->|"no"| Abstain["[BOT] Abstencion explicita<br/>y redireccion segura"]:::bot
    Evidence -->|"si"| Compose["[RAG] Construir contexto delimitado<br/>con documento, pagina y chunk"]:::rag
    Compose --> Model["[BOT] Llama permitido o fallback extractivo"]:::bot
    Model --> Cite["[BOT] Respuesta breve + cita + decision"]:::bot
    Clarify --> Audio["[BOT] Texto y audio en espanol"]:::bot
    Abstain --> Audio
    Cite --> Audio
    Audio --> Persist["[DATOS] Guardar turno, fuentes,<br/>latencia y tokens"]:::data
    Persist --> End(["[BOT] Continuar o cerrar llamada"]):::bot

    classDef actor fill:#DBEAFE,stroke:#1D4ED8,color:#1E3A8A,stroke-width:2px;
    classDef bot fill:#EDE9FE,stroke:#6D28D9,color:#4C1D95,stroke-width:2px;
    classDef rag fill:#CCFBF1,stroke:#0F766E,color:#134E4A,stroke-width:2px;
    classDef data fill:#E2E8F0,stroke:#475569,color:#1E293B,stroke-width:2px;
    classDef security fill:#FEE2E2,stroke:#B91C1C,color:#7F1D1D,stroke-width:2px;
```

Las ramas rojas y amarillas no dependen de que el LLM recuerde la regla de seguridad. El
modelo puede redactar una respuesta, pero no puede degradar el nivel calculado ni convertir
un contexto no recuperado en una instruccion clinica. La implementacion automatizada cubre
rojo, amarillo, verde y `unknown`; la cobertura no equivale a un smoke de voz real.

## Conocimiento vivo

```mermaid
sequenceDiagram
    participant U as ADMIN - Administrador
    participant R as BOT - Rutas FastAPI
    participant I as RAG - Ingestion
    participant D as DATOS - SQLite/FTS5
    participant A as BOT - Agente

    U->>R: POST /api/admin/documents
    R->>I: extraer por pagina y generar chunks
    I->>D: guardar documento, estado, enabled y fuentes
    D-->>R: available, needs_ocr o error
    R-->>U: estado visible en /admin
    U->>R: GET /api/admin/documents/id/preview
    R->>D: leer pages.text, limite <= 8000
    D-->>R: texto plano no ejecutable o reason=needs_ocr
    R-->>U: preview textual
    U->>R: PATCH /api/admin/documents/id enabled=false/true
    R->>D: cambiar publicacion, revision y audit sin reingesta
    D-->>R: rag_eligible=false/true
    A->>D: consultar solo status=available AND enabled=1
    D-->>A: chunks y citas
    U->>R: DELETE /api/admin/documents/id
    R->>D: snapshots, transaccion de borrado e invalidacion
    D-->>R: confirmacion sin chunks activos
    A->>D: nueva consulta
    D-->>A: no devuelve la fuente eliminada
```

Un documento sin texto extraible se queda en `needs_ocr` y no entra en el indice disponible. Un
documento deshabilitado conserva pages/chunks y preview, pero queda fuera de RAG. Delete limpia
el contenido indexable, conserva el snapshot minimo de fuentes historicas, elimina el archivo
despues del commit y no requiere reinicio. La prueba G5 automatizada es local; el gate requiere
ademas material externo.

## Mapa de implementacion

| Area | Ruta | Responsabilidad y estado |
|---|---|---|
| Configuracion | `app/config.py`, `.env.example` | Entorno, perfiles, RAG, rutas, limites y `PATIENT_LISTEN_TIMEOUT_MS`; baseline TESTED, target PROPOSED |
| Persistencia | `app/database.py` | SQLite, FTS5, transacciones, `enabled`, snapshots y revision; TESTED |
| Contratos | `app/schemas.py`, `app/main.py` | Entrada/salida, preview, toggle, voice-events y serializacion API; TESTED |
| Dataset | `app/dataset.py`, `scripts/validate_dataset.py` | XLSX, JSON y joins de solo lectura; TESTED |
| Bootstrap | `app/bootstrap.py`, `scripts/bootstrap.py` | Validacion, hash, ingestion e idempotencia; TESTED |
| Ingestion | `app/services/ingestion.py` | PDF, TXT, MD, paginas, chunks y `needs_ocr`; TESTED |
| Documentos | `app/services/documents.py` | Upload/process/preview/toggle/delete y snapshots; TESTED |
| RAG | `app/services/rag.py`, `vector_store.py` | FTS5 baseline, Chroma target, filtro `available AND enabled` y citas; baseline TESTED, target PROPOSED |
| Embeddings | `app/services/embeddings.py` | Provider/modelo, dimension, cache y latencia; PROPOSED |
| LangChain | `app/services/rag_chain.py`, `prompts.py` | loader, retriever, contexto y prompt; PROPOSED |
| Index ops | `app/services/index_manager.py`, `scripts/` | manifest, reconciliacion, promotion y rollback; PROPOSED |
| Observabilidad | `app/services/observability.py` | spans, redaction y LangSmith; JSONL baseline TESTED, target PROPOSED |
| Agente | `app/services/agent.py`, `app/services/messages.py` | Groq opcional, fallback, abstencion, copy `voice_text`/`display_text` y seguridad de salida; TESTED local |
| Seguridad | `app/services/triage.py` | Nivel conservador, alertas y aclaraciones; TESTED |
| Llamadas | `app/services/calls.py` | Turnos, fuentes, alertas, resumen, IDs, `late_transcript` y errores seguros; TESTED |
| Metricas | `app/services/metrics.py` | JSONL, voice-events y agregacion P50/P95; TESTED local |
| Voz | `app/services/voice.py`, `app/web/app.js`, `app/web/messages.js` | Whisper opcional, estados humanizados, SpeechRecognition y SpeechSynthesis; manual pendiente |
| Web | `app/main.py`, `app/web/` | API, `/admin` y `/call`; canales de voz/UI implementados; voz MANUAL_PENDING |

La correspondencia del diagrama con el codigo esta cubierta por la suite automatizada y por
la verificacion local del bootstrap. `node --check` valida la sintaxis de `app.js` y `messages.js`; la
presencia del microfono, el transcript, el audio y el proveedor remoto en un navegador compatible
aun debe comprobarse manualmente. La vista formal con procedencia, estados y divergencias esta
en [`mvp/deliverables/02_architecture/architecture.md`](../mvp/deliverables/02_architecture/architecture.md).

## Evidencia del corte

- `python -m pytest tests/test_admin_lifecycle.py tests/test_timeout.py -q --basetemp <temp>`:
  24 tests pasaron.
- `python -m pytest -q --basetemp <temp>`: 96 tests pasaron.
- `ruff check .`: paso sin hallazgos.
- `node --check app/web/app.js`: sintaxis valida.
- `python -m scripts.validate_dataset`: dataset valido, con filas `3991/40/40/160`.
- `python -m app.bootstrap --data-dir <temp>`: 104 documentos procesados, 103
  `available` y 1 `needs_ocr`.
- La prueba de idempotencia de bootstrap y el aprendizaje/olvido local pasan; G5 sigue
  pendiente de un documento externo en demo.
