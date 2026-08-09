"""Patient-facing Spanish copy with separate voice and display channels."""

from __future__ import annotations

import re
from typing import Any

MESSAGES: dict[str, dict[str, str | None]] = {
    "CALL_READY": {
        "voice_text": "La llamada está lista. Cuando quieras, toca Hablar o escribe tu mensaje.",
        "display_text": "La llamada está lista.",
    },
    "CALL_OPEN": {
        "voice_text": (
            "Estoy aquí para escucharte. Cuéntame cómo te has sentido desde tu procedimiento."
        ),
        "display_text": "La llamada está abierta.",
    },
    "CALL_CONTEXT_MISSING": {
        "voice_text": (
            "Para orientarte mejor, necesito saber quién eres y qué procedimiento te realizaron."
        ),
        "display_text": "Completa el nombre y el procedimiento.",
    },
    "FIRST_TRIAGE": {
        "voice_text": "Revisaremos cómo te sientes en tu primer mensaje.",
        "display_text": "Revisaremos tu estado de seguridad.",
    },
    "DEMO_DISCLAIMER": {
        "voice_text": (
            "Esta información es de demostración y no reemplaza la atención de tu equipo clínico."
        ),
        "display_text": "Información sintética de demostración; no reemplaza a tu equipo clínico.",
    },
    "LISTEN_START": {
        "voice_text": "Te escucho. Cuéntame con calma cómo te sientes.",
        "display_text": "Escuchando.",
    },
    "LISTENING": {"voice_text": "Te escucho.", "display_text": "Escuchando..."},
    "PROCESSING": {"voice_text": None, "display_text": "Procesando tu mensaje..."},
    "RESPONDING": {"voice_text": None, "display_text": "Preparando una respuesta..."},
    "RECONNECTING": {"voice_text": None, "display_text": "Preparando la escucha..."},
    "LISTEN_PARTIAL": {"voice_text": None, "display_text": "Borrador de lo que entendí: {texto}"},
    "LISTEN_NO_RESPONSE": {
        "voice_text": "No alcancé a escucharte. ¿Quieres intentarlo de nuevo?",
        "display_text": "No recibimos una respuesta. Puedes reintentar o escribir.",
    },
    "LISTEN_TIMEOUT": {
        "voice_text": "No alcancé a escucharte. ¿Quieres intentarlo de nuevo?",
        "display_text": "No pudimos completar la escucha. Puedes reintentar o escribir.",
    },
    "LISTEN_ERROR": {
        "voice_text": "No pude escucharte bien. Puedes intentarlo otra vez o escribir tu mensaje.",
        "display_text": "No pudimos escuchar el mensaje. Puedes reintentar o escribir.",
    },
    "MIC_PERMISSION_DENIED": {
        "voice_text": (
            "No pude activar el micrófono. Puedes escribir tu mensaje o intentarlo de nuevo."
        ),
        "display_text": "No pudimos activar el micrófono. Puedes escribir.",
    },
    "MIC_UNAVAILABLE": {
        "voice_text": (
            "Aquí no puedo activar el micrófono. Prueba Chrome o Edge, o escribe tu mensaje."
        ),
        "display_text": "El micrófono no está disponible. Puedes escribir.",
    },
    "MIC_ENDED_EARLY": {
        "voice_text": (
            "La escucha terminó antes de recibir tu mensaje. ¿Quieres intentarlo de nuevo?"
        ),
        "display_text": "La escucha terminó antes de recibir el mensaje.",
    },
    "LISTEN_CONFIG_ERROR": {
        "voice_text": (
            "No pude preparar la escucha. Puedes escribir tu mensaje o intentarlo de nuevo."
        ),
        "display_text": "No pudimos preparar la escucha. Puedes escribir.",
    },
    "LISTEN_RETRY": {
        "voice_text": "Podemos intentarlo otra vez, sin afán.",
        "display_text": "Reintentar",
    },
    "KNOWLEDGE_LOOKUP": {
        "voice_text": "Estoy revisando la información disponible para orientarte.",
        "display_text": "Consultando la información disponible...",
    },
    "GROUNDED_ANSWER_PREFIX": {
        "voice_text": "Según la guía disponible, {respuesta_breve}.",
        "display_text": "Respuesta basada en una fuente disponible.",
    },
    "EXTRACTIVE_ANSWER": {
        "voice_text": "La guía disponible indica: {respuesta_breve}.",
        "display_text": "La guía disponible indica: {respuesta_breve}.",
    },
    "NO_EVIDENCE": {
        "voice_text": (
            "No tengo información suficiente para orientarte con seguridad. "
            "¿Qué síntoma tienes ahora?"
        ),
        "display_text": "No encontramos información suficiente para responder con seguridad.",
    },
    "RAG_UNAVAILABLE": {
        "voice_text": "No pude consultar la información ahora. ¿Quieres intentarlo de nuevo?",
        "display_text": "No pudimos consultar la información. Puedes reintentar.",
    },
    "UNSAFE_ANSWER": {
        "voice_text": "No pude preparar una orientación segura. ¿Quieres intentarlo de nuevo?",
        "display_text": "No pudimos preparar una orientación segura. Puedes reintentar.",
    },
    "CORPUS_CHANGED": {
        "voice_text": (
            "La información se actualizó mientras revisaba tu consulta. Inténtalo de nuevo."
        ),
        "display_text": "La información cambió durante la consulta. Puedes reintentar.",
    },
    "EMPTY_RESPONSE": {
        "voice_text": "No pude preparar una respuesta ahora. ¿Quieres intentarlo de nuevo?",
        "display_text": "No pudimos preparar una respuesta. Puedes reintentar.",
    },
    "AGENT_ERROR": {
        "voice_text": (
            "Lo siento, no pude preparar una respuesta ahora. Si tienes una señal de alarma, "
            "busca atención inmediata; si no, inténtalo de nuevo."
        ),
        "display_text": "No pudimos preparar una respuesta. Puedes reintentar.",
    },
    "TURN_REGISTERED": {"voice_text": None, "display_text": "Tu mensaje fue recibido."},
    "TURN_DUPLICATE": {
        "voice_text": "Ya había recibido este mensaje y conservé la respuesta.",
        "display_text": "Este turno ya estaba registrado.",
    },
    "LATENCY_NOT_SAVED": {
        "voice_text": None,
        "display_text": "Guardamos tu respuesta, pero no pudimos registrar el tiempo de voz.",
    },
    "TRIAGE_RED": {
        "voice_text": (
            "Siento que estés pasando por esto. Busca atención inmediata en urgencias o llama "
            "ahora a tu equipo clínico; no esperes a terminar esta llamada."
        ),
        "display_text": "Atención inmediata",
    },
    "TRIAGE_YELLOW": {
        "voice_text": (
            "Entiendo que esto te preocupe. Contacta hoy a tu equipo clínico para recibir "
            "indicaciones."
        ),
        "display_text": "Contactar hoy",
    },
    "TRIAGE_GREEN": {
        "voice_text": (
            "Qué bueno saber que vas bien. Sigue las indicaciones de tu equipo clínico y "
            "cuéntanos si aparece algo nuevo."
        ),
        "display_text": "Sin señales de alarma",
    },
    "TRIAGE_UNKNOWN": {
        "voice_text": (
            "Quiero orientarte con cuidado. Necesito aclarar un detalle antes de continuar."
        ),
        "display_text": "Necesitamos aclarar",
    },
    "ALERT_RED_UI": {
        "voice_text": None,
        "display_text": "Busca atención inmediata o llama a tu equipo clínico.",
    },
    "ALERT_YELLOW_UI": {
        "voice_text": None,
        "display_text": "Contacta hoy a tu equipo clínico.",
    },
    "ASK_SEVERE_PAIN": {
        "voice_text": ("¿Tienes un dolor muy fuerte ahora? Responde sí o no."),
        "display_text": "Confirma si tienes dolor muy fuerte.",
    },
    "ASK_FEVER": {
        "voice_text": ("¿Tienes fiebre o una temperatura de 38 grados o más? Responde sí o no."),
        "display_text": "Confirma si tienes fiebre.",
    },
    "ASK_BLEEDING": {
        "voice_text": "¿Tienes sangrado ahora? Responde sí o no.",
        "display_text": "Confirma si tienes sangrado.",
    },
    "ASK_BREATHING": {
        "voice_text": ("¿Te cuesta respirar ahora? Responde sí o no."),
        "display_text": "Confirma si te cuesta respirar.",
    },
    "ASK_CHEST": {
        "voice_text": ("¿Tienes dolor u opresión en el pecho ahora? Responde sí o no."),
        "display_text": "Confirma si tienes dolor en el pecho.",
    },
    "ASK_WOUND_OPEN": {
        "voice_text": "¿Está abierta la herida? Responde sí o no.",
        "display_text": "Confirma si la herida está abierta.",
    },
    "ASK_WOUND_DRAINAGE": {
        "voice_text": "¿Sale líquido de la herida? Responde sí o no.",
        "display_text": "Confirma si sale líquido de la herida.",
    },
    "ASK_FLUIDS": {
        "voice_text": "¿Puedes retener pequeños sorbos de agua? Responde sí o no.",
        "display_text": "Confirma si puedes retener líquidos.",
    },
    "ASK_URINARY": {
        "voice_text": "¿Puedes orinar con normalidad? Responde sí o no.",
        "display_text": "Confirma si puedes orinar con normalidad.",
    },
    "ASK_LOCATION": {
        "voice_text": "Gracias. ¿En qué parte sientes la molestia?",
        "display_text": "Indica dónde sientes la molestia.",
    },
    "ASK_ONSET": {
        "voice_text": "¿Desde cuándo la sientes?",
        "display_text": "Indica desde cuándo la sientes.",
    },
    "ASK_GENERIC_SYMPTOM": {
        "voice_text": "Quiero ayudarte con cuidado. ¿Qué síntoma te preocupa más ahora?",
        "display_text": "Indica qué síntoma te preocupa más.",
    },
    "UNTRUSTED_INPUT": {
        "voice_text": (
            "Quiero centrarme en cómo te sientes y ayudarte con seguridad. "
            "¿Qué síntoma te preocupa?"
        ),
        "display_text": "La entrada no se pudo usar para orientar esta consulta.",
    },
    "PROMPT_INJECTION": {
        "voice_text": (
            "Quiero centrarme en cómo te sientes y ayudarte con seguridad. "
            "¿Qué síntoma te preocupa?"
        ),
        "display_text": "La entrada no se pudo usar para orientar esta consulta.",
    },
    "GENERIC_RETRY": {
        "voice_text": "No pude completar este paso. ¿Quieres intentarlo de nuevo?",
        "display_text": "No pudimos completar este paso. Puedes reintentar.",
    },
    "BACKEND_UNAVAILABLE": {
        "voice_text": (
            "El servicio no respondió ahora. Puedes intentarlo de nuevo o escribir tu mensaje."
        ),
        "display_text": "El servicio no respondió. Puedes reintentar o escribir.",
    },
    "AUDIO_TRANSCRIPTION_ERROR": {
        "voice_text": (
            "No pude convertir el audio en texto. Puedes hablar otra vez o escribir tu mensaje."
        ),
        "display_text": "No pudimos convertir el audio. Puedes escribir.",
    },
    "CALL_NOT_FOUND": {
        "voice_text": "No encuentro esta llamada. Abre una llamada nueva para continuar.",
        "display_text": "No encontramos esta llamada. Abre una nueva.",
    },
    "CALL_CLOSED": {
        "voice_text": "Esta llamada ya terminó. Puedes abrir otra si necesitas continuar.",
        "display_text": "Esta llamada ya terminó.",
    },
    "INVALID_MESSAGE": {
        "voice_text": (
            "No alcancé a entender ese mensaje. ¿Puedes decirme con otras palabras qué sientes?"
        ),
        "display_text": "No entendimos el mensaje. Puedes decirlo de otra forma.",
    },
    "FINISH_PROMPT": {
        "voice_text": (
            "Cuando terminemos, guardaré un resumen de lo que hablamos. "
            "¿Quieres finalizar la llamada?"
        ),
        "display_text": "Al finalizar se guardará un resumen de la llamada.",
    },
    "CALL_FINISHED": {
        "voice_text": (
            "La llamada terminó y el resumen quedó guardado. Si aparece una señal de alarma, "
            "busca atención inmediata."
        ),
        "display_text": "Llamada cerrada y resumen guardado.",
    },
    "SUMMARY_UNAVAILABLE": {
        "voice_text": (
            "No pude guardar el resumen ahora. Si tienes una señal de alarma, "
            "busca atención inmediata."
        ),
        "display_text": "No pudimos guardar el resumen.",
    },
    "SUMMARY_NEXT_STEPS": {"voice_text": None, "display_text": "Próximos pasos"},
    "SUMMARY_EMPTY": {"voice_text": None, "display_text": "No registrado"},
    "SUMMARY_UNKNOWN": {"voice_text": None, "display_text": "Por confirmar con tu equipo clínico"},
}

