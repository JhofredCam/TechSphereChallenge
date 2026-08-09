# Spec: Pruebas unitarias e integracion del MVP

**Estado:** baseline ejecutable; suites Chroma/benchmark/LangChain/LangSmith/ops especificadas, aun pendientes
**Version:** 0.3.0
**Fecha:** 2026-08-08

## Objetivo

Definir una estrategia reproducible de pruebas unitarias, integracion, benchmark y operacion para
el runtime del MVP y el upgrade RAG en `app/`, `scripts/` y `tests/`. La suite debe validar
contratos, persistencia, FTS5, ChromaDB, retrieval, triaje, seguridad, metricas, ingestion,
LangChain y API sin depender de credenciales, red, modelos descargados ni modificaciones de las
fuentes canonicas.

La estrategia debe demostrar:

- comportamiento determinista de triaje, grounding, abstencion y seguridad;
- persistencia real en SQLite/FTS5, transacciones, revision y borrado;
- ingestion de PDF, TXT y MD, incluyendo `needs_ocr`, duplicados, hashes y rutas problematicas;
- contratos HTTP de `/admin`, `/call`, `/health` y `/api/metrics`;
- aprendizaje y olvido de conocimiento mediante upload/delete sin reiniciar el proceso;
- persistencia Chroma, manifest, reinicio, reconciliacion, stale vectors y rollback FTS5;
- benchmark reproducible de chunking/providers/modelos con recall, context precision y latencias;
- redaction y comportamiento fail-open de LangSmith;
- persistencia de turnos, fuentes, alertas y resumen de llamada;
- separacion entre automatizacion, smoke manual y compuertas G1-G5.

Las pruebas no validan la seguridad clinica real de los documentos. Los datos de `dataset/` son
sinteticos y no estan validados para uso asistencial. El baseline historico documentado reporta
38 pruebas pasadas; esta implementacion ejecutable agrega 31 casos y verifica 93 casos en total.

## Dependencias y precedencia

Esta spec depende de:

- `specs/00_mvp_specification.md`: alcance, limites y criterios de exito;
- `specs/01_implementation_plan.md` y `specs/02_implementation_tasks.md`: orden y comandos;
- `specs/03_mvp_structure_specification.md`: ownership de `tests/` y artefactos;
- `specs/04_admin_document_lifecycle_specification.md`: preview, `enabled` y RAG activo;
- `specs/05_patient_listening_timeout_specification.md`: timeout, eventos e idempotencia;
- `specs/06_system_flow_diagram_specification.md`: IDs `TRZ-*`, flujo y estados;
- `specs/13_rag_environment_configuration_specification.md`: variables y perfiles;
- `specs/14_rag_vector_store_chromadb_specification.md`: Chroma y consistencia;
- `specs/15_rag_chunking_embedding_benchmark_specification.md`: qrels y gates;
- `specs/16_rag_langchain_orchestration_specification.md`: loaders, prompt y runnables;
- `specs/17_rag_observability_langsmith_specification.md`: spans y redaction;
- `specs/18_rag_production_operations_specification.md`: rollout, backup y rollback;
- `specs/19_rag_production_migration_specification.md`: contrato integrador;
- `docs/rubrica-evaluacion.md`: gates G1-G5 y metricas obligatorias;
- `docs/stack-tecnico.md`: familias de modelos permitidas.

Los cambios en contratos, tablas, rutas, timeouts o estados deben actualizar esta spec y la
matriz `TRZ-*` del diagrama antes de agregar o modificar pruebas.

## Tech Stack

| Componente | Seleccion del checkout |
|---|---|
| Runtime | Python 3.11 o superior |
| API | FastAPI 0.115.12 y Uvicorn 0.34.2 |
| Pruebas | pytest 8.4.2 |
| Cobertura | pytest-cov 6.1.1 |
| Lint | Ruff 0.11.2 |
| Cliente HTTP | `fastapi.testclient.TestClient` sobre HTTPX 0.28.1 |
| Persistencia | SQLite de la biblioteca estandar con FTS5 + ChromaDB versionado |
| PDF | PyMuPDF 1.25.5 |
| XLSX | openpyxl 3.1.5 |
| Frontend | HTML, CSS y JavaScript sin bundler |
| Modelo remoto opcional | `llama-3.1-8b-instant` via Groq |
| STT remoto opcional | `whisper-large-v3` via Groq |

Las dependencias de ejecucion viven en `requirements.txt`; pytest, pytest-cov y Ruff viven en
`requirements-dev.txt`. No se agrega por defecto Playwright, Selenium, pytest-xdist, Docker,
CI ni un servicio externo. La automatizacion browser requiere una decision separada porque
puede afectar el setup de 15 minutos.

## Project Structure

### Suite existente

| Archivo | Cobertura principal |
|---|---|
| `tests/test_agent.py` | grounding, abstencion, citas, salida segura, prompt injection y allowlist de modelos |
| `tests/test_api.py` | `/health`, CRUD documental, llamadas, audio, timing, metricas y G5 HTTP |
| `tests/test_bootstrap.py` | XLSX sintetico, bootstrap, idempotencia, hashes y limpieza de almacenamiento |
| `tests/test_calls.py` | turnos, fuentes, triaje persistente, resumen y timing de voz |
| `tests/test_database.py` | SQLite, FTS5, WAL, claves foraneas, revision y transacciones |
| `tests/test_ingestion.py` | extraccion, chunking, normalizacion, PDF, OCR, XLSX y nombres seguros |
| `tests/test_live_knowledge.py` | aprender, recuperar, borrar y olvidar conocimiento sin reinicio |
| `tests/test_metrics.py` | JSONL, percentiles, timestamps y eventos de voz |
| `tests/test_triage.py` | alarmas, niveles sticky, ambiguedad e inyeccion de instrucciones |
| `tests/test_config_contracts.py` | rutas, limites y overrides locales de configuracion |
| `tests/test_dataset_contracts.py` | contratos negativos XLSX, JSON, joins y CLI temporal |
| `tests/test_http_contracts.py` | limites de llamadas, paginas, errores y payloads sin rutas |
| `tests/test_schema_contracts.py` | defaults y propiedades de trazabilidad de schemas |
| `tests/test_structure.py` | estructura de `mvp/` y ausencia de copias prohibidas |
| `tests/test_voice.py` | adaptador Whisper con cliente falso, limites y errores |

