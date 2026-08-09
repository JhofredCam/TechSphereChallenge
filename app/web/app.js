(() => {
  "use strict";

  const page = document.body.dataset.page;
  const $ = (selector) => document.querySelector(selector);

  function messageFrom(value) {
    if (!value) return "Error desconocido";
    if (typeof value === "string") return value;
    if (Array.isArray(value)) return value.map((item) => item.msg || String(item)).join(", ");
    if (value.detail) return messageFrom(value.detail);
    if (value.error_code && value.message) return `${value.error_code}: ${value.message}`;
    return value.message || value.error_code || JSON.stringify(value);
  }

  async function api(path, options = {}) {
    const response = await fetch(path, options);
    const contentType = response.headers.get("content-type") || "";
    const data = contentType.includes("application/json") ? await response.json() : await response.text();
    if (!response.ok) throw new Error(messageFrom(data));
    return data;
  }

  function setStatus(node, text, kind = "") {
    if (!node) return;
    node.textContent = text;
    node.className = `form-status ${kind}`.trim();
  }

  function formatBytes(bytes) {
    if (!Number.isFinite(bytes)) return "";
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  }

  function statusLabel(status) {
    return {
      available: "Disponible",
      needs_ocr: "Necesita revision",
      processing: "Procesando",
      error: "Error al procesar",
    }[status] || status;
  }

  function publicationLabel(documentRecord) {
    if (documentRecord.status !== "available") {
      return { className: "publication-unavailable", text: "No publicable" };
    }
    return documentRecord.enabled
      ? { className: "publication-enabled", text: "Disponible para el agente" }
      : { className: "publication-disabled", text: "No disponible para el agente" };
  }

  const previewState = { documentRecord: null, page: 1 };

  async function loadPreview(documentRecord, page = 1) {
    const panel = $("#preview-panel");
    const pageInput = $("#preview-page");
    const documentLabel = $("#preview-document");
    const meta = $("#preview-meta");
    const text = $("#preview-text");
    if (!panel || !pageInput || !documentLabel || !meta || !text) return;
    previewState.documentRecord = documentRecord;
    previewState.page = page;
    panel.hidden = false;
    $(".admin-workspace")?.classList.add("preview-open");
    documentLabel.textContent = documentRecord.filename;
    pageInput.value = String(page);
    text.textContent = "";
    meta.textContent = "Cargando texto extraido...";
    setStatus($("#preview-status"), "");
    try {
      const data = await api(
        `/api/admin/documents/${encodeURIComponent(documentRecord.id)}/preview?page=${encodeURIComponent(page)}&offset=0&limit=8000`,
      );
      const preview = data.preview || {};
      if (preview.available) {
        text.textContent = preview.text || "";
        meta.textContent = `Pagina ${preview.page} de ${preview.page_count} · ${preview.total_chars} caracteres${preview.truncated ? " · vista truncada a 8000" : ""}`;
        setStatus($("#preview-status"), "Se muestra texto plano no ejecutable. No se interpreta Markdown ni HTML.", "success");
      } else {
        text.textContent = "";
        meta.textContent = `Pagina ${preview.page || page} de ${preview.page_count || documentRecord.page_count || 0}`;
        setStatus($("#preview-status"), `Preview no disponible: ${preview.reason || "sin texto extraible"}.`, "error");
      }
    } catch (error) {
      text.textContent = "";
      meta.textContent = "";
      setStatus($("#preview-status"), error.message, "error");
    }
  }

  function renderDocumentRow(documentRecord) {
    const row = document.createElement("tr");
    const nameCell = document.createElement("td");
    const name = document.createElement("div");
    name.className = "document-name";
    name.title = documentRecord.filename;
    name.textContent = documentRecord.filename;
    const meta = document.createElement("div");
    meta.className = "document-meta";
    const dates = [documentRecord.created_at, documentRecord.processed_at]
      .filter(Boolean)
      .map((value) => String(value).replace("T", " "))
      .join(" → ");
    meta.textContent = `${formatBytes(documentRecord.size_bytes)}${dates ? ` · ${dates}` : ""}`;
    nameCell.append(name, meta);

    const statusCell = document.createElement("td");
    statusCell.dataset.label = "Procesamiento";
    const processingBadge = document.createElement("span");
    processingBadge.className = `status-badge status-${documentRecord.status}`;
    processingBadge.textContent = statusLabel(documentRecord.status);
    statusCell.appendChild(processingBadge);

    const publicationCell = document.createElement("td");
    publicationCell.dataset.label = "Publicacion";
    const publication = publicationLabel(documentRecord);
    const publicationBadge = document.createElement("span");
    publicationBadge.className = `status-badge ${publication.className}`;
    publicationBadge.textContent = publication.text;
    publicationCell.appendChild(publicationBadge);

    const contentCell = document.createElement("td");
    contentCell.dataset.label = "Contenido";
    contentCell.className = "document-content";
    contentCell.textContent = `${documentRecord.page_count || 0} paginas · ${documentRecord.chunk_count || 0} fragmentos · ${formatBytes(documentRecord.size_bytes)}`;

    const actionCell = document.createElement("td");
    actionCell.dataset.label = "Acciones";
    actionCell.className = "document-actions";
    const previewButton = document.createElement("button");
    previewButton.className = "admin-action";
    previewButton.type = "button";
    previewButton.textContent = "Previsualizar";
    previewButton.setAttribute("aria-label", `Previsualizar ${documentRecord.filename}`);
    previewButton.addEventListener("click", () => {
      void loadPreview(documentRecord);
    });
    actionCell.appendChild(previewButton);

    if (documentRecord.status === "available") {
      const toggleButton = document.createElement("button");
      toggleButton.className = "admin-action";
      toggleButton.type = "button";
      toggleButton.textContent = documentRecord.enabled ? "Deshabilitar" : "Habilitar";
      toggleButton.addEventListener("click", async () => {
        const nextEnabled = !documentRecord.enabled;
        const action = nextEnabled ? "habilitar" : "deshabilitar";
        if (!window.confirm(`Confirma ${action} ${documentRecord.filename}.`)) return;
        toggleButton.disabled = true;
        try {
          const result = await api(`/api/admin/documents/${encodeURIComponent(documentRecord.id)}`, {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ enabled: nextEnabled }),
          });
          const publicationState = nextEnabled ? "habilitado" : "deshabilitado";
          setStatus($("#documents-status"), result.changed ? `Documento ${publicationState}.` : "Sin cambios: estado ya aplicado.", "success");
          await loadDocuments();
        } catch (error) {
          toggleButton.disabled = false;
          setStatus($("#documents-status"), error.message, "error");
        }
      });
      actionCell.appendChild(toggleButton);
    }

    const deleteButton = document.createElement("button");
    deleteButton.className = "delete-button";
    deleteButton.type = "button";
    deleteButton.textContent = "Eliminar";
    deleteButton.setAttribute("aria-label", `Eliminar ${documentRecord.filename}`);
    deleteButton.addEventListener("click", async () => {
      if (!window.confirm(`Eliminar ${documentRecord.filename} de forma permanente? Esta accion no se puede deshacer.`)) return;
      deleteButton.disabled = true;
      try {
        await api(`/api/admin/documents/${encodeURIComponent(documentRecord.id)}`, { method: "DELETE" });
        setStatus($("#documents-status"), "Documento eliminado. El agente lo olvida sin reiniciar.", "success");
        await loadDocuments();
      } catch (error) {
        deleteButton.disabled = false;
        setStatus($("#documents-status"), error.message, "error");
      }
    });
    actionCell.appendChild(deleteButton);
    row.append(nameCell, statusCell, publicationCell, contentCell, actionCell);
    return row;
  }

  async function loadDocuments() {
    const rows = $("#document-rows");
    if (!rows) return;
    try {
      const data = await api("/api/admin/documents");
      const documents = Array.isArray(data) ? data : (data.documents || []);
      rows.replaceChildren();
      if (!documents.length) {
        const empty = document.createElement("tr");
        const emptyCell = document.createElement("td");
        emptyCell.colSpan = 5;
        emptyCell.className = "empty-state";
        emptyCell.textContent = "Aun no hay documentos. Agrega la primera fuente.";
        empty.appendChild(emptyCell);
        rows.appendChild(empty);
      } else {
        documents.forEach((item) => rows.appendChild(renderDocumentRow(item)));
      }
      setStatus($("#documents-status"), `${documents.length} fuente${documents.length === 1 ? "" : "s"} en el corpus.`, "success");
    } catch (error) {
      setStatus($("#documents-status"), error.message, "error");
    }
  }

  function initAdmin() {
    const fileInput = $("#knowledge-file");
    const fileLabel = $("#file-label");
    fileInput?.addEventListener("change", () => {
      const file = fileInput.files?.[0];
      if (file) fileLabel.textContent = `${file.name} · ${formatBytes(file.size)}`;
    });

    $("#upload-form")?.addEventListener("submit", async (event) => {
      event.preventDefault();
      const file = fileInput?.files?.[0];
      if (!file) return;
      const button = $("#upload-button");
      button.disabled = true;
      setStatus($("#upload-status"), "Procesando y creando el indice...");
      const formData = new FormData();
      formData.append("file", file);
      try {
        const record = await api("/api/admin/documents", { method: "POST", body: formData });
        setStatus($("#upload-status"), `${record.filename}: ${statusLabel(record.status)}.`, "success");
        event.target.reset();
        fileLabel.textContent = "Elegir un documento";
        await loadDocuments();
      } catch (error) {
        setStatus($("#upload-status"), error.message, "error");
      } finally {
        button.disabled = false;
      }
    });
    $("#refresh-documents")?.addEventListener("click", loadDocuments);
    $("#preview-close")?.addEventListener("click", () => {
      $("#preview-panel").hidden = true;
      $(".admin-workspace")?.classList.remove("preview-open");
      previewState.documentRecord = null;
    });
    $("#preview-load")?.addEventListener("click", () => {
      if (!previewState.documentRecord) return;
      const page = Number($("#preview-page")?.value || 1);
      if (Number.isInteger(page) && page > 0) void loadPreview(previewState.documentRecord, page);
    });
    loadDocuments();
  }

  const TEXT_INPUT_TIMING = Object.freeze({
    mode: "text",
    speech_ended_at: null,
    audio_started_at: null,
  });
  const LISTEN_STATES = Object.freeze([
    "LISTENING",
    "PARTIAL",
    "PROCESSING",
    "NO_RESPONSE",
    "LISTEN_TIMEOUT",
    "RECOGNITION_ERROR",
    "RETRY_REQUIRED",
  ]);
  const callState = {
    id: null,
    recognition: null,
    listening: false,
    closed: false,
    currentAttempt: null,
    voiceSupported: false,
    patientListenTimeoutMs: null,
    healthPromise: null,
    callEnabled: false,
    processing: false,
  };

  function syncCallControls() {
    const enabled = callState.callEnabled && !callState.closed && !callState.processing;
    [$("#turn-text"), $("#send-text"), $("#finish-call")].forEach((node) => {
      if (node) node.disabled = !enabled;
    });
    const micButton = $("#mic-button");
    if (micButton) micButton.disabled = !enabled || !callState.voiceSupported;
  }

  function setCallEnabled(enabled) {
    callState.callEnabled = enabled;
    $("#conversation-panel")?.classList.toggle("is-disabled", !enabled);
    syncCallControls();
  }

  function setTurnBusy(busy) {
    callState.processing = busy;
    syncCallControls();
  }

  function createClientId(prefix) {
    const random = typeof crypto !== "undefined" && typeof crypto.randomUUID === "function"
      ? crypto.randomUUID().replace(/-/g, "")
      : `${Date.now()}_${Math.random().toString(16).slice(2)}`;
    return `${prefix}_${random}`.slice(0, 128);
  }

  function monotonicNow() {
    return performance.now();
  }

  function setVoiceState(state, attempt = callState.currentAttempt) {
    if (!LISTEN_STATES.includes(state)) return;
    if (attempt) attempt.state = state;
    const node = $("#voice-state");
    if (node) node.textContent = `Estado: ${state}`;
  }

  function updateListenTimer(attempt, elapsed = null) {
    const node = $("#listen-timer");
    if (!node || !attempt?.startedAt || !Number.isFinite(callState.patientListenTimeoutMs)) return;
    const duration = Number.isFinite(elapsed) ? elapsed : Math.max(0, monotonicNow() - attempt.startedAt);
    node.textContent = `Escucha ${Math.round(duration)} ms de ${callState.patientListenTimeoutMs} ms`;
  }

  function clearListenTimer(attempt) {
    if (!attempt) return;
    if (attempt.timerId !== null) window.clearTimeout(attempt.timerId);
    attempt.timerId = null;
    updateListenTimer(attempt);
  }

  function clearPartial() {
    const node = $("#partial-transcript");
    if (!node) return;
    node.textContent = "";
    node.hidden = true;
  }

  function showPartial(text) {
    const node = $("#partial-transcript");
    if (!node) return;
    node.textContent = text ? `Borrador no clinico: ${text}` : "";
    node.hidden = !text;
  }

  async function registerVoiceEvent(attempt, eventType, extra = {}) {
    if (!callState.id || !attempt?.listenId) return null;
    const payload = {
      event_type: eventType,
      listen_id: attempt.listenId,
      client_turn_id: attempt.clientTurnId,
      configured_timeout_ms: callState.patientListenTimeoutMs,
      elapsed_ms: attempt.startedAt ? Math.max(0, monotonicNow() - attempt.startedAt) : null,
      locale: "es-CO",
      implementation: attempt.implementation,
      ...extra,
    };
    try {
      return await api(`/api/calls/${encodeURIComponent(callState.id)}/voice-events`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
    } catch (error) {
      if (attempt.state !== "PROCESSING" && !attempt.terminal) {
        setStatus($("#call-status"), `No se pudo registrar el estado de voz: ${error.message}`, "error");
      }
      return null;
    }
  }

  function finishAttemptControls(attempt, label = "Hablar") {
    if (callState.currentAttempt !== attempt) return;
    callState.listening = false;
    const micButton = $("#mic-button");
    micButton?.classList.remove("listening");
    const micLabel = $("#mic-label");
    if (micLabel) micLabel.textContent = label;
  }

  function requireListenTimeout() {
    if (Number.isInteger(callState.patientListenTimeoutMs)) return Promise.resolve();
    if (!callState.healthPromise) {
      callState.healthPromise = api("/health").then((health) => {
        const timeout = Number(health.patient_listen_timeout_ms);
        if (!Number.isInteger(timeout) || timeout < 1000 || timeout > 300000) {
          throw new Error("/health no devolvio un timeout de escucha valido");
        }
        callState.patientListenTimeoutMs = timeout;
      }).catch((error) => {
        callState.healthPromise = null;
        throw error;
      });
    }
    return callState.healthPromise;
  }

  function renderTriage(result) {
    const triage = result?.triage || result;
    if (!triage) return;
    const level = triage.level || result.level || "unknown";
    const badge = $("#triage-badge");
    if (badge) {
      badge.className = `triage-badge triage-${level}`;
      badge.textContent = ({ red: "Rojo", yellow: "Amarillo", green: "Verde", unknown: "Aclarar" })[level] || level;
    }
    const rationale = $("#triage-rationale");
    if (rationale) rationale.textContent = triage.rationale || "Se actualizo la señal de seguridad.";
    const alert = $("#triage-alert");
    if (alert) {
      alert.hidden = !triage.alert;
      alert.textContent = triage.alert
        ? (level === "red" ? "Alerta inmediata: busque urgencias o contacte ahora al equipo clinico." : "Alerta: contacte oportunamente al equipo clinico.")
        : "";
    }
  }

  function renderSources(sources) {
    const list = $("#source-list");
    if (!list) return;
    list.replaceChildren();
    if (!sources?.length) {
      const empty = document.createElement("li");
      empty.className = "empty-state";
      empty.textContent = "Sin evidencia recuperada en este turno.";
      list.appendChild(empty);
      return;
    }
    sources.forEach((source) => {
      const item = document.createElement("li");
      const citation = document.createElement("span");
      citation.className = "source-citation";
      const shortChunk = source.chunk_id ? ` · chunk ${String(source.chunk_id).slice(0, 12)}` : "";
      const score = Number.isFinite(Number(source.score)) ? ` · score ${Number(source.score).toFixed(2)}` : "";
      citation.textContent = `${source.citation || source.filename || "Fuente"}${shortChunk}${score}`;
      const revision = document.createElement("span");
      revision.className = "source-revision";
      revision.textContent = source.corpus_revision ? `Revision ${source.corpus_revision}` : "Fuente local";
      item.append(citation, revision);
      list.appendChild(item);
    });
  }

  function renderTurn(speaker, text, sources = []) {
    const list = $("#turn-list");
    if (!list) return;
    list.querySelector(".empty-conversation")?.remove();
    const turn = document.createElement("article");
    turn.className = `turn ${speaker === "patient" ? "patient" : "agent"}`;
    const label = document.createElement("div");
    label.className = "turn-label";
    label.textContent = speaker === "patient" ? "Paciente" : "Agente";
    const body = document.createElement("p");
    body.className = "turn-text";
    body.textContent = text;
    turn.append(label, body);
    if (speaker === "agent" && sources.length) {
      const sourceWrap = document.createElement("div");
      sourceWrap.className = "turn-sources";
      sources.slice(0, 3).forEach((source) => {
        const sourceTag = document.createElement("span");
        sourceTag.className = "source-mini";
        const shortChunk = source.chunk_id ? ` · ${String(source.chunk_id).slice(0, 8)}` : "";
        sourceTag.textContent = `${source.citation || "Fuente"}${shortChunk}`;
        sourceWrap.appendChild(sourceTag);
      });
      turn.appendChild(sourceWrap);
    }
    list.appendChild(turn);
    list.scrollTop = list.scrollHeight;
  }

  function speak(text, onStart = null) {
    if (!("speechSynthesis" in window) || !text) return false;
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = "es-CO";
    utterance.rate = .98;
    utterance.onstart = () => {
      if (typeof onStart === "function") onStart(new Date().toISOString());
    };
    window.speechSynthesis.speak(utterance);
    return true;
  }

  async function recordVoiceTiming(callId, agentTurnId, timing, audioStartedAt) {
    if (!callId || !agentTurnId || !timing?.speech_ended_at || !audioStartedAt) return;
    try {
      await api(`/api/calls/${encodeURIComponent(callId)}/turns/${encodeURIComponent(agentTurnId)}/voice-timing`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          speech_ended_at: timing.speech_ended_at,
          audio_started_at: audioStartedAt,
        }),
      });
    } catch (error) {
      setStatus($("#call-status"), `Turno registrado; no se pudo guardar la latencia de voz: ${error.message}`, "error");
    }
  }

  async function sendTurn(text, inputTiming = TEXT_INPUT_TIMING, attempt = null) {
    if (!callState.id || callState.closed || !text.trim()) return;
    const normalized = text.trim();
    const callId = callState.id;
    const turnAttempt = attempt || {
      listenId: createClientId("listen"),
      clientTurnId: createClientId("client_turn"),
      state: "PROCESSING",
      terminal: false,
      startedAt: null,
    };
    turnAttempt.state = "PROCESSING";
    turnAttempt.terminal = true;
    setTurnBusy(true);
    const sendButton = $("#send-text");
    if (sendButton) sendButton.disabled = true;
    if (!inputTiming?.duplicate) renderTurn("patient", normalized);
    setStatus($("#call-status"), "El agente esta consultando el conocimiento disponible...");
    try {
      const response = await api(`/api/calls/${encodeURIComponent(callState.id)}/turns`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          text: normalized,
          client_turn_id: turnAttempt.clientTurnId,
          listen_id: turnAttempt.listenId,
          elapsed_ms: inputTiming?.elapsed_ms ?? null,
        }),
      });
      const answer = response.text || response.answer || response.response || "No hay respuesta disponible.";
      if (!response.duplicate) {
        renderTurn("agent", answer, response.sources || []);
        renderTriage(response);
        renderSources(response.sources || []);
      }
      const voiceInput = inputTiming?.mode === "voice" ? inputTiming : null;
      speak(answer, (audioStartedAt) => {
        void recordVoiceTiming(callId, response.agent_turn_id, voiceInput, audioStartedAt);
      });
      setStatus($("#call-status"), response.duplicate ? "Turno ya registrado; se reutilizo la respuesta." : "Turno registrado.", "success");
    } catch (error) {
      setStatus($("#call-status"), error.message, "error");
    } finally {
      if (sendButton) sendButton.disabled = false;
      setTurnBusy(false);
    }
  }

  function initRecognition() {
    const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    const micButton = $("#mic-button");
    const support = $("#voice-support");
    if (!Recognition) {
      callState.voiceSupported = false;
      if (support) support.textContent = "SpeechRecognition no esta disponible; usa el texto de respaldo.";
      if (micButton) micButton.disabled = true;
      setVoiceState("RECOGNITION_ERROR");
      return;
    }
    callState.voiceSupported = true;
    if (support) support.textContent = "Microfono listo · SpeechRecognition es-CO";
    micButton?.addEventListener("click", async () => {
      if (callState.listening) {
        callState.recognition?.stop();
        return;
      }
      if (callState.closed) return;
      const previousAttempt = callState.currentAttempt;
      if (previousAttempt && previousAttempt.terminal && previousAttempt.state !== "PROCESSING") {
        void registerVoiceEvent(previousAttempt, "retry");
      }
      try {
        await requireListenTimeout();
      } catch (error) {
        setVoiceState("RECOGNITION_ERROR");
        setStatus($("#call-status"), `No se pudo obtener la configuracion de escucha: ${error.message}. Usa el texto de respaldo.`, "error");
        return;
      }
      const recognition = new Recognition();
      const implementation = window.SpeechRecognition ? "SpeechRecognition" : "webkitSpeechRecognition";
      const attempt = {
        listenId: createClientId("listen"),
        clientTurnId: createClientId("client_turn"),
        implementation,
        state: "LISTENING",
        startedAt: null,
        deadline: null,
        timerId: null,
        terminal: false,
        finalSubmitted: false,
      };
      callState.recognition = recognition;
      callState.currentAttempt = attempt;
      recognition.lang = "es-CO";
      recognition.continuous = false;
      recognition.interimResults = true;
      recognition.maxAlternatives = 1;
      recognition.onstart = () => {
        if (callState.currentAttempt !== attempt || attempt.terminal) return;
        attempt.startedAt = monotonicNow();
        attempt.deadline = attempt.startedAt + callState.patientListenTimeoutMs;
        callState.listening = true;
        micButton.classList.add("listening");
        $("#mic-label").textContent = "Escuchando...";
        setVoiceState("LISTENING", attempt);
        updateListenTimer(attempt, 0);
        attempt.timerId = window.setTimeout(() => expireAttempt(), callState.patientListenTimeoutMs);
        void registerVoiceEvent(attempt, "patient_listen_started", { elapsed_ms: 0 });
        setStatus($("#call-status"), `Hable ahora. Tiene ${callState.patientListenTimeoutMs} ms para este turno.`);
      };
      recognition.onresult = (event) => {
        if (
          callState.currentAttempt !== attempt
          || attempt.terminal
          || attempt.finalSubmitted
          || !attempt.startedAt
        ) return;
        let interim = "";
        let finalText = "";
        const startIndex = Number.isInteger(event.resultIndex) ? event.resultIndex : 0;
        for (let index = startIndex; index < (event.results?.length || 0); index += 1) {
          const result = event.results[index];
          const transcript = result?.[0]?.transcript || "";
          if (result?.isFinal) finalText += transcript;
          else interim += transcript;
        }
        const now = monotonicNow();
        const elapsed = Math.max(0, now - attempt.startedAt);
        updateListenTimer(attempt, elapsed);
        if (interim && !finalText) {
          setVoiceState("PARTIAL", attempt);
          showPartial(interim.trim());
          void registerVoiceEvent(attempt, "partial", { elapsed_ms: elapsed });
        }
        if (!finalText.trim()) return;
        if (now > attempt.deadline) {
          expireAttempt();
          return;
        }
        attempt.finalSubmitted = true;
        attempt.terminal = true;
        clearListenTimer(attempt);
        clearPartial();
        setVoiceState("PROCESSING", attempt);
        finishAttemptControls(attempt);
        const timing = {
          mode: "voice",
          speech_ended_at: new Date().toISOString(),
          audio_started_at: null,
          elapsed_ms: elapsed,
        };
        void registerVoiceEvent(attempt, "final", { elapsed_ms: elapsed });
        void sendTurn(finalText.trim(), timing, attempt);
      };
      recognition.onerror = (event) => {
        if (callState.currentAttempt !== attempt || attempt.terminal || attempt.finalSubmitted) return;
        attempt.terminal = true;
        clearListenTimer(attempt);
        clearPartial();
        setVoiceState("RECOGNITION_ERROR", attempt);
        finishAttemptControls(attempt, "Reintentar");
        const errorCode = String(event.error || "recognition_error").slice(0, 64).replace(/[^A-Za-z0-9_.-]/g, "_");
        void registerVoiceEvent(attempt, "error", { error_code: errorCode });
        setStatus($("#call-status"), `No se pudo escuchar: ${event.error || "error de microfono"}. Usa el texto de respaldo.`, "error");
      };
      recognition.onend = () => {
        if (callState.currentAttempt !== attempt || attempt.terminal || attempt.finalSubmitted) return;
        if (!attempt.startedAt) {
          attempt.terminal = true;
          setVoiceState("RECOGNITION_ERROR", attempt);
          finishAttemptControls(attempt, "Reintentar");
          setStatus($("#call-status"), "El microfono termino antes de iniciar. Usa el texto de respaldo.", "error");
          return;
        }
        const elapsed = Math.max(0, monotonicNow() - attempt.startedAt);
        if (elapsed >= callState.patientListenTimeoutMs) {
          expireAttempt();
          return;
        }
        attempt.terminal = true;
        clearListenTimer(attempt);
        clearPartial();
        setVoiceState("NO_RESPONSE", attempt);
        finishAttemptControls(attempt, "Reintentar");
        void registerVoiceEvent(attempt, "ended", { elapsed_ms: elapsed });
        void registerVoiceEvent(attempt, "no_response", { elapsed_ms: elapsed });
        setStatus($("#call-status"), "No se recibio una respuesta. Puede reintentar o escribir el mensaje.", "error");
      };

      function expireAttempt() {
        if (
          callState.currentAttempt !== attempt
          || attempt.terminal
          || attempt.finalSubmitted
          || !attempt.startedAt
        ) return;
        attempt.terminal = true;
        clearListenTimer(attempt);
        const elapsed = Math.max(callState.patientListenTimeoutMs, monotonicNow() - attempt.startedAt);
        setVoiceState("LISTEN_TIMEOUT", attempt);
        clearPartial();
        finishAttemptControls(attempt, "Reintentar");
        try {
          if (typeof recognition.abort === "function") recognition.abort();
          else recognition.stop();
        } catch (_) {
          // A late browser callback is ignored by the terminal attempt state.
        }
        const eventPromise = registerVoiceEvent(attempt, "timeout", { elapsed_ms: elapsed });
        void eventPromise.then(() => {
          if (callState.currentAttempt === attempt && attempt.state === "LISTEN_TIMEOUT") {
            setVoiceState("RETRY_REQUIRED", attempt);
          }
        });
        setStatus($("#call-status"), "LISTEN_TIMEOUT: no se recibio una respuesta. Reintente o use el texto.", "error");
      }

      try {
        recognition.start();
      } catch (error) {
        attempt.terminal = true;
        setVoiceState("RECOGNITION_ERROR", attempt);
        finishAttemptControls(attempt, "Reintentar");
        void registerVoiceEvent(attempt, "error", { error_code: "start_failed" });
        setStatus($("#call-status"), "El microfono no pudo iniciar. Usa el texto de respaldo.", "error");
      }
    });
  }

  function summaryList(value) {
    if (Array.isArray(value)) return value.filter((item) => item !== null && item !== undefined && String(item).trim());
    if (value === null || value === undefined || String(value).trim() === "") return [];
    return [value];
  }

  function appendSummaryField(box, label, value) {
    const row = document.createElement("div");
    row.className = "summary-field";
    const name = document.createElement("span");
    name.className = "summary-label";
    name.textContent = label;
    row.appendChild(name);
    if (Array.isArray(value)) {
      const list = document.createElement("ul");
      list.className = "summary-list";
      value.forEach((item) => {
        const entry = document.createElement("li");
        entry.textContent = String(item);
        list.appendChild(entry);
      });
      if (!value.length) {
        const empty = document.createElement("span");
        empty.className = "summary-value";
        empty.textContent = "No registrado";
        row.appendChild(empty);
      } else {
        row.appendChild(list);
      }
    } else {
      const text = document.createElement("span");
      text.className = "summary-value";
      text.textContent = value === null || value === undefined || value === "" ? "No registrado" : String(value);
      row.appendChild(text);
    }
    box.appendChild(row);
  }

  function renderSummary(summary) {
    const box = $("#summary-box");
    if (!box || !summary) return;
    box.hidden = false;
    box.replaceChildren();
    const patient = summary.name || summary.patient || summary.patient_id || null;
    const patientId = summary.name && summary.patient_id && summary.patient_id !== summary.name
      ? ` (ID: ${summary.patient_id})`
      : "";
    appendSummaryField(box, "Paciente / nombre", patient ? `${patient}${patientId}` : null);
    appendSummaryField(box, "Procedimiento", summary.procedure || null);
    const day = summary.day_postop ?? summary.day;
    if (day !== null && day !== undefined && day !== "") {
      appendSummaryField(box, "Dia postoperatorio", day);
    }
    appendSummaryField(box, "Sintomas", summaryList(summary.symptoms));
    appendSummaryField(box, "Decision", summary.decision || summary.triage_level || "desconocida");
    appendSummaryField(box, "Alerta", summary.alert ? "Si" : "No");
    appendSummaryField(box, "Proximos pasos", summaryList(summary.next_steps));
    const sources = summaryList(summary.sources).map((source) => (
      source && typeof source === "object"
        ? source.citation || source.filename || source.source || "Fuente"
        : source
    ));
    appendSummaryField(box, "Fuentes", sources);
  }

  function initCall() {
    initRecognition();
    void requireListenTimeout().catch(() => {});
    setCallEnabled(false);
    $("#call-form")?.addEventListener("submit", async (event) => {
      event.preventDefault();
      const startButton = $("#start-call");
      startButton.disabled = true;
      const dayValue = $("#day-postop").value;
      const payload = {
        patient_id: $("#patient-id").value.trim() || null,
        name: $("#patient-name").value.trim() || null,
        procedure: $("#procedure").value.trim(),
        day_postop: dayValue === "" ? null : Number(dayValue),
      };
      try {
        await requireListenTimeout();
         const call = await api("/api/calls", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        callState.id = call.id;
         callState.closed = false;
         callState.processing = false;
         callState.currentAttempt = null;
        callState.listening = false;
        clearPartial();
        setVoiceState("LISTENING");
        $("#call-id-label").textContent = call.id;
        $("#turn-list").replaceChildren();
        const empty = document.createElement("div");
        empty.className = "empty-state empty-conversation";
        empty.textContent = "La llamada esta abierta. Habla o escribe el primer turno.";
        $("#turn-list").appendChild(empty);
        setCallEnabled(true);
        setStatus($("#call-status"), "Llamada abierta. Pulsa Hablar para solicitar el microfono.", "success");
      } catch (error) {
        setStatus($("#call-status"), error.message, "error");
      } finally {
        startButton.disabled = false;
      }
    });

    $("#text-form")?.addEventListener("submit", (event) => {
      event.preventDefault();
      const input = $("#turn-text");
      const value = input.value;
      input.value = "";
      sendTurn(value, TEXT_INPUT_TIMING);
    });

    $("#finish-call")?.addEventListener("click", async () => {
      if (!callState.id || callState.closed) return;
      const button = $("#finish-call");
      button.disabled = true;
      setTurnBusy(true);
      try {
        const call = await api(`/api/calls/${encodeURIComponent(callState.id)}/finish`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({}),
        });
        callState.closed = true;
        if (call.summary) renderSummary(call.summary);
        setStatus($("#call-status"), "Llamada cerrada y resumen guardado.", "success");
        $("#mic-button").disabled = true;
        $("#turn-text").disabled = true;
        $("#send-text").disabled = true;
      } catch (error) {
        button.disabled = false;
        setStatus($("#call-status"), error.message, "error");
      } finally {
        setTurnBusy(false);
      }
    });
  }

  if (page === "admin") initAdmin();
  if (page === "call") initCall();
})();
