/* Static, generated-at-review-time architecture catalog.  It never reads runtime state. */
(() => {
  "use strict";

  const generatedAt = "2026-08-08";
  const sourceSpecVersion = "0.4.0";
  const commit = "working tree/no commit";
  const source = (label, href) => ({ label, href });
  const spec06 = source("Spec 06 · diagrama integrador", "../specs/06_system_flow_diagram_specification.md");
  const rubric = source("Rubrica de evaluacion", "../docs/rubrica-evaluacion.md");
  const base = {
    status: "IMPLEMENTED",
    status_scope: "El contrato existe en el baseline local.",
    views: ["D1"],
    stages: [],
    inputs: [],
    outputs: [],
    invariants: [],
    code_refs: [],
    test_refs: [],
    source_refs: [spec06],
    related_ids: [],
    evidence: "Catalogo estatico derivado de la Spec 06; no es evidencia clinica.",
    divergences: [],
    tags: [],
    ownership: "bot",
    surface: "API",
    automated_test: false,
    manual_pending: false,
    gate: "",
    generated_at: generatedAt,
    source_spec_version: sourceSpecVersion,
    commit,
  };

  const entity = (value) => ({
    ...base,
    ...value,
    inputs: value.inputs || base.inputs,
    outputs: value.outputs || base.outputs,
    invariants: value.invariants || base.invariants,
    code_refs: value.code_refs || base.code_refs,
    test_refs: value.test_refs || base.test_refs,
    source_refs: value.source_refs || base.source_refs,
    related_ids: value.related_ids || base.related_ids,
    divergences: value.divergences || base.divergences,
    tags: value.tags || base.tags,
  });

  const entities = [];
  const add = (kind, ownership, values) => entities.push(entity({ kind, ownership, ...values }));
  const ref = (path, symbol) => symbol ? `${path} · ${symbol}` : path;

  [
    ["ACT-PATIENT-001", "Paciente", "Inicia o responde el seguimiento postoperatorio.", "usuario", "call", ["STG-CALL-001", "STG-VOICE-001"]],
    ["ACT-ADMIN-001", "Administrador", "Gestiona fuentes y su publicacion local.", "admin", "admin", ["STG-ADMIN-001"]],
    ["ACT-BROWSER-001", "Navegador", "Aporta microfono, reconocimiento y audio cuando el entorno lo permite.", "usuario", "voz", ["STG-VOICE-001", "STG-TTS-001"]],
  ].forEach(([id, title, summary, ownership, surface, stages]) => add("ACT", ownership, {
    entity_id: id, title, summary, description: `${summary} No ejecuta logica clinica por si solo.`,
    surface, stages, views: ["D1", "D2"], tags: ["actor", surface],
  }));

  [
    ["UI-ADMIN-001", "Consola de conocimiento", "Superficie para cargar, inspeccionar, publicar y olvidar fuentes.", "admin", ["STG-ADMIN-001", "STG-CLOSE-001"]],
    ["UI-CALL-001", "Interfaz de llamada", "Superficie browser/API para escuchar, responder y cerrar una llamada.", "call", ["STG-CALL-001", "STG-VOICE-001", "STG-CLOSE-001"]],
    ["UI-TEXT-FALLBACK-001", "Entrada textual de respaldo", "Permite continuar sin SpeechRecognition o tras un error de audio.", "call", ["STG-VOICE-001", "STG-AGENT-001"]],
  ].forEach(([id, title, summary, surface, stages]) => add("UI", surface === "admin" ? "admin" : "usuario", {
    entity_id: id, title, summary, description: `${summary} Mantiene el mismo contrato auditable del backend.`,
    surface, stages, views: ["D1", "D2", "D3", "D5"], code_refs: [ref("app/web", id === "UI-ADMIN-001" ? "admin.html" : "call.html")],
    test_refs: ["tests/test_http_contracts.py"], automated_test: true, tags: ["browser", surface],
  }));

  const apis = [
    ["API-ADMIN-LIST-001", "Listar fuentes", "GET /api/admin/documents", "Devuelve inventario y estados sin rutas fisicas.", "admin", "TESTED"],
    ["API-ADMIN-PREVIEW-001", "Texto extraido", "GET /api/admin/documents/{id}/preview", "Devuelve una pagina acotada y literal.", "admin", "TESTED"],
    ["API-ADMIN-SOURCE-001", "Archivo original", "GET /api/admin/documents/{id}/source", "Sirve bytes validados para la inspeccion administrativa.", "admin", "IMPLEMENTED"],
    ["API-ADMIN-TOGGLE-001", "Publicar u ocultar", "PATCH /api/admin/documents/{id}", "Cambia enabled sin reingestar.", "admin", "TESTED"],
    ["API-ADMIN-DELETE-001", "Eliminar fuente", "DELETE /api/admin/documents/{id}", "Retira el documento del corpus activo y conserva snapshots historicos.", "admin", "TESTED"],
    ["API-CALL-TURN-001", "Registrar turno", "POST /api/calls/{id}/turns", "Procesa un turno final con triaje, RAG, respuesta y fuentes.", "API", "TESTED"],
  ];
  apis.forEach(([id, title, route, summary, surface, status]) => add("API", surface === "admin" ? "admin" : "bot", {
    entity_id: id, title, summary, description: `${summary} La ruta valida entrada y entrega errores acotados.`,
    status, status_scope: status === "IMPLEMENTED" ? "Contrato local aplicado; la inspeccion de navegador sigue separada." : "Contrato automatizado local.",
    surface, views: ["D1", "D2", "D3", "D4", "D6"], stages: id.startsWith("API-ADMIN") ? ["STG-ADMIN-001"] : ["STG-CALL-001", "STG-AGENT-001", "STG-OBS-001"],
    inputs: [route], outputs: ["JSON o bytes con estado HTTP"], invariants: ["No expone secretos ni rutas internas."],
    code_refs: [ref("app/main.py", id)], test_refs: ["tests/test_api.py", "tests/test_http_contracts.py"],
    automated_test: true, tags: ["api", "http", surface.toLowerCase()],
  }));

  const stages = [
    ["STG-BOOT-001", "Preparar", "Valida hojas, joins y recorre el corpus local.", "TESTED", ["MOD-BOOTSTRAP-001"]],
    ["STG-ADMIN-001", "Administrar", "Sube, inspecciona, publica, deshabilita o borra una fuente.", "TESTED", ["MOD-DOCUMENT-001", "UI-ADMIN-001"]],
    ["STG-CALL-001", "Iniciar", "Abre la llamada browser/API y crea su contexto.", "TESTED", ["MOD-CALL-001", "UI-CALL-001"]],
    ["STG-VOICE-001", "Escuchar", "Captura voz, parcial, timeout o texto de respaldo.", "MANUAL_PENDING", ["MOD-VOICE-BROWSER-001", "STATE-VOICE-TIMEOUT-001"]],
    ["STG-TRIAGE-001", "Analizar", "Clasifica de forma determinista y sticky.", "TESTED", ["MOD-TRIAGE-001", "RULE-RED-001"]],
    ["STG-RAG-001", "Recuperar", "Busca evidencia elegible y conserva citas.", "TESTED", ["MOD-RAG-001", "RULE-RAG-ELIGIBLE-001"]],
    ["STG-AGENT-001", "Responder", "Redacta grounded o se abstiene con limites.", "TESTED", ["MOD-AGENT-001", "MOD-FALLBACK-001"]],
    ["STG-TTS-001", "Hablar", "Reproduce la respuesta en es-CO.", "MANUAL_PENDING", ["MOD-TTS-BROWSER-001"]],
    ["STG-OBS-001", "Persistir", "Guarda turnos, fuentes, alertas, eventos y metricas.", "TESTED", ["MOD-METRICS-001", "DATA-SQLITE-001"]],
    ["STG-CLOSE-001", "Cerrar", "Guarda el resumen estructurado y finaliza la llamada.", "TESTED", ["MOD-CALL-001", "API-CALL-TURN-001"]],
  ];
  stages.forEach(([id, title, summary, status, related]) => add("STG", "bot", {
    entity_id: id, title, summary, description: `${summary} La etapa es una vista documental del flujo, no una accion ejecutable.`,
    status, status_scope: status === "MANUAL_PENDING" ? "El contrato local existe; falta observar navegador/audio real." : "Pruebas locales reproducibles.",
    stages: [id], views: ["D1", "D2", "D3", "D4", "D5", "D6"], related_ids: related,
    inputs: ["Salida de la etapa anterior"], outputs: ["Estado y artefactos trazables"], invariants: ["No borrar la procedencia del flujo."],
    test_refs: ["tests/test_api.py", "tests/test_calls.py"], automated_test: true, manual_pending: status === "MANUAL_PENDING", tags: ["stage", "flow"],
  }));

  const modules = [
    ["MOD-BOOTSTRAP-001", "Bootstrap", "Valida dataset y carga el corpus local.", "TESTED", "RAG", "app/bootstrap.py"],
    ["MOD-DOCUMENT-001", "DocumentService", "Administra hash, archivo, paginas, chunks y estados.", "TESTED", "admin", "app/services/documents.py"],
    ["MOD-INGEST-001", "Ingestion", "Extrae PDF/TXT/MD y marca needs_ocr.", "TESTED", "RAG", "app/services/ingestion.py"],
    ["MOD-RAG-001", "RAG lexical", "Recupera FTS5 y filtra available + enabled.", "TESTED", "RAG", "app/services/rag.py"],
    ["MOD-TRIAGE-001", "Triage", "Aplica reglas conservadoras y sticky.", "TESTED", "seguridad", "app/services/triage.py"],
    ["MOD-AGENT-001", "AgentService", "Valida grounding, citas y abstencion.", "TESTED", "bot", "app/services/agent.py"],
    ["MOD-CALL-001", "CallService", "Persiste turnos, idempotencia, alertas y resumen.", "TESTED", "bot", "app/services/calls.py"],
    ["MOD-METRICS-001", "Metricas", "Agrega latencia, tokens, invocaciones y consultas.", "TESTED", "metricas", "app/services/metrics.py"],
    ["MOD-API-001", "Rutas FastAPI", "Expone contratos HTTP y sirve las vistas estaticas.", "TESTED", "bot", "app/main.py"],
    ["MOD-FALLBACK-001", "Fallback extractivo", "Permite una respuesta segura sin proveedor remoto.", "TESTED", "RAG", "app/services/agent.py"],
    ["MOD-VOICE-BROWSER-001", "Voz browser", "Orquesta escucha, timeout y transcripcion final.", "MANUAL_PENDING", "usuario", "app/web/app.js"],
    ["MOD-TTS-BROWSER-001", "SpeechSynthesis", "Reproduce audio es-CO en el navegador.", "MANUAL_PENDING", "bot", "app/web/app.js"],
    ["MOD-CHROMA-001", "ChromaDB", "Indice vectorial derivado de produccion.", "PROPOSED", "RAG", "specs/14_rag_vector_store_chromadb_specification.md"],
    ["MOD-LANGCHAIN-001", "LangChain", "Orquestacion futura acotada y grounded.", "PROPOSED", "bot", "specs/16_rag_langchain_orchestration_specification.md"],
    ["MOD-OBS-001", "Observabilidad avanzada", "Trazas redacted y LangSmith fail-open.", "PROPOSED", "metricas", "specs/17_rag_observability_langsmith_specification.md"],
  ];
  modules.forEach(([id, title, summary, status, ownership, path]) => add("MOD", ownership, {
    entity_id: id, title, summary, description: `${summary} El estado indica el alcance real del checkout.`,
    status, status_scope: status === "PROPOSED" ? "Especificado, no instalado ni ejecutado en el baseline." : status === "MANUAL_PENDING" ? "Contrato local; evidencia manual pendiente." : "Runtime y pruebas locales.",
    surface: ownership === "RAG" ? "datos" : ownership, views: ["D1", "D2", "D3", "D4", "D5", "D6"], code_refs: [path],
    test_refs: ["tests/test_agent.py", "tests/test_calls.py"], automated_test: status !== "PROPOSED", manual_pending: status === "MANUAL_PENDING", tags: ["module", ownership.toLowerCase()],
  }));

  [
    ["EXT-GROQ-LLM-001", "Groq · Llama permitido", "Proveedor opcional del modelo de razonamiento declarado.", "MANUAL_PENDING", "externo", "G3"],
    ["EXT-GROQ-STT-001", "Groq · Whisper", "Proveedor opcional de transcripcion de audio.", "MANUAL_PENDING", "externo", "G4"],
  ].forEach(([id, title, summary, status, ownership, gate]) => add("EXT", ownership, {
    entity_id: id, title, summary, description: `${summary} La familia y disponibilidad deben verificarse en la demo.`,
    status, status_scope: "La prueba local no reemplaza proveedor real.", surface: "voz", gate, views: ["D2", "D5", "D6"],
    inputs: ["Credencial configurada fuera del catalogo"], outputs: ["Respuesta o transcript"], invariants: ["Nunca imprimir secretos."],
    test_refs: ["tests/test_agent.py", "tests/test_voice.py"], automated_test: true, manual_pending: true, tags: ["provider", "external"],
  }));

  [
    ["DATA-SQLITE-001", "SQLite + FTS5", "Autoridad local para documentos, chunks, llamadas y fuentes.", "TESTED", "datos", "D6"],
    ["DATA-SOURCE-001", "Fuente y snapshot", "Cita con pagina, chunk, revision y snapshot historico.", "TESTED", "datos", "D3"],
    ["DATA-TURN-001", "Turno", "Transcripcion, respuesta, triaje y consumo de un turno.", "TESTED", "datos", "D2"],
    ["DATA-EVENTS-001", "Eventos de metricas", "Eventos acotados para latencia, voz y uso.", "TESTED", "metricas", "D6"],
    ["DATA-CHROMA-001", "Indice vectorial", "Indice derivado propuesto y reconciliable.", "PROPOSED", "RAG", "D4"],
    ["DATA-FILES-001", "Archivos controlados", "Originales de fuentes locales sin ruta expuesta al cliente.", "TESTED", "datos", "D3"],
  ].forEach(([id, title, summary, status, ownership, view]) => add("DATA", ownership, {
    entity_id: id, title, summary, description: `${summary} No contiene datos reales en este artefacto.`,
    status, status_scope: status === "PROPOSED" ? "Objetivo de migracion, no runtime." : "Persistencia local reproducible.", views: [view, "D6"],
    outputs: ["Registro trazable"], invariants: ["No reutilizar snapshots historicos como evidencia nueva."], code_refs: ["app/database.py"],
    test_refs: ["tests/test_database.py", "tests/test_metrics.py"], automated_test: true, tags: ["persistence", "data"],
  }));

  const states = [
    ["STATE-DOC-AVAILABLE-001", "Documento disponible", "Tiene texto extraible y puede publicarse.", "TESTED", "D3"],
    ["STATE-DOC-DISABLED-001", "Documento deshabilitado", "Se conserva pero queda fuera del RAG.", "TESTED", "D3"],
    ["STATE-DOC-OCR-001", "Necesita OCR", "El original puede existir, pero no hay texto utilizable.", "TESTED", "D3"],
    ["STATE-DOC-PROCESSING-001", "Procesando", "No debe aparecer como fuente elegible mientras se procesa.", "TESTED", "D3"],
    ["STATE-DOC-ERROR-001", "Error documental", "No expone contenido residual ni se publica.", "TESTED", "D3"],
    ["STATE-DOC-DELETED-001", "Eliminado", "La fuente deja de aparecer en consultas nuevas.", "TESTED", "D3"],
    ["STATE-VOICE-IDLE-001", "Escucha inactiva", "Aun no se captura un turno.", "TESTED", "D5"],
    ["STATE-VOICE-LISTENING-001", "Escuchando", "El navegador recibe voz del paciente.", "MANUAL_PENDING", "D5"],
    ["STATE-VOICE-PARTIAL-001", "Parcial", "Borrador visible que no crea turno clinico.", "TESTED", "D5"],
    ["STATE-VOICE-TIMEOUT-001", "Timeout de escucha", "Termina el intento sin crear turno y ofrece reintento.", "TESTED", "D5"],
    ["STATE-VOICE-ERROR-001", "Error de reconocimiento", "Falla de voz con camino textual seguro.", "MANUAL_PENDING", "D5"],
    ["STATE-VOICE-NO-RESPONSE-001", "Sin respuesta", "No hubo transcript final antes de terminar la escucha.", "TESTED", "D5"],
    ["STATE-VOICE-RETRY-001", "Reintento", "El paciente puede volver a intentar o escribir.", "TESTED", "D5"],
    ["STATE-VOICE-PROCESSING-001", "Procesando turno", "El transcript final espera respuesta auditable.", "TESTED", "D2"],
    ["STATE-VOICE-SPEAK-001", "Audio del agente", "SpeechSynthesis reproduce el canal hablado.", "MANUAL_PENDING", "D5"],
    ["STATE-VOICE-TEXT-001", "Texto de respaldo", "La llamada conserva el contrato al cambiar de canal.", "TESTED", "D5"],
    ["STATE-VOICE-PERMISSION-001", "Permiso de microfono", "El navegador puede negar acceso sin perder el camino textual.", "MANUAL_PENDING", "D5"],
  ];
  states.forEach(([id, title, summary, status, view]) => add("STATE", "bot", {
    entity_id: id, title, summary, description: `${summary} El estado tecnico nunca se presenta como una decision clinica.`,
    status, status_scope: status === "MANUAL_PENDING" ? "Contrato local; requiere navegador compatible." : "Contrato y prueba local.", views: [view],
    stages: view === "D3" ? ["STG-ADMIN-001"] : ["STG-VOICE-001"], outputs: ["Estado observable y proximo paso seguro"],
    code_refs: ["app/web/app.js", "app/services/calls.py"], test_refs: ["tests/test_timeout.py", "tests/test_voice.py"],
    automated_test: true, manual_pending: status === "MANUAL_PENDING", tags: ["state", view.toLowerCase()],
  }));

  [
    ["RULE-RED-001", "Alerta roja", "Escala inmediatamente y nunca baja de nivel.", "seguridad", "TESTED"],
    ["RULE-YELLOW-001", "Alerta amarilla", "Indica contacto oportuno y se conserva en el resumen.", "seguridad", "TESTED"],
    ["RULE-UNKNOWN-001", "Aclaracion", "Pide informacion antes de concluir cuando falta evidencia.", "seguridad", "TESTED"],
    ["RULE-TRIAGE-STICKY-001", "Nivel sticky", "El nivel previo limita cualquier degradacion posterior.", "seguridad", "TESTED"],
    ["RULE-RAG-ELIGIBLE-001", "Elegibilidad RAG", "Solo available + enabled entra en consultas nuevas.", "RAG", "TESTED"],
    ["RULE-SECURITY-001", "Contenido no confiable", "Paciente, corpus y preview se tratan como datos, no instrucciones.", "seguridad", "TESTED"],
  ].forEach(([id, title, summary, ownership, status]) => add("RULE", ownership, {
    entity_id: id, title, summary, description: `${summary} La regla determinista prevalece ante una respuesta remota.`,
    status, status_scope: "Regla local automatizada.", views: ["D3", "D4", "D5"], stages: ["STG-TRIAGE-001", "STG-RAG-001"],
    invariants: [summary], code_refs: [ownership === "RAG" ? "app/services/rag.py" : "app/services/triage.py"],
    test_refs: ["tests/test_triage.py", "tests/test_agent.py"], automated_test: true, tags: ["rule", ownership.toLowerCase()],
  }));

  [
    ["MET-VOICE-LATENCY-001", "Latencia de voz", "Fin de habla a inicio de audio del agente.", "D6", "MANUAL_PENDING"],
    ["MET-VOICE-TIMEOUT-001", "Timeout de escucha", "Intentos que terminan por el limite configurado.", "D5", "TESTED"],
    ["MET-TOKENS-001", "Tokens", "Entrada y salida por turno y llamada.", "D6", "TESTED"],
    ["MET-MODEL-CALLS-001", "Invocaciones", "Numero de llamadas al modelo por turno.", "D6", "TESTED"],
    ["MET-RAG-QUERIES-001", "Consultas RAG", "Consultas y fuentes recuperadas.", "D4", "TESTED"],
    ["MET-COST-001", "Costo", "Costo estimado remoto o costo local cero documentado.", "D6", "PROPOSED"],
  ].forEach(([id, title, summary, view, status]) => add("MET", "metricas", {
    entity_id: id, title, summary, description: `${summary} La fuente y timestamps deben ser visibles antes de interpretar el numero.`,
    status, status_scope: status === "MANUAL_PENDING" ? "Requiere timestamps reales del navegador." : status === "PROPOSED" ? "Formula futura dependiente de precios/proveedor." : "Agregacion local.",
    views: [view, "D6"], inputs: ["Eventos y timestamps acotados"], outputs: ["Valor agregado o pendiente"],
    code_refs: ["app/services/metrics.py"], test_refs: ["tests/test_metrics.py"], automated_test: status !== "PROPOSED", manual_pending: status === "MANUAL_PENDING", tags: ["metric", "evidence"],
  }));

  [
    ["TRZ-SURFACES-001", "Superficies", "Relaciona admin, call, API y voz con sus contratos.", "TESTED", "D1"],
    ["TRZ-ADMIN-SOURCE-001", "Trazabilidad del original", "Distingue bytes originales y texto extraido.", "IMPLEMENTED", "D3"],
    ["TRZ-ADMIN-PREVIEW-001", "Trazabilidad de preview", "Conserva pagina, chunk logico y revision sin mutar el corpus.", "TESTED", "D3"],
    ["TRZ-CITATION-001", "Cita grounded", "Conecta respuesta, fuente, pagina y revision.", "TESTED", "D4"],
    ["TRZ-TIMEOUT-SEPARATION-001", "Timeout separado", "Un intento parcial no se convierte en turno clinico.", "TESTED", "D5"],
    ["TRZ-METRICS-001", "Metricas trazables", "Relaciona eventos con turnos y llamada.", "TESTED", "D6"],
  ].forEach(([id, title, summary, status, view]) => add("TRZ", "bot", {
    entity_id: id, title, summary, description: `${summary} La traza documenta el vinculo, no sustituye una observacion manual.`,
    status, status_scope: "Matriz documental y pruebas locales.", views: [view], related_ids: ["SPEC-BASE-001", "SPEC-TEST-001"],
    test_refs: ["tests/test_http_contracts.py", "tests/test_metrics.py"], automated_test: true, tags: ["traceability", view.toLowerCase()],
  }));

  [
    ["TEST-TIMEOUT-001", "Pruebas de timeout", "Verifican no-turno, late transcript, reintento y fallback textual.", "TESTED", "D5"],
    ["TEST-ADMIN-001", "Pruebas admin", "Verifican upload, preview, toggle y delete.", "TESTED", "D3"],
    ["TEST-RAG-001", "Pruebas de conocimiento vivo", "Verifican aprender y olvidar sin reiniciar.", "TESTED", "D4"],
    ["TEST-VOICE-001", "Smoke de voz", "Recorrido manual de microfono, transcript y audio.", "MANUAL_PENDING", "D5"],
  ].forEach(([id, title, summary, status, view]) => add("TEST", "metricas", {
    entity_id: id, title, summary, description: `${summary} Una prueba automatizada no aprueba por si sola G4 o evidencia externa.`,
    status, status_scope: status === "MANUAL_PENDING" ? "Falta navegador y audio observado." : "Comando local ejecutado.", views: [view],
    test_refs: ["python -m pytest -q --basetemp <temp>"], source_refs: [source("Spec 07 · estrategia de pruebas", "../specs/07_testing_unit_integration_specification.md")],
    automated_test: status === "TESTED", manual_pending: status === "MANUAL_PENDING", tags: ["test", "evidence"],
  }));

  [
    ["GATE-G1-001", "Entregables", "Repositorio, arquitectura, informe y video exigidos por el reto.", "MANUAL_PENDING", "G1"],
    ["GATE-G2-001", "Setup en 15 minutos", "El arranque debe medirse desde un entorno limpio.", "MANUAL_PENDING", "G2"],
    ["GATE-G3-001", "Modelo permitido", "La familia declarada y la disponibilidad real deben coincidir.", "MANUAL_PENDING", "G3"],
    ["GATE-G4-001", "Voz en tiempo real", "Requiere microfono, transcripcion y audio observados.", "MANUAL_PENDING", "G4"],
    ["GATE-G5-001", "Conocimiento vivo", "Requiere aprender, consultar, eliminar y olvidar una fuente externa.", "MANUAL_PENDING", "G5"],
  ].forEach(([id, title, summary, status, gate]) => add("GATE", "metricas", {
    entity_id: id, title, summary, description: `${summary} Las pruebas locales aportan evidencia parcial, no aprobacion del gate.`,
    status, status_scope: "Evidencia requerida por la rubrica; pendiente de recorrido externo o manual.", views: ["D6"], gate,
    inputs: ["Recorrido documentado"], outputs: ["Resultado TESTED o MANUAL_PENDING"], invariants: ["No inferir aprobacion desde presencia del catalogo."],
    source_refs: [rubric, spec06], test_refs: ["readme/04_metricas_y_evidencia.md"], automated_test: false, manual_pending: true, tags: ["gate", gate.toLowerCase()],
  }));

  add("RULE", "seguridad", {
    entity_id: "FUT-AUTH-001", title: "Autenticacion empresarial", summary: "No forma parte del MVP local.",
    description: "Es un limite explicito: publicar el admin fuera de localhost requiere autenticacion, CSRF y autorizacion.",
    status: "OUT_OF_SCOPE", status_scope: "Limite del MVP", surface: "admin", views: ["D1", "D3"],
    source_refs: [spec06], tags: ["out-of-scope", "security"],
  });

  const views = [
    ["D1", "Mapa de actores y ownership", "Quien participa, que posee cada bloque y donde vive.", ["ACT-PATIENT-001", "ACT-ADMIN-001", "UI-ADMIN-001", "UI-CALL-001", "MOD-API-001"]],
    ["D2", "Llamada e idempotencia", "Como transcurre una llamada, escucha, timeout y turno final.", ["STG-CALL-001", "STG-VOICE-001", "API-CALL-TURN-001", "STATE-VOICE-TIMEOUT-001"]],
    ["D3", "Ciclo documental", "Como se sube, inspecciona, publica, deshabilita y elimina conocimiento.", ["STG-ADMIN-001", "API-ADMIN-SOURCE-001", "STATE-DOC-OCR-001", "RULE-RAG-ELIGIBLE-001"]],
    ["D4", "Triaje, RAG y grounding", "Como se separan seguridad, recuperacion, citas y abstencion.", ["MOD-TRIAGE-001", "MOD-RAG-001", "MOD-AGENT-001", "RULE-SECURITY-001"]],
    ["D5", "Estados de voz", "Que significa cada estado y como funciona el fallback.", ["STATE-VOICE-TIMEOUT-001", "STATE-VOICE-PARTIAL-001", "MOD-TTS-BROWSER-001", "TRZ-TIMEOUT-SEPARATION-001"]],
    ["D6", "Persistencia y evidencia", "Que se persiste, que se mide y que falta observar.", ["DATA-SQLITE-001", "MET-VOICE-LATENCY-001", "GATE-G4-001", "GATE-G5-001"]],
  ].map(([id, title, question, entityIds]) => ({ id, title, question, entity_ids: entityIds, source_refs: [spec06] }));

  const stagesForFlow = stages.map(([id, title, summary, status, related]) => ({ id, title, summary, status, related_ids: related }));
  const glossary = [
    ["available / enabled / rag_eligible", "Disponible significa texto extraible; enabled publica; rag_eligible resume ambas condiciones."],
    ["FTS5 y chunk", "FTS5 recupera texto local; un chunk es un fragmento trazable de una pagina."],
    ["grounding y abstencion", "Grounding conecta una respuesta con evidencia; abstencion evita inventar cuando falta."],
    ["late_transcript", "Transcript que llega despues del timeout; se registra, pero no crea turno clinico."],
    ["IMPLEMENTED / TESTED / MANUAL_PENDING", "Estados del catalogo: existe, tiene verificacion local o aun necesita evidencia manual."],
    ["PROPOSED / OUT_OF_SCOPE", "Capacidad futura especificada o limite deliberado del MVP."],
    ["P50/P95, tokens, llamadas y costo", "Metricas de latencia, consumo e invocaciones; algunas dependen de timestamps/proveedor real."],
  ];

  window.ARCHITECTURE_CATALOG = Object.freeze({
    meta: Object.freeze({ generated_at: generatedAt, source_spec_version: sourceSpecVersion, commit, precedence: ["specs canonicas", "vista publicada", "codigo", "pruebas y evidencia"] }),
    entities: Object.freeze(entities.map((item) => Object.freeze(item))),
    stages: Object.freeze(stagesForFlow),
    views: Object.freeze(views),
    glossary: Object.freeze(glossary),
  });
})();