No existe `tests/conftest.py` ni una bateria automatizada para `app/web/app.js`. Un `conftest.py`
puede agregarse para fixtures compartidas, pero no debe ocultar el contexto de cada prueba ni
mover la logica especifica de los modulos actuales.

### Extensiones propuestas por la migracion

Estos archivos no existen aun y no se deben contar como cobertura actual:

| Archivo propuesto | Cobertura prevista |
|---|---|
| `tests/test_vector_store.py` | Chroma adapter, metadata, score, persistencia y fallos |
| `tests/test_rag_consistency.py` | hydration SQLite, revision, stale vectors, disable/delete y fallback |
| `tests/test_benchmark_contracts.py` | qrels, schemas, metricas, no-fuga y manifest |
| `tests/test_loader_contracts.py` | DocumentLoader y metadata LangChain |
| `tests/test_rag_chain.py` | runnables, budgets, conteo y contexto |
| `tests/test_prompt_contracts.py` | prompt versionado, injection, citas y salida segura |
| `tests/test_observability_contracts.py` | spans, redaction, fail-open y health |
| `tests/test_rag_operations.py` | manifest, promotion, rollback, reconciliacion y backup |

### Extensiones implementadas y frontera manual

- `tests/test_admin_lifecycle.py` verifica la migracion idempotente, preview, toggle, filtro RAG,
  delete, limpieza fisica y snapshots de la spec 04.
- `tests/test_timeout.py` verifica configuracion, `/health`, estados de escucha, carreras,
  `client_turn_id`, transcript tardio y eventos de la spec 05.
- `tests/test_voice.py` verifica el contrato del proveedor falso; no afirma que Whisper real,
  `SpeechRecognition` o `SpeechSynthesis` funcionen.
- No existe `tests/test_voice_state.py`: la maquina de estados del navegador continua como
  `MANUAL_PENDING`, porque no se agrego un runner browser por separado.

No se crean copias de `dataset/`, `docs/` ni `data/` dentro de `tests/`.

## Code Style

- Nombrar archivos `test_<area>.py` y casos con el comportamiento esperado, no con detalles de
  implementacion.
- Organizar cada caso como arrange, act, assert, con un oraculo explicito y mensajes utiles.
- Preferir `tmp_path`, `monkeypatch` y dobles pequenos sobre estado global, `sleep` o red real.
- Mantener los IDs `UT-*`, `IT-*` y `MAN-*` en tablas o comentarios breves para enlazar prueba,
  requisito y evidencia.
- No convertir un fixture en una copia del dataset ni ocultar una dependencia externa.

## Baseline actual y brechas conocidas

El checkout tiene 17 modulos de pruebas y 93 casos ejecutados en esta implementacion. La cifra de
38 funciones `test_*` pertenece a una sesion anterior y se conserva solo como referencia
historica.
Las siguientes brechas son conocidas y no deben presentarse como cubiertas:

- la eliminacion fisica exitosa y el error de limpieza estan cubiertos localmente; no se prueba un
  bloqueo de archivo real en todos los sistemas operativos;
- la API actual valida sufijo y tamaño, pero no valida MIME de forma independiente;
- la prueba de bootstrap usa fixtures XLSX, no los cuatro archivos canonicos completos;
- no hay cobertura automatizada de navegador, microfono, TTS, Groq real o Whisper real;
- la cobertura se ejecuta con un XML temporal que no se conserva en el repositorio;
- importar `app.main` crea una instancia global y puede tocar `data/` antes del aislamiento;
- varios tests actuales no cierran explicitamente `TestClient` o conexiones;
- el entorno padre puede aportar `GROQ_MODEL` aunque no exista `GROQ_API_KEY`;
- G1, G2, G4 y la demostracion externa de G5 siguen necesitando evidencia fuera de pytest.

Una fila catalogada como local se considera verificada solo cuando el archivo actual y el
resultado fechado de abajo la respaldan. Las capacidades de navegador, proveedor real, G2 y G5
externo permanecen fuera de pytest.

### Resultado ejecutado de esta implementacion

Fecha de ejecucion: `2026-08-08`; entorno: Windows, Python `3.13.3`; estado de versionado:
`working tree/no commit`. Los temporales y el XML de cobertura se escribieron fuera del
repositorio.

- Suite completa: `96 passed` usando `python -m pytest -q --basetemp <temp>/pytest`.
- Cobertura de `app` y `scripts`, con ramas y umbral 80: `80.07%`, `96 passed`, usando el
  comando de cobertura de esta spec; `TST-AC-10` queda verificado para este checkout.
- Regresion API/conocimiento vivo: `8 passed`.
- Agente, triaje, llamadas y metricas: `28 passed`.
- Base, ingestion y bootstrap: `16 passed`.
- Ruff: `All checks passed`.
- Dataset canonico: valido; filas `3991/40/40/160`.
- Bootstrap canonico: `104` documentos, `103 available` y `1 needs_ocr`.
- Estructura `mvp/`: 13 rutas requeridas presentes y sin copias prohibidas.
- `git diff --check`: sin errores.

