(() => {
  "use strict";

  const page = document.body.dataset.page;
  const $ = (selector) => document.querySelector(selector);

  function messageFrom(value) {
    if (!value) return "Error desconocido";
    if (typeof value === "string") return value;
    if (Array.isArray(value)) return value.map((item) => item.msg || String(item)).join(", ");
    return value.detail || value.message || JSON.stringify(value);
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
      needs_ocr: "Necesita OCR",
      processing: "Procesando",
      error: "Error",
    }[status] || status;
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
    meta.textContent = documentRecord.id.slice(0, 12);
    nameCell.append(name, meta);

    const statusCell = document.createElement("td");
    const badge = document.createElement("span");
    badge.className = `status-badge status-${documentRecord.status}`;
    badge.textContent = statusLabel(documentRecord.status);
    statusCell.appendChild(badge);

    const sizeCell = document.createElement("td");
    sizeCell.textContent = formatBytes(documentRecord.size_bytes);

    const actionCell = document.createElement("td");
    const deleteButton = document.createElement("button");
    deleteButton.className = "delete-button";
    deleteButton.type = "button";
    deleteButton.textContent = "Eliminar";
    deleteButton.setAttribute("aria-label", `Eliminar ${documentRecord.filename}`);
    deleteButton.addEventListener("click", async () => {
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
    row.append(nameCell, statusCell, sizeCell, actionCell);
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
        empty.innerHTML = '<td colspan="4" class="empty-state">Aun no hay documentos. Agrega la primera fuente.</td>';
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
    loadDocuments();
  }

  const TEXT_INPUT_TIMING = Object.freeze({
    mode: "text",
    speech_ended_at: null,
    audio_started_at: null,
  });
  const callState = {
    id: null,
    recognition: null,
    listening: false,
    closed: false,
    pendingTranscript: null,
  };

  function setCallEnabled(enabled) {
    $("#conversation-panel")?.classList.toggle("is-disabled", !enabled);
    [$("#mic-button"), $("#turn-text"), $("#send-text"), $("#finish-call")].forEach((node) => {
      if (node) node.disabled = !enabled;
    });
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

  async function sendTurn(text, inputTiming = TEXT_INPUT_TIMING) {
    if (!callState.id || callState.closed || !text.trim()) return;
    const normalized = text.trim();
    const callId = callState.id;
    const sendButton = $("#send-text");
    if (sendButton) sendButton.disabled = true;
    renderTurn("patient", normalized);
    setStatus($("#call-status"), "El agente esta consultando el conocimiento disponible...");
    try {
      const response = await api(`/api/calls/${encodeURIComponent(callState.id)}/turns`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: normalized }),
      });
      const answer = response.text || response.answer || response.response || "No hay respuesta disponible.";
      renderTurn("agent", answer, response.sources || []);
      renderTriage(response);
      renderSources(response.sources || []);
      const voiceInput = inputTiming?.mode === "voice" ? inputTiming : null;
      speak(answer, (audioStartedAt) => {
        void recordVoiceTiming(callId, response.agent_turn_id, voiceInput, audioStartedAt);
      });
      setStatus($("#call-status"), "Turno registrado.", "success");
    } catch (error) {
      setStatus($("#call-status"), error.message, "error");
    } finally {
      if (sendButton) sendButton.disabled = false;
    }
  }

  function initRecognition() {
    const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    const micButton = $("#mic-button");
    const support = $("#voice-support");
    if (!Recognition) {
      if (support) support.textContent = "SpeechRecognition no esta disponible; usa el texto de respaldo.";
      if (micButton) micButton.disabled = true;
      return;
    }
    if (support) support.textContent = "Microfono listo · SpeechRecognition es-CO";
    micButton?.addEventListener("click", () => {
      if (callState.listening) {
        callState.recognition?.stop();
        return;
      }
      const recognition = new Recognition();
      callState.recognition = recognition;
      recognition.lang = "es-CO";
      recognition.continuous = false;
      recognition.interimResults = false;
      recognition.maxAlternatives = 1;
      recognition.onstart = () => {
        callState.listening = true;
        callState.pendingTranscript = null;
        micButton.classList.add("listening");
        $("#mic-label").textContent = "Escuchando...";
        setStatus($("#call-status"), "Hable ahora. El turno terminara al hacer una pausa.");
      };
      recognition.onresult = (event) => {
        const transcript = event.results?.[0]?.[0]?.transcript || "";
        callState.pendingTranscript = transcript || null;
      };
      recognition.onerror = (event) => {
        callState.pendingTranscript = null;
        setStatus($("#call-status"), `No se pudo escuchar: ${event.error || "error de microfono"}. Usa el texto de respaldo.`, "error");
      };
      recognition.onend = () => {
        const transcript = callState.pendingTranscript;
        callState.pendingTranscript = null;
        const speechEndedAt = new Date().toISOString();
        callState.listening = false;
        micButton.classList.remove("listening");
        $("#mic-label").textContent = "Hablar";
        if (transcript) {
          sendTurn(transcript, {
            mode: "voice",
            speech_ended_at: speechEndedAt,
            audio_started_at: null,
          });
        }
      };
      try {
        recognition.start();
      } catch (error) {
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
        const call = await api("/api/calls", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        callState.id = call.id;
        callState.closed = false;
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
      }
    });
  }

  if (page === "admin") initAdmin();
  if (page === "call") initCall();
})();
