(() => {
  "use strict";

  const messages = {
    CALL_READY: ["La llamada está lista. Cuando quieras, toca Hablar o escribe tu mensaje.", "La llamada está lista."],
    CALL_OPEN: ["Estoy aquí para escucharte. Cuéntame cómo te has sentido desde tu procedimiento.", "La llamada está abierta."],
    LISTEN_START: ["Te escucho. Cuéntame con calma cómo te sientes.", "Escuchando."],
    LISTENING: ["Te escucho.", "Escuchando..."],
    PROCESSING: [null, "Procesando tu mensaje..."],
    RESPONDING: [null, "Preparando una respuesta..."],
    RECONNECTING: [null, "Preparando la escucha..."],
    LISTEN_PARTIAL: [null, "Borrador de lo que entendí: {texto}"],
    LISTEN_NO_RESPONSE: ["No alcancé a escucharte. ¿Quieres intentarlo de nuevo?", "No recibimos una respuesta. Puedes reintentar o escribir."],
    LISTEN_TIMEOUT: ["No alcancé a escucharte. ¿Quieres intentarlo de nuevo?", "No pudimos completar la escucha. Puedes reintentar o escribir."],
    LISTEN_ERROR: ["No pude escucharte bien. Puedes intentarlo otra vez o escribir tu mensaje.", "No pudimos escuchar el mensaje. Puedes reintentar o escribir."],
    MIC_PERMISSION_DENIED: ["No pude activar el micrófono. Puedes escribir tu mensaje o intentarlo de nuevo.", "No pudimos activar el micrófono. Puedes escribir."],
    MIC_UNAVAILABLE: ["Aquí no puedo activar el micrófono. Prueba Chrome o Edge, o escribe tu mensaje.", "El micrófono no está disponible. Puedes escribir."],
    MIC_ENDED_EARLY: ["La escucha terminó antes de recibir tu mensaje. ¿Quieres intentarlo de nuevo?", "La escucha terminó antes de recibir el mensaje."],
    LISTEN_CONFIG_ERROR: ["No pude preparar la escucha. Puedes escribir tu mensaje o intentarlo de nuevo.", "No pudimos preparar la escucha. Puedes escribir."],
    LISTEN_RETRY: ["Podemos intentarlo otra vez, sin afán.", "Reintentar"],
    KNOWLEDGE_LOOKUP: ["Estoy revisando la información disponible para orientarte.", "Consultando la información disponible..."],
    NO_EVIDENCE: ["No tengo información suficiente para orientarte con seguridad. ¿Qué síntoma tienes ahora?", "No encontramos información suficiente para responder con seguridad."],
    RAG_UNAVAILABLE: ["No pude consultar la información ahora. ¿Quieres intentarlo de nuevo?", "No pudimos consultar la información. Puedes reintentar."],
    UNSAFE_ANSWER: ["No pude preparar una orientación segura. ¿Quieres intentarlo de nuevo?", "No pudimos preparar una orientación segura. Puedes reintentar."],
    BACKEND_UNAVAILABLE: ["El servicio no respondió ahora. Puedes intentarlo de nuevo o escribir tu mensaje.", "El servicio no respondió. Puedes reintentar o escribir."],
    AUDIO_TRANSCRIPTION_ERROR: ["No pude convertir el audio en texto. Puedes hablar otra vez o escribir tu mensaje.", "No pudimos convertir el audio. Puedes escribir."],
    CALL_NOT_FOUND: ["No encuentro esta llamada. Abre una llamada nueva para continuar.", "No encontramos esta llamada. Abre una nueva."],
    CALL_CLOSED: ["Esta llamada ya terminó. Puedes abrir otra si necesitas continuar.", "Esta llamada ya terminó."],
    INVALID_MESSAGE: ["No alcancé a entender ese mensaje. ¿Puedes decirme con otras palabras qué sientes?", "No entendimos el mensaje. Puedes decirlo de otra forma."],
    TRIAGE_RED: ["Siento que estés pasando por esto. Busca atención inmediata en urgencias o llama ahora a tu equipo clínico. No esperes a terminar esta llamada.", "Atención inmediata"],
    TRIAGE_YELLOW: ["Entiendo que esto te preocupe. Contacta hoy a tu equipo clínico para recibir indicaciones.", "Contactar hoy"],
    TRIAGE_GREEN: ["Qué bueno saber que vas bien. Sigue las indicaciones de tu equipo clínico y cuéntanos si aparece algo nuevo.", "Sin señales de alarma"],
    TRIAGE_UNKNOWN: ["Quiero orientarte con cuidado. Necesito aclarar un detalle antes de continuar.", "Necesitamos aclarar"],
    ALERT_RED_UI: [null, "Busca atención inmediata o llama a tu equipo clínico."],
    ALERT_YELLOW_UI: [null, "Contacta hoy a tu equipo clínico."],
    PROMPT_INJECTION: ["Quiero centrarme en cómo te sientes y ayudarte con seguridad. ¿Qué síntoma te preocupa?", "La entrada no se pudo usar para orientar esta consulta."],
    TURN_REGISTERED: [null, "Tu mensaje fue recibido."],
    TURN_DUPLICATE: ["Ya había recibido este mensaje y conservé la respuesta.", "Este turno ya estaba registrado."],
    LATENCY_NOT_SAVED: [null, "Guardamos tu respuesta, pero no pudimos registrar el tiempo de voz."],
    GENERIC_RETRY: ["No pude completar este paso. ¿Quieres intentarlo de nuevo?", "No pudimos completar este paso. Puedes reintentar."],
    FINISH_PROMPT: ["Cuando terminemos, guardaré un resumen de lo que hablamos. ¿Quieres finalizar la llamada?", "Al finalizar se guardará un resumen de la llamada."],
    CALL_FINISHED: ["La llamada terminó y el resumen quedó guardado. Si aparece una señal de alarma, busca atención inmediata.", "Llamada cerrada y resumen guardado."],
    SUMMARY_UNAVAILABLE: ["No pude guardar el resumen ahora. Si tienes una señal de alarma, busca atención inmediata.", "No pudimos guardar el resumen."],
    SUMMARY_EMPTY: [null, "No registrado"],
    SUMMARY_UNKNOWN: [null, "Por confirmar con tu equipo clínico"],
  };

  function render(code, channel = "display_text", values = {}) {
    const entry = messages[code] || messages.GENERIC_RETRY;
    const template = entry[channel === "voice_text" ? 0 : 1] || entry[1] || "";
    return String(template).replace(/\{([A-Za-z_]+)\}/g, (_, key) => String(values[key] ?? ""));
  }

  function isSafeVoice(text) {
    const technical = /LISTEN_TIMEOUT|RECOGNITION_ERROR|SpeechRecognition|error_code|client_turn_id|source_ids|corpus_revision|\bchunk\b|\bscore\b|\bprompt\b|GROQ|Whisper|FTS5|milisegundos/i;
    return Boolean(text) && !technical.test(text) && (String(text).match(/[.!?]+/g) || []).length <= 2 && String(text).split("?").length <= 2;
  }

  function voice(code, values = {}) {
    const text = render(code, "voice_text", values);
    return isSafeVoice(text) ? text : render("GENERIC_RETRY", "voice_text");
  }

  window.CALL_MESSAGES = Object.freeze({ messages: Object.freeze(messages), render, voice, isSafeVoice });
})();