En este entorno, `python -m pytest -q` sin `--basetemp` no pudo crear el directorio temporal
predeterminado por un `PermissionError` de Windows; la misma suite pasa con el temporal
escribible documentado en `README.md`. Esto no se cuenta como fallo de un test.

## Testing Strategy

La suite sigue una piramide: muchas pruebas unitarias deterministas, menos integraciones con
SQLite/FTS5 y API en proceso, y una frontera manual pequena para navegador, hardware, proveedor
real y documento externo. Cada nivel tiene un oraculo distinto y un estado de evidencia propio.

## Definiciones de nivel

### Prueba unitaria

Valida una funcion, clase o regla con dependencias externas sustituidas. Puede usar memoria y
archivos temporales, pero no requiere una API, proveedor, dataset canonico ni proceso de
servidor. El oraculo debe ser determinista y describir la salida, excepcion o invariante.

Ejemplos: normalizacion, chunking, `classify_triage`, construccion de contexto, abstencion,
percentiles y parseo de configuracion.

### Prueba de integracion

Valida dos o mas componentes reales del sistema: SQLite/FTS5, servicios, bootstrap, FastAPI y
`TestClient`. Puede usar proveedores falsos con el mismo contrato, pero no puede afirmar que
Groq, Whisper, microfono o audio real funcionan.

Ejemplos: upload/search/delete, llamada completa con resumen, bootstrap temporal y consulta de
`/api/metrics`.

### Evidencia manual

Valida capacidades que dependen de navegador, permisos, hardware, proveedor real o protocolo
de evaluacion. No se convierte en un test automatizado mediante mocks. G2, G4 y la parte externa
de G5 conservan evidencia manual aunque las pruebas locales pasen.

## Piramide y prioridades

La distribucion orientativa es:

| Nivel | Proporcion | Proposito |
|---|---:|---|
| Unitarias | 60 % | reglas puras, normalizacion, ingestion, citas y metricas |
| Integracion | 30 % | SQLite/FTS5, servicios, bootstrap y API en proceso |
| Smoke/manual | 10 % | microfono, audio, UI, proveedor real y documento externo |

La prioridad de fallas es:

1. **P0:** falso negativo rojo, degradacion de amarillo, respuesta clinica sin evidencia,
   cita inventada, delete incompleto o timeout convertido en `verde`.
2. **P1:** perdida de revision, fuentes no trazables, resumen incompleto, fuga de secretos,
   duplicacion de turnos o contaminación entre pruebas.
3. **P2:** cobertura de errores secundarios, compatibilidad de formatos y mensajes de UI.

Una prueba P0 fallida bloquea el cierre aunque la cobertura global supere el umbral.

## Fixtures y aislamiento

Los fixtures deben ser pequeños, sinteticos, autocontenidos y eliminables:

- `tmp_path` para cada SQLite, upload, JSONL, corpus y dataset de fixture;
- `Settings(data_dir=tmp_path)` y `init_database(settings)` para persistencia real aislada;
- `TestClient(create_app(settings=settings, database=database))` para contratos HTTP;
- `monkeypatch.delenv("GROQ_API_KEY")` como estado predeterminado de pruebas locales;
- `FakeRag`, `FakeAdapter`, `FakeAgent` y cliente HTTP falso para aislar proveedores;
- reloj controlado para `MetricsService` y percentiles reproducibles;
- TXT/MD en directorios anidados con espacios, Unicode y nombres peligrosos;
- PDF generado con PyMuPDF, uno con texto y otro sin capa de texto;
- XLSX generado con openpyxl, hoja `result`, headers esperados y JSON valido;
- marcador unico de conocimiento, por ejemplo `mariposa zafiro 92817`, para G5 local;
- `threading.Event` y tiempos controlados solo en pruebas de concurrencia justificadas.

Reglas de aislamiento:

- No usar la instancia global `app = create_app()` de `app.main` cuando se necesite un directorio
  temporal.
- Cerrar explicitamente bases y clientes creados por una prueba.
- No depender del orden de ejecucion ni de IDs aleatorios concretos.
- Eliminar variables de proveedor del entorno y no cargar `.env` automaticamente.
- Ejecutar bootstrap con `--data-dir` temporal.
- No usar pruebas paralelas hasta resolver conexiones SQLite compartidas y handles en Windows.
- No modificar `dataset/`, `docs/` ni el `data/` compartido del checkout.

## Catalogo de pruebas unitarias

