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

  const ADMIN_COPY = Object.freeze({
    status: Object.freeze({
      available: { label: "Disponible", className: "status-available", help: "La fuente tiene texto utilizable." },
      needs_ocr: { label: "Necesita revisión", className: "status-needs_ocr", help: "No encontramos texto utilizable. Se necesita OCR." },
      processing: { label: "Procesando", className: "status-processing", help: "Estamos procesando esta fuente." },
      error: { label: "Error al procesar", className: "status-error", help: "No pudimos procesar esta fuente." },
    }),
    publication: Object.freeze({
      enabled: { label: "Disponible para el agente", className: "publication-enabled", help: "El agente puede consultar esta fuente." },
      disabled: { label: "No disponible para el agente", className: "publication-disabled", help: "La fuente se conserva, pero el agente no la consulta." },
      unavailable: { label: "No publicable", className: "publication-unavailable", help: "La fuente necesita texto utilizable antes de publicarse." },
    }),
  });

  class AdminApiError extends Error {
    constructor(status, code) {
      super("No se pudo completar la operación");
      this.name = "AdminApiError";
      this.status = status;
      this.code = code;
    }
  }

  async function adminApi(path, options = {}) {
    const response = await fetch(path, options);
    const contentType = response.headers.get("content-type") || "";
    const data = contentType.includes("application/json") ? await response.json() : await response.text();
    if (!response.ok) throw new AdminApiError(response.status, adminErrorCode(data));
    return data;
  }

  function adminErrorCode(value) {
    if (Array.isArray(value)) return value[0]?.type || "validation";
    if (value && typeof value === "object") {
      if (value.detail && typeof value.detail === "object") return value.detail.error_code || "request";
      return value.error_code || "request";
    }
    return "request";
  }

  function adminErrorMessage(error, action = "actualizar") {
    if (!(error instanceof AdminApiError)) return `No pudimos ${action} la fuente. Inténtalo de nuevo.`;
    const messages = {
      document_not_found: "La fuente ya no está disponible. Actualiza el inventario.",
      document_processing: "La fuente todavía se está procesando. Inténtalo de nuevo en un momento.",
      document_not_searchable: "La fuente no tiene texto utilizable para esta acción.",
      page_not_found: "No encontramos esa página en la fuente.",
      invalid_preview_range: "Indica una página válida para consultar la fuente.",
      offset_out_of_range: "No encontramos texto en ese punto de la página.",
    };
    return messages[error.code] || `No pudimos ${action} la fuente. Inténtalo de nuevo.`;
  }

  function sourceErrorMessage(error) {
    const messages = {
      source_unavailable: "No pudimos abrir el archivo original.",
      source_format_not_supported: "Este formato no se puede previsualizar aqui.",
      source_read_error: "No pudimos abrir esta fuente. Intentalo de nuevo.",
      document_processing: "La fuente aun se esta procesando. Intentalo de nuevo en un momento.",
    };
    return messages[error?.code] || "No pudimos abrir el archivo original.";
  }

  function adminStatusInfo(status) {
    return ADMIN_COPY.status[status] || {
      label: "Estado no disponible",
      className: "status-unknown",
      help: "No pudimos confirmar el estado de esta fuente.",
    };
  }

  function adminPublicationInfo(documentRecord) {
    if (documentRecord.status !== "available") return ADMIN_COPY.publication.unavailable;
    return documentRecord.enabled ? ADMIN_COPY.publication.enabled : ADMIN_COPY.publication.disabled;
  }

  function adminFormatBytes(bytes) {
    if (!Number.isFinite(Number(bytes)) || Number(bytes) < 0) return "Tamaño no disponible";
    const value = Number(bytes);
    if (value < 1024) return "<1 KB";
    if (value < 1024 * 1024) return `${Math.round(value / 1024)} KB`;
    return `${(value / (1024 * 1024)).toFixed(1)} MB`;
  }

  function adminFormatDate(value) {
    if (!value) return "";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return "";
    return new Intl.DateTimeFormat("es-CO", { dateStyle: "medium", timeStyle: "short" }).format(date);
  }

  function adminFileType(documentRecord) {
    const mime = String(documentRecord.mime_type || "").toLowerCase();
    if (mime.includes("pdf") || /\.pdf$/i.test(documentRecord.filename || "")) return "PDF";
    if (mime.includes("markdown") || /\.md$/i.test(documentRecord.filename || "")) return "Markdown";
    return "Texto";
  }

  function adminDocumentDetails(documentRecord) {
    const pages = Number(documentRecord.page_count) || 0;
    const chunks = Number(documentRecord.chunk_count) || 0;
    return `${pages} ${pages === 1 ? "página" : "páginas"} · ${chunks} ${chunks === 1 ? "fragmento" : "fragmentos"} · ${adminFormatBytes(documentRecord.size_bytes)}`;
  }

  function adminAppendText(parent, className, value) {
    const node = document.createElement("span");
    node.className = className;
    node.textContent = value;
    parent.appendChild(node);
    return node;
  }

  const adminPreviewState = {
    documentRecord: null,
    page: 1,
    opener: null,
    mode: "source",
    requestToken: 0,
    sourceObjectUrl: null,
  };

  function clearSourceObjectUrl() {
    if (adminPreviewState.sourceObjectUrl) {
      URL.revokeObjectURL(adminPreviewState.sourceObjectUrl);
      adminPreviewState.sourceObjectUrl = null;
    }
  }

  function setPreviewMode(mode) {
    const isSource = mode === "source";
    adminPreviewState.mode = isSource ? "source" : "extracted";
    const sourceTab = $("#preview-source-tab");
    const extractedTab = $("#preview-extracted-tab");
    sourceTab?.setAttribute("aria-selected", String(isSource));
    extractedTab?.setAttribute("aria-selected", String(!isSource));
    sourceTab?.classList.toggle("button-secondary", isSource);
    sourceTab?.classList.toggle("button-quiet", !isSource);
    extractedTab?.classList.toggle("button-secondary", !isSource);
    extractedTab?.classList.toggle("button-quiet", isSource);
    $("#preview-source-view")?.toggleAttribute("hidden", !isSource);
    $("#preview-extracted-view")?.toggleAttribute("hidden", isSource);
  }

  function closeAdminPreview(restoreFocus = true) {
    const panel = $("#preview-panel");
    adminPreviewState.requestToken += 1;
    clearSourceObjectUrl();
    const sourceFrame = $("#preview-source-frame");
    if (sourceFrame) sourceFrame.removeAttribute("src");
    if (panel?.open && typeof panel.close === "function") panel.close();
    panel?.classList.remove("is-polyfill-open");
    if (panel) panel.hidden = false;
    document.body.classList.remove("preview-modal-open");
    const opener = adminPreviewState.opener;
    adminPreviewState.documentRecord = null;
    adminPreviewState.opener = null;
    if (restoreFocus && opener && document.contains(opener)) opener.focus();
  }

  async function loadAdminExtractedPreview(documentRecord, page = 1, requestToken = adminPreviewState.requestToken) {
    const panel = $("#preview-panel");
    const pageInput = $("#preview-page");
    const documentLabel = $("#preview-document");
    const meta = $("#preview-meta");
    const text = $("#preview-text");
    if (!panel || !pageInput || !documentLabel || !meta || !text) return;
    pageInput.value = String(page);
    text.textContent = "";
    meta.textContent = "";
    setStatus($("#preview-status"), "Estamos cargando el texto de la fuente...");
    $("#preview-close")?.focus();
    try {
      const data = await adminApi(
        `/api/admin/documents/${encodeURIComponent(documentRecord.id)}/preview?page=${encodeURIComponent(page)}&offset=0&limit=8000`,
      );
      if (requestToken !== adminPreviewState.requestToken) return;
      const preview = data.preview || {};
      if (preview.available) {
        text.textContent = preview.text || "";
        const truncation = preview.truncated ? " · vista limitada" : "";
        meta.textContent = `Página ${preview.page} de ${preview.page_count} · ${preview.total_chars} caracteres${truncation}`;
        setStatus($("#preview-status"), "Texto plano seguro: el contenido no se interpreta como HTML, Markdown ni instrucciones.", "success");
      } else {
        text.textContent = "";
        meta.textContent = `Página ${preview.page || page} de ${preview.page_count || documentRecord.page_count || 0}`;
        setStatus($("#preview-status"), "No encontramos texto utilizable. Se necesita OCR.", "error");
      }
    } catch (error) {
      text.textContent = "";
      meta.textContent = "";
      setStatus($("#preview-status"), adminErrorMessage(error, "consultar"), "error");
    }
  }

  async function loadAdminSource(documentRecord, requestToken) {
    const sourceFrame = $("#preview-source-frame");
    const sourceText = $("#preview-source-text");
    const fallback = $("#preview-source-fallback");
    if (!sourceFrame || !sourceText || !fallback) return;
    clearSourceObjectUrl();
    sourceFrame.hidden = true;
    sourceText.hidden = true;
    setStatus($("#preview-status"), "Estamos cargando el archivo original...");
    try {
      const response = await fetch(
        `/api/admin/documents/${encodeURIComponent(documentRecord.id)}/source`,
      );
      const contentType = response.headers.get("content-type") || "";
      if (!response.ok) {
        const data = contentType.includes("application/json")
          ? await response.json()
          : await response.text();
        throw new AdminApiError(response.status, adminErrorCode(data));
      }
      const blob = await response.blob();
      if (requestToken !== adminPreviewState.requestToken) return;
      adminPreviewState.sourceObjectUrl = URL.createObjectURL(blob);
      if (documentRecord.source_format === "pdf" || /application\/pdf/i.test(contentType)) {
        sourceFrame.src = adminPreviewState.sourceObjectUrl;
        sourceFrame.hidden = false;
        fallback.hidden = false;
      } else {
        sourceText.textContent = await blob.text();
        sourceText.hidden = false;
        fallback.hidden = true;
      }
      setStatus($("#preview-status"), "Archivo original cargado. Se muestra como contenido no ejecutable.", "success");
    } catch (error) {
      if (requestToken !== adminPreviewState.requestToken) return;
      sourceFrame.removeAttribute("src");
      sourceText.textContent = "";
      setStatus($("#preview-status"), sourceErrorMessage(error), "error");
    }
  }

  async function loadAdminPreview(documentRecord, page = 1, opener = null) {
    const panel = $("#preview-panel");
    const documentLabel = $("#preview-document");
    if (!panel || !documentLabel) return;
    adminPreviewState.documentRecord = documentRecord;
    adminPreviewState.page = page;
    adminPreviewState.opener = opener || adminPreviewState.opener;
    adminPreviewState.requestToken += 1;
    const requestToken = adminPreviewState.requestToken;
    documentLabel.textContent = documentRecord.filename;
    setPreviewMode("source");
    $("#preview-source-help").textContent = "Archivo original: asi fue recibido. No es el texto indexado.";
    $("#preview-extracted-help").textContent = "Texto extraido: resultado de la ingestion. Puede diferir del archivo visual.";
    if (typeof panel.showModal === "function" && !panel.open) panel.showModal();
    else {
      panel.hidden = false;
      panel.classList.add("is-polyfill-open");
      document.body.classList.add("preview-modal-open");
    }
    $("#preview-close")?.focus();
    void loadAdminSource(documentRecord, requestToken);
  }

  function adminActionButton({ className = "admin-action", label, accessibleLabel, onClick }) {
    const button = document.createElement("button");
    button.className = className;
    button.type = "button";
    button.textContent = label;
    button.setAttribute("aria-label", accessibleLabel);
    button.addEventListener("click", onClick);
    return button;
  }

  function renderAdminDocumentRow(documentRecord) {
    const row = document.createElement("tr");
    row.className = "document-row";

    const nameCell = document.createElement("td");
    const name = document.createElement("div");
    name.className = "document-name";
    name.title = documentRecord.filename;
    name.textContent = documentRecord.filename;
    const type = document.createElement("span");
    type.className = "document-type";
    type.textContent = adminFileType(documentRecord);
    const meta = document.createElement("div");
    meta.className = "document-meta";
    const dates = [
      adminFormatDate(documentRecord.created_at) ? `Cargado ${adminFormatDate(documentRecord.created_at)}` : "",
      adminFormatDate(documentRecord.processed_at) ? `Procesado ${adminFormatDate(documentRecord.processed_at)}` : "",
    ].filter(Boolean);
    meta.textContent = dates.join(" · ") || "Fecha no disponible";
    nameCell.append(name, type, meta);

    const processing = adminStatusInfo(documentRecord.status);
    const statusCell = document.createElement("td");
    statusCell.dataset.label = "Procesamiento";
    adminAppendText(statusCell, `status-badge ${processing.className}`, processing.label);
    adminAppendText(statusCell, "document-helper", processing.help);

    const publication = adminPublicationInfo(documentRecord);
    const publicationCell = document.createElement("td");
    publicationCell.dataset.label = "Publicación";
    adminAppendText(publicationCell, `status-badge ${publication.className}`, publication.label);
    adminAppendText(publicationCell, "document-helper", publication.help);

    const contentCell = document.createElement("td");
    contentCell.dataset.label = "Contenido";
    contentCell.className = "document-content";
    contentCell.textContent = adminDocumentDetails(documentRecord);

    const actionCell = document.createElement("td");
    actionCell.dataset.label = "Acciones";
    actionCell.className = "document-actions";

    if (documentRecord.original_preview_available === true || documentRecord.preview_available === true) {
      actionCell.appendChild(adminActionButton({
        label: "Previsualizar",
        accessibleLabel: `Previsualizar ${documentRecord.filename}`,
        onClick: (event) => { void loadAdminPreview(documentRecord, 1, event.currentTarget); },
      }));
    }

    if (documentRecord.status === "available") {
      const nextEnabled = !documentRecord.enabled;
      const action = nextEnabled ? "habilitar" : "deshabilitar";
      const toggleButton = adminActionButton({
        label: nextEnabled ? "Habilitar" : "Deshabilitar",
        accessibleLabel: `${nextEnabled ? "Habilitar" : "Deshabilitar"} ${documentRecord.filename}`,
        onClick: async () => {
          if (!window.confirm(`Confirma ${action} ${documentRecord.filename}.`)) return;
          toggleButton.disabled = true;
          setStatus($("#documents-status"), "Estamos actualizando la fuente...");
          try {
            const result = await adminApi(`/api/admin/documents/${encodeURIComponent(documentRecord.id)}`, {
              method: "PATCH",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ enabled: nextEnabled }),
            });
            setStatus($("#documents-status"), result.changed ? `Fuente ${nextEnabled ? "habilitada" : "deshabilitada"}.` : "La fuente ya tenía ese estado.", "success");
            await loadAdminDocuments();
          } catch (error) {
            toggleButton.disabled = false;
            setStatus($("#documents-status"), adminErrorMessage(error, action), "error");
          }
        },
      });
      actionCell.appendChild(toggleButton);
    }

    const deleteButton = adminActionButton({
      className: "delete-button",
      label: "Eliminar",
      accessibleLabel: `Eliminar ${documentRecord.filename}`,
      onClick: async () => {
        if (!window.confirm(`Eliminar ${documentRecord.filename} de forma permanente? Esta acción no se puede deshacer.`)) return;
        deleteButton.disabled = true;
        setStatus($("#documents-status"), "Estamos eliminando la fuente...");
        try {
          await adminApi(`/api/admin/documents/${encodeURIComponent(documentRecord.id)}`, { method: "DELETE" });
          if (adminPreviewState.documentRecord?.id === documentRecord.id) closeAdminPreview(false);
          setStatus($("#documents-status"), "Fuente eliminada. El agente la olvidó sin reiniciar.", "success");
          await loadAdminDocuments();
        } catch (error) {
          deleteButton.disabled = false;
          setStatus($("#documents-status"), adminErrorMessage(error, "eliminar"), "error");
        }
      },
    });
    actionCell.appendChild(deleteButton);
    row.append(nameCell, statusCell, publicationCell, contentCell, actionCell);
    return row;
  }

  function renderAdminEmptyRow(message) {
    const empty = document.createElement("tr");
    const emptyCell = document.createElement("td");
    emptyCell.colSpan = 5;
    emptyCell.className = "empty-state";
    emptyCell.textContent = message;
    empty.appendChild(emptyCell);
    return empty;
  }

  async function loadAdminDocuments() {
    const rows = $("#document-rows");
    if (!rows) return;
    rows.replaceChildren(renderAdminEmptyRow("Estamos cargando tus fuentes..."));
    setStatus($("#documents-status"), "Estamos cargando tus fuentes...");
    try {
      const data = await adminApi("/api/admin/documents");
      const documents = Array.isArray(data) ? data : (data.documents || []);
      rows.replaceChildren();
      if (!documents.length) rows.appendChild(renderAdminEmptyRow("Aún no hay fuentes cargadas."));
      else documents.forEach((item) => rows.appendChild(renderAdminDocumentRow(item)));
      if (adminPreviewState.documentRecord) {
        const refreshed = documents.find((item) => item.id === adminPreviewState.documentRecord.id);
        if (refreshed) adminPreviewState.documentRecord = refreshed;
        else closeAdminPreview(false);
      }
      setStatus($("#documents-status"), documents.length ? `${documents.length} fuente${documents.length === 1 ? "" : "s"} en el inventario.` : "Aún no hay fuentes cargadas.", "success");
    } catch (_) {
      rows.replaceChildren(renderAdminEmptyRow("No pudimos cargar tus fuentes."));
      setStatus($("#documents-status"), "No pudimos actualizar la lista. Inténtalo de nuevo.", "error");
    }
  }

  function initAdmin() {
    const fileInput = $("#knowledge-file");
    const fileLabel = $("#file-label");
    fileInput?.addEventListener("change", () => {
      const file = fileInput.files?.[0];
      if (file) fileLabel.textContent = `${file.name} · ${adminFormatBytes(file.size)}`;
    });

    $("#upload-form")?.addEventListener("submit", async (event) => {
      event.preventDefault();
      const file = fileInput?.files?.[0];
      if (!file) return;
      const button = $("#upload-button");
      button.disabled = true;
      setStatus($("#upload-status"), "Estamos procesando la fuente...");
      const formData = new FormData();
      formData.append("file", file);
      try {
        const record = await adminApi("/api/admin/documents", { method: "POST", body: formData });
        setStatus($("#upload-status"), `${record.filename}: ${adminStatusInfo(record.status).label}.`, "success");
        event.target.reset();
        fileLabel.textContent = "Elegir un documento";
        await loadAdminDocuments();
      } catch (_) {
        setStatus($("#upload-status"), "No pudimos procesar la fuente. Revisa el formato e inténtalo de nuevo.", "error");
      } finally {
        button.disabled = false;
      }
    });
    $("#refresh-documents")?.addEventListener("click", loadAdminDocuments);
    $("#preview-close")?.addEventListener("click", () => closeAdminPreview());
    $("#preview-source-tab")?.addEventListener("click", () => {
      if (!adminPreviewState.documentRecord) return;
      setPreviewMode("source");
      void loadAdminSource(adminPreviewState.documentRecord, adminPreviewState.requestToken);
    });
    $("#preview-extracted-tab")?.addEventListener("click", () => {
      if (!adminPreviewState.documentRecord) return;
      setPreviewMode("extracted");
      void loadAdminExtractedPreview(
        adminPreviewState.documentRecord,
        adminPreviewState.page,
        adminPreviewState.requestToken,
      );
    });
    $("#preview-panel")?.addEventListener("cancel", (event) => {
      event.preventDefault();
      closeAdminPreview();
    });
    $("#preview-load")?.addEventListener("click", () => {
      if (!adminPreviewState.documentRecord) return;
      const page = Number($("#preview-page")?.value || 1);
      if (Number.isInteger(page) && page > 0) {
        adminPreviewState.page = page;
        void loadAdminExtractedPreview(
          adminPreviewState.documentRecord,
          page,
          adminPreviewState.requestToken,
        );
      }
      else setStatus($("#preview-status"), "Indica una página válida para consultar la fuente.", "error");
    });
    loadAdminDocuments();
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