TECHNICAL_TERMS = (
    "LISTEN_TIMEOUT",
    "RECOGNITION_ERROR",
    "GROQ",
    "Whisper",
    "FTS5",
    "chunk",
    "score",
    "prompt",
    "source_ids",
    "corpus_revision",
    "error_code",
    "stack trace",
    "client_turn_id",
    "deadline",
    "SpeechRecognition",
    "milisegundos",
)


def render_message(code: str, channel: str = "display_text", **values: Any) -> str:
    entry = MESSAGES.get(code) or MESSAGES["GENERIC_RETRY"]
    template = entry.get(channel) or entry.get("display_text") or ""
    try:
        return str(template).format(**values)
    except (KeyError, ValueError):
        return str(template)


def voice_message(code: str, **values: Any) -> str:
    return render_message(code, "voice_text", **values)


def display_message(code: str, **values: Any) -> str:
    return render_message(code, "display_text", **values)


def is_safe_voice_text(value: str) -> bool:
    text = str(value or "").strip()
    if not text or any(term.casefold() in text.casefold() for term in TECHNICAL_TERMS):
        return False
    if len(re.findall(r"[.!?]+", text)) > 2 or text.count("?") > 1:
        return False
    return True


__all__ = [
    "MESSAGES",
    "TECHNICAL_TERMS",
    "display_message",
    "is_safe_voice_text",
    "render_message",
    "voice_message",
]