| ID | Area | Caso | Oraculo |
|---|---|---|---|
| `UT-DATA-01` | Dataset | hojas `result`, headers y conteos | valida correctamente; rechaza hoja/header/conteo invalido |
| `UT-DATA-02` | Dataset | JSON de `comorbilidades` y `adaptation_fields` | parsea valido y falla explicitamente ante JSON invalido |
| `UT-DATA-03` | Dataset | joins por `paciente_id` y `caso_id` | no usa posicion de fila ni crea casos incorrectos |
| `UT-DATA-04` | Dataset | capas limpia/ruidosa y sufijos `_c2` | no mezcla capas ni terceros |
| `UT-DATA-05` | Seguridad de datos | exclusion de `label_ground_truth` | el campo no llega a contexto clinico |
| `UT-ING-01` | Ingestion | recursion, espacios, Unicode, duplicados y SHA-256 | inspecciona rutas y deduplica sin perder trazabilidad |
| `UT-ING-02` | Ingestion | paginas, TXT/MD, PDF sin texto y chunks | conserva pagina, indice, cita y `needs_ocr` |
| `UT-ING-03` | Ingestion | PDF corrupto, bytes invalidos y extension no soportada | devuelve error seguro y no publica contenido parcial |
| `UT-RAG-01` | RAG | normalizacion, ranking FTS5 y limite de resultados | retorna documento, pagina, chunk, score, cita y revision |
| `UT-RAG-02` | RAG | sin evidencia o score insuficiente | `sources=[]`, abstencion y redireccion segura |
| `UT-RAG-03` | RAG | filtro de corpus | `status='available' AND enabled=1`; documento deshabilitado no es recuperable |
| `UT-RAG-04` | Citas | fuente citada no recuperada | rechaza citas inventadas o ajenas al resultado |
| `UT-AGENT-01` | Agente | contexto con prompt injection | trata documentos/paciente como datos no ejecutables |
| `UT-AGENT-02` | Agente | salida insegura, dosis o diagnostico inventado | filtra, usa fallback o se abstiene |
| `UT-AGENT-03` | Agente | proveedor ausente, error o timeout | fallback auditable y triaje conservado |
| `UT-TRIAGE-01` | Triaje | rojo, amarillo, verde y unknown | clasificacion determinista esperada |
| `UT-TRIAGE-02` | Triaje | multiples señales y nivel previo | rojo/amarillo no se degradan |
| `UT-TRIAGE-03` | Triaje | negaciones, regionalismos y ambiguedad | normaliza sin falso verde y pide aclaracion cuando corresponde |
| `UT-CALL-01` | Llamadas | persistencia de turnos, fuentes y alertas | relaciones e invariantes se conservan |
| `UT-CALL-02` | Resumen | cierre de llamada | paciente, procedimiento, sintomas, decision, fuentes, alerta y pasos |
| `UT-CALL-03` | Llamadas | llamada inexistente/cerrada y cierre repetido | errores HTTP/estado estables e idempotencia definida |
| `UT-VOICE-01` | Voz | soporte, idioma `es-CO` y fallback textual | estado visible y alternativa sin microfono |
| `UT-VOICE-02` | Voz | `SpeechSynthesis` | idioma y respuesta entregados al navegador |
| `UT-TIME-01` | Timeout | default `30000`, rango `1000..300000` | acepta limites y rechaza valores invalidos |
| `UT-TIME-02` | Timeout | estados listening/partial/processing/timeout/retry | parcial no llama backend; timeout no crea turno ni verde |
| `UT-TIME-03` | Timeout | carrera timer/result/end/error | un solo intercambio y transcript tardio descartado |
| `UT-TIME-04` | Idempotencia | `client_turn_id` repetido o deadline exacto | respuesta persistida o `409 late_transcript` |
| `UT-TIME-05` | Separacion | cambio de timeout paciente | no cambia Groq, Whisper ni SQLite |
| `UT-ADMIN-01` | Admin | `status`, `enabled`, `rag_eligible` | solo `available + enabled` es recuperable |
| `UT-ADMIN-02` | Preview | pagina, offset, limite 8000 y HTML malicioso | texto seguro, sin `stored_path` ni ejecucion |
| `UT-ADMIN-03` | Toggle | habilitar, deshabilitar y no-op | revision aumenta solo en cambios efectivos |
| `UT-ADMIN-04` | Migracion | backfill e idempotencia de enabled | solo disponibles quedan habilitados |
| `UT-ADMIN-UI-01` | Inventario admin | HTML, CSS y JS sin SHA/IDs visibles, overflow horizontal ni `innerHTML` | contrato estatico de layout, copy humano y render seguro |
| `UT-MET-01` | Metricas | P50/P95 y timestamps invalidos | sin timestamps no reporta latencia |
| `UT-MET-02` | Metricas | tokens, llamadas, RAG y fuentes | agregacion por turno y llamada coherente |
| `UT-MET-03` | Costo | formula y precios fechados | contrato documentado; precios vivos siguen `MANUAL_PENDING` |
| `UT-MET-04` | Observabilidad | eventos de voz/timeout | IDs presentes; sin audio, texto completo ni secretos |

Las filas `UT-ADMIN-*` y `UT-TIME-*` tienen cobertura local en `test_admin_lifecycle.py`,
`test_admin_ui_contracts.py` y `test_timeout.py`; la evidencia de layout calculado, lector de
pantalla y navegador sigue siendo manual.

| `UT-CONFIG-01` | Configuracion | rutas, limites y overrides locales | no crea rutas durante el parseo y rechaza limites inseguros |
| `UT-STRUCT-01` | Entregables | fases, entregables y ausencia de copias | estructura aplicada y sin fuentes canonicas duplicadas |

`UT-DATA-04` y `UT-DATA-05` no se declaran satisfechas por pytest: el runtime valida capas y
headers, pero no reconstruye conversaciones ni envia `label_ground_truth` a un contexto clinico.
La exclusion debe revisarse si se agrega ese consumidor. `UT-VOICE-01` y `UT-VOICE-02` describen
contratos de navegador y siguen `MANUAL_PENDING`; `UT-MET-03` sigue pendiente de precios y logs
reales.

## Catalogo de pruebas de integracion

| ID | Flujo | Caso | Oraculo |
|---|---|---|---|
| `IT-DATA-01` | Dataset | comando de validacion sobre los cuatro XLSX reales | `valid`; baseline esperado `3991/40/40/160`; no es un test pytest actual |
| `IT-BOOT-01` | Bootstrap | base temporal, FTS5, corpus y directorios | no descarga ni modifica `dataset/`; baseline 104 documentos |
| `IT-BOOT-02` | Bootstrap | ejecutar dos veces | segunda ejecucion idempotente, sin duplicar hashes/chunks |
| `IT-ADMIN-01` | Admin local | upload PDF/TXT/MD y listado | estado, SHA, tamaño, paginas/chunks y revision visibles |
| `IT-ADMIN-02` | Admin actual | extension y tamaño invalidos | codigos HTTP y errores estables; MIME independiente queda como brecha futura |
| `IT-LIVE-01` | G5 local | subir marcador, consultar y verificar cita | respuesta grounded con fuente, pagina, chunk y revision |
| `IT-LIVE-02` | G5 local | borrar y consultar sin reiniciar | FTS5/chunks/paginas dejan de devolver fuente; abstencion |
| `IT-RAG-01` | RAG | pregunta conocida del corpus | fuente real, `source_ids` y cita coherentes |
| `IT-RAG-02` | Abstencion | pregunta fuera del corpus | no inventa clinica ni muestra fuentes |
| `IT-SEC-01` | Seguridad | injection en documento o paciente | no altera mision, triaje ni respuesta segura |
| `IT-TRIAGE-01` | Triaje | rojo, amarillo, verde y unknown por API | nivel, alertas, aclaraciones y pasos persistidos |
| `IT-TRIAGE-02` | Triaje | rojo seguido de texto benigno | nivel y alerta no se degradan |
| `IT-CALL-01` | Llamada | crear, turnar y finalizar | `closed` y resumen estructurado persistidos |
| `IT-VOICE-01` | Voz contractual | audio fixture con adaptador Whisper falso | transcript/error/fallback correctos; no prueba G4 |
| `IT-VOICE-02` | Timing | registrar `voice-timing` repetido | latencia vinculada sin duplicar turno |
| `IT-MET-01` | Metricas | turno completo y `/api/metrics` | JSONL y agregados coinciden |
| `IT-MET-02` | Metricas | turno sin timestamps | no fabrica P50/P95 |
| `IT-G3-01` | Modelo | config, health y allowlist | familia permitida y fallback no contado como llamada remota |
| `IT-ADMIN-P-01` | Admin lifecycle | preview, disable, enable y delete | contratos 200/404/409/422, filtro y revision correctos |
| `IT-ADMIN-P-02` | Admin lifecycle | deshabilitar, rehabilitar y eliminar | abstencion, recuperacion sin reingesta y olvido |
| `IT-ADMIN-UI-01` | Admin UI | carga, vacio, estados, identidad interna y reflow | contrato estatico; smoke manual en 320/375/540/768/1024/1280 px |
| `IT-TIME-P-01` | Timeout | `/health` y timeout publico | `patient_listen_timeout_ms` sin secretos |
| `IT-TIME-P-02` | Timeout | transcript duplicado/tardio y carrera | un intercambio por `(call_id, client_turn_id)` |
| `IT-STRUCT-01` | Entregables | comprobacion estructural de `mvp/` | 13 rutas presentes y no hay copias prohibidas |
| `IT-HTTP-01` | API | limites de llamada, errores y payloads | `422/404/409`, sin `stored_path` |
| `IT-VOICE-03` | Voz contractual | cliente Whisper falso | transcript y errores sin red; no prueba G4 |

Las pruebas de integracion usan SQLite y servicios reales, pero proveedores remotos falsos.
Solo una prueba manual con credencial demuestra disponibilidad real de Groq/Whisper.

## Catalogo de pruebas de la migracion RAG

### Unitarias nuevas

| ID | Area | Caso | Oraculo |
|---|---|---|---|
| `UT-CONFIG-RAG-01` | Config | defaults, rangos y cross-fields | perfil efectivo valido o error accionable |
| `UT-VECTOR-01` | Chroma | metadata, dimension, metrica y manifest | incompatibles se rechazan antes de query |
| `UT-VECTOR-02` | Score | distancia cosine y threshold | score determinista y no clinico |
| `UT-VECTOR-03` | Hydration | hit sin SQLite, disabled o deleted | se descarta y registra stale, no se cita |
| `UT-RAG-HYBRID-01` | Fusion | FTS5 + Chroma, deduplicacion y orden | resultado estable y `rag_queries` coherente |
| `UT-BENCH-01` | Qrels | recall, precision, hit, MRR/nDCG | formulas y casos vacios correctos |
| `UT-BENCH-02` | Latencia | p50/p95 por nodo y cold/warm | no mezcla voz ni inventa valores |
| `UT-LOADER-01` | LangChain | PDF/TXT/MD a `Document` | pagina, offsets, hash y OCR se conservan |
| `UT-CHAIN-01` | LangChain | nodos, timeouts y contexto | no hay llamadas ocultas ni contexto ilimitado |
| `UT-PROMPT-01` | Prompt | delimitadores e injection | paciente/fuente no cambian instrucciones |
| `UT-OBS-01` | LangSmith | redaction y exporter caido | sin PII/secrets y fail-open |
| `UT-OPS-01` | Ops | transiciones, promotion y rollback | puntero atomico y razon auditada |

### Integracion nueva

| ID | Flujo | Caso | Oraculo |
|---|---|---|---|
| `IT-CHROMA-01` | Persistencia | build, reinicio y query | vectores disponibles con manifest identico |
| `IT-CHROMA-02` | Idempotencia | backfill dos veces | mismo conteo e IDs, sin duplicados |
| `IT-RAG-03` | Lifecycle | upload, disable, enable y delete | cero fuga, abstencion o recuperacion esperada |
| `IT-RAG-04` | Revision | mutacion durante retrieval | `corpus_changed`, sources vacias o reintento seguro |
| `IT-RAG-05` | Fallo parcial | SQLite commit y Chroma error en ambos ordenes | no citable, evento y reconciliacion |
| `IT-BENCH-01` | Benchmark | matriz completa y repetible | resultado con hardware/versiones/latencias |
| `IT-CHAIN-01` | Orquestacion | loader -> retriever -> prompt -> DTO | grounding/cita y aliases existentes |
| `IT-CHAIN-02` | Seguridad | LLM contradice triage o inventa cita | validator fallback/abstencion |
| `IT-OBS-01` | Trazas | LangSmith off/on/fake | local siempre funciona, externo redacted |
| `IT-OPS-01` | Rollout | shadow/canary/promote/rollback | puntero y health coherentes |
| `IT-OPS-02` | Restore | backup SQLite + Chroma + manifest | consulta valida y snapshots fuera del RAG |

### Gates de benchmark

Una corrida se marca `PASS` solo si tiene snapshot, qrels, manifest, commit, hardware, warmups,
repeticiones y resultados por consulta. Los gates P0 son:

- `disabled_document_leak_count == 0`;
- `deleted_document_leak_count == 0`;
- `citation_revision_mismatch_count == 0`;
- `prompt_injection_mission_change_count == 0`;
- paridad de triage `100%`;
- no se promueve una variante sin fallback FTS5.

Los resultados de recall, precision, context precision y latencia no se escriben como cifras
historicas hasta ejecutar el runner. Un provider faltante queda `SKIPPED`, no `0`.

El archivo de borrado fisico esta cubierto localmente. La validacion MIME independiente no existe
en el runtime actual y queda como brecha documentada; la lectura del dataset canonico se verifica
con `python -m scripts.validate_dataset`, no como fixture pytest.

## Contratos HTTP a cubrir

| Metodo y ruta | Verificaciones minimas |
|---|---|
| `GET /health` | `200`, estado, modelo/familia, FTS5, documentos, revision y modo de voz |
| `GET /api/admin/documents` | `200`, documentos, conteo y estados |
| `POST /api/admin/documents` | multipart, PDF/TXT/MD, SHA, `available`/`needs_ocr`, limites |
| `DELETE /api/admin/documents/{id}` | `200 deleted=true`, limpieza y segundo delete `404` |
| `POST /api/calls` | contexto minimo y llamada activa |
| `GET /api/calls/{id}` | llamada, turnos, fuentes y `404` |
| `POST /api/calls/{id}/turns` | texto 1..5000, triaje, fuentes, respuesta y metricas |
| `POST /api/calls/{id}/audio` | multipart, audio vacio/excedido, `503` sin credencial y error seguro |
| `POST /api/calls/{id}/turns/{turn_id}/voice-timing` | timestamps, latencia e idempotencia |
| `POST /api/calls/{id}/finish` | resumen, alerta, decision y cierre |
| `GET /api/metrics` | percentiles, tokens, llamadas, RAG, fuentes y eventos |
| `GET /api/admin/documents/{id}/preview` | pagina, offset, limite, OCR, 404/409/422 |
| `PATCH /api/admin/documents/{id}` | toggle, no-op, revision, 404/409/422 |
| `POST /api/calls/{id}/voice-events` | timeout, IDs, sin texto clinico completo |

Las respuestas no deben exponer `stored_path`, claves, tokens ni secretos. Preview, toggle y
voice-events tienen contratos locales verificados; la UI y la voz real no se aprueban por estos
tests.

## Cobertura y calidad

La cobertura objetivo es 80 % del codigo propio mediante pytest-cov, con prioridad en:

- `app/config.py`, `app/database.py`, `app/dataset.py`;
- `app/services/documents.py`, `ingestion.py`, `rag.py`, `agent.py`, `triage.py`, `calls.py`,
  `metrics.py` y `voice.py`;
- `app/main.py` y `scripts/`.

Ademas de la cifra global, deben probarse explicitamente las ramas P0: borrado FTS5, abstencion,
citas invalidas, dosis/diagnosticos inventados, rojo/amarillo sticky, `needs_ocr`, duplicado por
SHA, fallo de limpieza, timing duplicado y limites HTTP.

La cobertura de `app/web/app.js` no se obtiene con pytest-cov. Su voz requiere smoke manual o un
runner JavaScript aprobado por separado. No se acepta una cifra sin comando, fecha, commit,
entorno y reporte de cobertura. La cobertura no aprueba G4 ni la prueba externa de G5.

## Seguridad y datos

Las pruebas deben comprobar:

- SQL parametrizado ante nombres como `guide'); DROP TABLE documents;--.txt`;
- extension, tamaño, rutas derivadas del hash y ausencia de traversal; la validacion MIME
  independiente queda como brecha del runtime;
- nombres Windows reservados, Unicode, espacios finales y rutas largas;
- no exposicion de `stored_path`, claves, tokens, audio ni texto clinico completo en eventos;
- escape de contexto recuperado y rechazo de prompt injection en ingles y español;
- persistencia del rojo frente a injection y rechazo de salida clinica insegura;
- abstencion cuando falta evidencia y ausencia de fuentes despues de delete;
- fixtures sin credenciales, personas reales ni datos innecesarios;
- bind local en `127.0.0.1` mientras no haya autenticacion.

Los datos reales del reto solo se leen en validaciones explicitas. Ninguna prueba escribe en
`dataset/` o `docs/`; el estado de bootstrap usa `--data-dir` temporal.

## Comandos de verificacion ejecutados

Desde la raiz, con `requirements-dev.txt` instalado. Sustituir `<temp>` por un directorio
temporal escribible; no reutilizar `data/` del checkout:

```text
python -m pytest -q --basetemp <temp>/techsphere-pytest
python -m pytest tests/test_api.py tests/test_live_knowledge.py -q --basetemp <temp>/api
python -m pytest tests/test_agent.py tests/test_triage.py tests/test_calls.py tests/test_metrics.py -q --basetemp <temp>/agent
python -m pytest tests/test_database.py tests/test_ingestion.py tests/test_bootstrap.py -q --basetemp <temp>/data
python -m pytest -q --basetemp <temp>/coverage-pytest --cov=app --cov=scripts --cov-branch --cov-report=term-missing --cov-report=xml:<temp>/coverage.xml --cov-fail-under=80
ruff check .
python -m scripts.validate_dataset
python -m app.bootstrap --data-dir <temp>/techsphere-bootstrap
python -c "from pathlib import Path; required = ['mvp/README.md', 'mvp/crisp-dm/README.md', 'mvp/crisp-dm/01_business_understanding/README.md', 'mvp/crisp-dm/02_data_understanding/README.md', 'mvp/crisp-dm/03_data_preparation/README.md', 'mvp/crisp-dm/04_modeling/README.md', 'mvp/crisp-dm/05_evaluation/README.md', 'mvp/crisp-dm/06_deployment/README.md', 'mvp/deliverables/01_repository/README.md', 'mvp/deliverables/02_architecture/README.md', 'mvp/deliverables/03_final_report/README.md', 'mvp/deliverables/04_video/README.md']; missing = [p for p in required if not Path(p).is_file()]; assert not missing, missing"
git diff --check
```

Si pytest no puede crear su temporal:

```text
python -m pytest -q --basetemp <temp>/techsphere-pytest
```

Para evidencia manual, levantar sin credenciales obligatorias:

```text
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

URLs manuales: `/admin`, `/call`, `/health` y `/docs` en `http://127.0.0.1:8000`.

Cada resultado debe registrarse con fecha, commit, entorno, comando o URL, resultado y artefacto
en `readme/04_metricas_y_evidencia.md`. Un comando no ejecutado permanece `PENDIENTE`.

## Evidencia manual y compuertas

| Gate | Automatizacion de soporte | Evidencia que no se sustituye |
|---|---|---|
| G1 | rutas, enlaces y manifiestos | repositorio, diagrama, informe, video y preguntas de cierre |
| G2 | bootstrap, health y smoke local | cronometraje desde entorno limpio en <=15 minutos |
| G3 | allowlist, config y `model_version` | proveedor/modelo real coherente y declarado |
| G4 | API, audio contractual y fallback simulado | Chrome/Edge, microfono, saludo y audio del agente |
| G5 | upload/search/delete local sin reinicio | documento externo al corpus y olvido en demo |

Los mocks pueden demostrar contratos y fallback, nunca aprobar G3, G4 o el documento externo de
G5. Las pruebas de voz deben distinguir `SpeechRecognition`, Whisper, `SpeechSynthesis` y texto.

## Dependencias de las specs 04-06

### Spec 04: ciclo documental de `/admin`

`specs/04_admin_document_lifecycle_specification.md` esta implementada en el runtime y sus
pruebas locales viven en `tests/test_admin_lifecycle.py` y `tests/test_live_knowledge.py`:

- migracion idempotente, backfill e indice de `enabled`;
- preview por pagina, offset, limite 8000, PDF/TXT/MD, OCR, error y texto no ejecutable;
- habilitar, deshabilitar, no-op, revision y filtro `available + enabled`;
- delete, snapshot historico y ausencia de reutilizacion de fuentes borradas;
- contratos `404`, `409`, `413`, `415` y `422`.

La presentacion del inventario definida por Spec 08 agrega `tests/test_admin_ui_contracts.py` para
los invariantes estaticos (sin SHA, IDs, rutas ni `innerHTML`; grid de una/dos columnas; fichas
sin overflow). Ese contrato no sustituye la inspeccion manual del DOM, zoom, teclado, lector de
pantalla ni el calculo de `scrollWidth` en los viewports soportados.

El 2026-08-08 se intento ejecutar el smoke con el navegador integrado, pero el runtime no expuso
ningun backend de navegador (`agent.browsers.list()` devolvio una lista vacia). Por eso la
verificacion visual, de zoom, lector de pantalla y `scrollWidth` conserva estado `MANUAL_PENDING`.

### Spec 05: timeout configurable

`specs/05_patient_listening_timeout_specification.md` esta implementada en el runtime y sus
pruebas locales viven en `tests/test_timeout.py` y `tests/test_api.py`:

- default 30000, rango 1000..300000 y valores invalidos;
- `GET /health` con `patient_listen_timeout_ms` sin secretos;
- carreras `onresult`, `onend`, `onerror` y timer;
- `client_turn_id`, transcript tardio y `409 late_transcript`;
- ausencia de respuesta clinica, verde o cierre al vencer sin transcript final;
- eventos sin audio ni texto clinico completo y sin cambios en timeouts de Groq, Whisper o SQLite.

### Spec 06: diagrama normativo

Cada ID `TRZ-*` que corresponda a una prueba debe tener requisito, fuente, ruta/contrato,
comando o recorrido y estado. La existencia de un diagrama no es evidencia de ejecucion. G4
conserva `MANUAL_PENDING` hasta comprobar microfono/audio y G5 conserva el requisito de documento
externo.

### Specs 08-10: documentacion y superficies derivadas

- **Spec 08:** el layout responsive, la ausencia de scroll horizontal, el ocultamiento de SHA y
  el foco requieren smoke en Chrome/Edge; `node --check` no prueba el DOM.
- **Spec 09:** el endpoint de archivo original requiere pruebas de bytes, MIME canonico, headers,
  path traversal, PDF/TXT/MD, `needs_ocr` y modal accesible. El visor PDF no puede prometer
  impedir copias hechas desde el navegador.
- **Spec 10:** el explorador HTML debe abrir con `file://`, no hacer solicitudes de red, mantener
  procedencia y pasar validacion estatica de IDs, estados, relaciones, enlaces locales y ausencia
  de secretos. Este smoke documental no aprueba G4 ni G5.
- **Spec 11:** el catalogo de mensajes debe cubrir todas las ramas de agente, triaje, llamadas y
  voz. Las pruebas deben comprobar maximo dos oraciones, una pregunta, contencion, copy si/no,
  ausencia de metadatos tecnicos y conservacion de alertas. El smoke real de `SpeechSynthesis`
  sigue siendo manual.
- **Specs 13-19:** la documentacion RAG debe reflejar configuracion, ingestion, chunking versionado,
  embeddings, ChromaDB, FTS5 fallback, `available + enabled`, filtro de relevancia, revision,
  citas, snapshots, LangChain, LangSmith redacted, benchmark y rollback. Sus pruebas focalizadas
  agregan `test_vector_store.py`, `test_rag_consistency.py`, `test_benchmark_contracts.py`,
  `test_loader_contracts.py`, `test_rag_chain.py`, `test_prompt_contracts.py`,
  `test_observability_contracts.py` y `test_rag_operations.py`; ninguna suite local aprueba el
  recorrido G5 con documento externo.

La UI de `/admin` y el explorador de arquitectura tienen fronteras distintas. No se reutiliza el
estado de una llamada, el catalogo del explorador no consulta el API y los datos de preview nunca
se convierten en evidencia RAG.

## Criterios de aceptacion

- **TST-AC-01:** `requirements-dev.txt` permite ejecutar pytest, pytest-cov y Ruff desde la raiz.
- **TST-AC-02:** el baseline automatizado funciona sin `GROQ_API_KEY`, red ni modelos descargados.
- **TST-AC-03:** la suite de base usa SQLite/FTS5 real y verifica transacciones, revision,
  claves foraneas, WAL y limpieza.
- **TST-AC-04:** ingestion cubre PDF, TXT, MD, paginas, chunks, duplicados, espacios, Unicode,
  nombres Windows y `needs_ocr`.
- **TST-AC-05:** `/health`, `/admin`, `/call`, timing, audio, cierre y metricas tienen contratos
  de integracion con `TestClient`.
- **TST-AC-06:** upload, busqueda, delete y olvido ocurren sin reiniciar y la nueva consulta no
  cita la fuente borrada.
- **TST-AC-07:** rojo nunca baja, amarillo conserva alerta, unknown aclara e injection no altera
  la mision.
- **TST-AC-08:** respuestas grounded conservan documento, pagina, chunk, cita y revision;
  respuestas sin evidencia se abstienen.
- **TST-AC-09:** JSONL y `/api/metrics` concuerdan en latencia, tokens, llamadas, RAG y fuentes.
- **TST-AC-10:** la cobertura reportada alcanza 80 % segun el comando definido y las ramas P0
  tienen pruebas explicitas; resultado local `80.07%` con `96 passed`.
- **TST-AC-11:** ninguna prueba escribe en `dataset/`, `docs/` o el `data/` compartido.
- **TST-AC-12:** G4 sigue pendiente hasta tener navegador, microfono y audio reales.
- **TST-AC-13:** las specs 04 y 05 tienen runtime y cobertura local; browser, proveedor real y
  evidencia externa permanecen `MANUAL_PENDING`. La spec 06 esta integrada.
- **TST-AC-14:** cada resultado publicado conserva fecha, commit, entorno y evidencia; no se
  inventan metricas de voz.
- **TST-AC-15:** el flujo de validacion documental de specs 08-10 separa DOM/viewport, archivo
  original/MIME y explorador offline; una prueba estatica no se presenta como un gate real.
- **TST-AC-16:** la reescritura de Spec 11 tiene inventario completo de literales, pruebas de copy
  y una frontera explicita entre texto hablado, UI, fuentes y diagnostico interno.
- **TST-AC-17:** las pruebas RAG de la Spec 19 cubren normalizacion, chunking, hashes, PDF sin
  texto, FTS5 parametrizado, relevancia, `available + enabled`, revision concurrente, citas
  validas, fallback, abstencion y conocimiento vivo; el recorrido G5 externo permanece manual.
- **TST-AC-18:** las suites nuevas cubren Chroma persistente, metadata, dimension/metrica,
  hydration SQLite, stale vectors, reconciliacion, rollback y paridad FTS5.
- **TST-AC-19:** el benchmark separa qrels de ajuste/prueba, reporta recall, context precision,
  citas, abstencion, memoria y latencia por nodo sin fabricar valores.
- **TST-AC-20:** LangChain conserva el DTO y la seguridad, LangSmith es redacted/fail-open y
  `health` no expone secretos.

## Limites

- **Siempre:** usar fixtures temporales, consultas parametrizadas, proveedores falsos en tests,
  oraculos explicitos y estados honestos.
- **Preguntar antes:** agregar browser automation, ejecutar proveedores remotos en CI, cambiar
  el umbral de cobertura, mover `tests/`, introducir servicios externos o cambiar el esquema.
- **Nunca:** commitear secretos, modificar `dataset/` o `docs/`, usar un mock como gate real,
  ocultar una prueba fallida, fabricar P50/P95, marcar timeout como verde o citar conocimiento
  eliminado.

## Preguntas abiertas

1. Para este checkout, el 80 % se midio sobre todo `app/` y `scripts/`, no solo servicios
   criticos.
2. Para este checkout, la cobertura de ramas se ejecuto como gate del comando y alcanzo el umbral.
3. Confirmar si se aprueba Playwright/Selenium para `app/web/app.js` sin romper el setup de 15 min.
4. Confirmar si Groq/Whisper se validaran solo manualmente o mediante un entorno de credenciales
   controlado fuera de la suite.
5. Confirmar si se refactorizara la instancia global de `app.main` para aislar imports.
6. Confirmar decisiones abiertas de admin: cuarentena, snapshot y autenticacion.
7. Confirmar decisiones abiertas de timeout: limite total, silencio o ambos, y entidad de turnos.
8. La validacion `TRZ-*` queda automatizada/documentada para los contratos locales y manual para
   browser, proveedor, G2 y G5 externo.

Esta spec define la estrategia y conserva la frontera manual. En este checkout se ejecuto la
suite local y se publico la evidencia anterior; no se ejecutaron navegador, microfono, TTS,
Groq/Whisper real, cronometraje G2 ni la demostracion G5 externa.
