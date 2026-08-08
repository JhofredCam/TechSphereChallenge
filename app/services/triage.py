"""Deterministic, conservative triage rules for Spanish patient messages.

The language model is deliberately not part of this module.  A patient message is
untrusted data: requests to suppress an alert or reveal internal instructions do
not change the clinical rules below.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from enum import Enum
from typing import Any, Iterable, Mapping


class TriageLevel(str, Enum):
    """The four decisions used by the call workflow."""

    RED = "red"
    YELLOW = "yellow"
    GREEN = "green"
    UNKNOWN = "unknown"


TRIAGE_LEVELS = ("red", "yellow", "green", "unknown")

# Unknown is intentionally above green when it is the current candidate.  An
# explicit well statement may clear a previous unknown, but never clears a
# previously established yellow or red decision.
_LEVEL_RANK = {"green": 0, "unknown": 1, "yellow": 2, "red": 3}
_LEVEL_ALIASES = {
    "rojo": "red",
    "amarillo": "yellow",
    "verde": "green",
    "desconocido": "unknown",
    "ambiguo": "unknown",
    "ambiguous": "unknown",
}


@dataclass(frozen=True, slots=True)
class _AlarmRule:
    code: str
    level: str
    label: str
    pattern: re.Pattern[str]


@dataclass(frozen=True, slots=True)
class TriageResult:
    """A JSON-friendly triage decision and the evidence for that decision."""

    level: str
    triggers: tuple[str, ...] = ()
    needs_clarification: bool = False
    questions: tuple[str, ...] = ()
    alert: bool = False
    prompt_injection_detected: bool = False
    normalized_text: str = ""
    rationale: str = ""
    trigger_details: tuple[Mapping[str, str], ...] = ()

    @property
    def level_es(self) -> str:
        return {
            "red": "rojo",
            "yellow": "amarillo",
            "green": "verde",
            "unknown": "desconocido",
        }.get(self.level, self.level)

    @property
    def is_alert(self) -> bool:
        return self.alert

    def to_dict(self) -> dict[str, Any]:
        """Return only values that FastAPI's JSON encoder can serialize."""

        return {
            "level": self.level,
            "level_es": self.level_es,
            "triggers": list(self.triggers),
            "trigger_details": [dict(item) for item in self.trigger_details],
            "needs_clarification": self.needs_clarification,
            "questions": list(self.questions),
            "alert": self.alert,
            "prompt_injection_detected": self.prompt_injection_detected,
            "normalized_text": self.normalized_text,
            "rationale": self.rationale,
        }

    # Mapping-style access is useful at the API boundary while retaining a
    # typed object for service callers.
    def __getitem__(self, key: str) -> Any:
        return self.to_dict()[key]

    def get(self, key: str, default: Any = None) -> Any:
        return self.to_dict().get(key, default)


def normalize_patient_text(value: str | None) -> str:
    """Normalize transcribed patient speech without interpreting instructions."""

    if value is None:
        return ""
    text = unicodedata.normalize("NFKC", str(value))
    # Control characters can be inserted by a transcript or an adversarial
    # client.  They have no clinical meaning and should not split a rule.
    text = "".join(" " if unicodedata.category(char).startswith("C") else char for char in text)
    return re.sub(r"\s+", " ", text).strip()


def _match_text(value: str) -> str:
    """Return a case/diacritic-insensitive representation for the rules."""

    decomposed = unicodedata.normalize("NFKD", value.casefold())
    without_marks = "".join(
        char for char in decomposed if not unicodedata.combining(char)
    )
    # Keep letters and numbers, but turn punctuation into spaces so phrase
    # boundaries remain deterministic across speech-to-text providers.
    return re.sub(r"[^\w]+", " ", without_marks, flags=re.UNICODE).strip()


def normalize_level(value: str | TriageLevel | None) -> str | None:
    """Normalize English or Spanish level labels used by API callers."""

    if value is None:
        return None
    if isinstance(value, TriageLevel):
        return value.value
    raw = str(value).strip().casefold()
    return _LEVEL_ALIASES.get(raw, raw if raw in _LEVEL_RANK else None)


def contains_prompt_injection(value: str | None) -> bool:
    """Detect common attempts to turn patient text into agent instructions."""

    text = _match_text(normalize_patient_text(value))
    if not text:
        return False
    patterns = (
        r"\bignora(?:r)?\b.{0,40}\b(?:instrucciones|reglas|alerta|seguridad)\b",
        r"\b(?:desatiende|desatender|desatiendan)\b.{0,60}\b(?:todas?\s+)?"
        r"(?:reglas?|normas?|instrucciones?|alertas?|seguridad)\b",
        r"\b(?:haz\s+caso\s+omiso|haga\s+caso\s+omiso)\b.{0,50}\b"
        r"(?:reglas?|normas?|instrucciones?|seguridad)\b",
        r"\b(?:ignore|disregard|forget|overlook)\b(?:\W+\w+){0,8}\W+"
        r"(?:rules?|instructions?|guidelines?|constraints?|prompts?|messages?|safety)\b",
        r"\b(?:disregard|ignore)\b.{0,60}\b(?:everything|all\s+(?:the\s+)?above)\b",
        r"\b(?:do\s+not|dont|don't)\s+follow\b.{0,45}\b(?:rules?|instructions?|"
        r"guidelines?|system|safety)\b",
        r"\b(?:revela|muestra|dime|entrega)\b.{0,35}\b(?:prompt|instrucciones|"
        r"mensaje del sistema)\b",
        r"\b(?:system prompt|mensaje del sistema|developer message|jailbreak)\b",
        r"\bactua como\b|\bhazte pasar por\b",
        r"\b(?:no alertes|no registres|no guardes|borra(?: el)? historial)\b",
        r"\b(?:cambia|baja|deja)\b.{0,25}\b(?:nivel|alerta|triage|triaje)\b",
        r"\b(?:di|diga)\b.{0,20}\b(?:que estoy bien|que no pasa nada)\b",
    )
    return any(re.search(pattern, text) for pattern in patterns)


def _is_negated(text: str, start: int) -> bool:
    """Avoid treating explicit absence of a symptom as the symptom itself.

    ``no puedo respirar`` is intentionally not negated: in Colombian Spanish
    that is a direct alarm statement, not a denial.
    """

    prefix = text[max(0, start - 42) : start]
    return bool(
        re.search(
            r"(?:\bno\s+(?:tengo|hay|presento|siento|se|esta|estoy)|"
            r"\bsin|\bnunca)\s*$|"
            r"\bno\s+(?:tengo|hay|presento|siento)\b.{0,25}\b(?:ni|y)\s*$",
            prefix,
        )
    )


def _compile_rules() -> tuple[_AlarmRule, ...]:
    # Rules are matched against _match_text(), so accents and capitalization do
    # not create separate clinical paths.
    raw_rules = (
        (
            "difficulty_breathing",
            "red",
            "dificultad para respirar",
            r"(?:tengo dificultad para respirar|presento dificultad para respirar|"
            r"dificultad para respirar|me cuesta respirar|me cuesta coger aire|"
            r"no puedo respirar|no respiro|no puedo coger aire|me falta el aire|"
            r"falta de aire|me ahogo|me estoy ahogando|me asfixio|me estoy asfixiando|"
            r"se me va el aire|respirar.{0,18}(?:dificil|complicado|cuesta))",
        ),
        (
            "chest_pain",
            "red",
            "dolor u opresion en el pecho",
            r"(?:dolor|opresion|presion|apretamiento|apretado|(?:me )?duele).{0,24}\bpecho\b|"
            r"\bpecho\b.{0,24}(?:duele|dolor|oprime|aprieta)",
        ),
        (
            "uncontrolled_bleeding",
            "red",
            "sangrado que no se detiene",
            r"(?:sangrad|sangre|hemorrag|desangr).{0,48}(?:no para|no se detiene|"
            r"a chorros|empapa|abundante|muchisima|mucho)|"
            r"\bdesangr\w*\b|"
            r"(?:botando|sale|me sale).{0,22}(?:much|abund|chorro).{0,15}sangr\w*|"
            r"(?:much|abund).{0,15}sangr\w*|"
            r"(?:no para|no se detiene|a chorros).{0,24}(?:sangr|sangre)",
        ),
        (
            "loss_of_consciousness",
            "red",
            "desmayo o perdida de conciencia",
            r"(?:me desmaye|se desmayo|me fui|perdi el conocimiento|"
            r"perdi la conciencia|estoy inconsciente|no responde|no despierta)",
        ),
        (
            "cyanosis",
            "red",
            "coloracion azulada o morada",
            r"(?:labios|cara|dedos|unas).{0,20}(?:morad|azul)|"
            r"(?:me puse|se puso).{0,12}(?:morado|azul)",
        ),
        (
            "seizure",
            "red",
            "convulsion",
            r"\bconvulsion(?:es|a|ando)?\b|\bataque epileptic\w*\b",
        ),
        (
            "severe_allergic_reaction",
            "red",
            "hinchazon de cara, labios o garganta",
            r"(?:se me|tengo|esta).{0,20}(?:hinch|inflam).{0,20}(?:cara|labios|lengua|garganta)|"
            r"(?:garganta|lengua).{0,20}(?:se cierra|hinch|inflam)",
        ),
        (
            "wound_dehiscence",
            "red",
            "herida abierta",
            r"(?:se me|se)\s*abrio\s*(?:la\s*)?herida|"
            r"(?:herida|operacion).{0,24}(?:abierta|separada).{0,24}(?:sale|veo)",
        ),
        (
            "severe_pain",
            "red",
            "dolor insoportable o extremo",
            r"(?:dolor|me duele).{0,28}(?:insoportable|inaguantable|no aguanto|"
            r"me esta matando|10 de 10|10 10|9 de 10|9 10)|"
            r"\bno aguanto (?:el )?dolor\b",
        ),
        (
            "neurologic_emergency",
            "red",
            "debilidad o perdida de sensibilidad repentina",
            r"(?:no puedo mover|no siento).{0,26}(?:brazo|pierna|lado|cara)|"
            r"(?:cara torcida|no puedo hablar|hablo enredado|se me duerme un lado)",
        ),
        (
            "blood_in_vomit_or_stool",
            "red",
            "sangre en vomito o heces negras",
            r"(?:vomit|vomito|devolvi).{0,25}sangre|sangre.{0,25}(?:vomit|vomito)|"
            r"\bheces negras\b",
        ),
        (
            "very_high_fever",
            "red",
            "temperatura extremadamente alta",
            r"(?:fiebre|temperatura|calentura).{0,12}\b(?:4[1-9]|[5-9]\d)(?:[.,]\d+)?\b",
        ),
        (
            "fever_or_chills",
            "yellow",
            "fiebre, calentura o escalofrios",
            r"\b(?:fiebre|calentura|temperatura alta|escalofrio|escalofrios|"
            r"tembladera)\b",
        ),
        (
            "infected_wound_signs",
            "yellow",
            "cambios preocupantes en la herida",
            r"(?:herida|incision|punto\w*).{0,50}(?:roja|colorada|hinch|caliente|pus|"
            r"secrecion|liquido|huele feo|mal olor|bota|botando)|"
            r"\b(?:pus|secrecion purulenta)\b",
        ),
        (
            "worsening_or_uncontrolled_pain",
            "yellow",
            "dolor que aumenta o no mejora",
            r"(?:dolor|me duele).{0,35}(?:mucho|harto|fuerte|moderado|aument|empeor|"
            r"no se quita|no mejora|persist|cada vez)|"
            r"\b(?:me duele mucho|me duele harto|el dolor empeora)\b",
        ),
        (
            "persistent_vomiting",
            "yellow",
            "vomito o incapacidad para retener liquidos",
            r"(?:vomit|vomito|devolv).{0,30}(?:varias veces|mucho|no para|persist)|"
            r"no puedo (?:retener|mantener).{0,20}(?:liquid|agua|comida)",
        ),
        (
            "diarrhea",
            "yellow",
            "diarrea persistente",
            r"\bdiarrea\b.{0,25}(?:much|varias|persist|no para)?",
        ),
        (
            "unilateral_leg_swelling",
            "yellow",
            "hinchazon o dolor de una pierna",
            r"(?:pierna|pantorrilla|gemelo).{0,35}(?:hinch|inflam|dolor|caliente)|"
            r"(?:hinch|inflam).{0,25}(?:una pierna|una pantorrilla)",
        ),
        (
            "urinary_problem",
            "yellow",
            "dificultad importante para orinar",
            r"(?:no he orin|no puedo orin|no sale orin|orino muy poco|ardor al orinar)",
        ),
        (
            "dizziness",
            "yellow",
            "mareo persistente",
            r"\b(?:maread|mareo|me da vueltas|vertigo)\w*\b",
        ),
        (
            "minor_bleeding",
            "yellow",
            "sangrado o manchado reportado",
            r"\b(?:sangrad|sangre|manchad)\w*\b",
        ),
        (
            "moderate_fever_value",
            "yellow",
            "temperatura por encima de lo esperado",
            r"(?:fiebre|temperatura|calentura).{0,12}\b(?:3[89]|40)(?:[.,]\d+)?\b",
        ),
    )
    return tuple(
        _AlarmRule(code, level, label, re.compile(pattern))
        for code, level, label, pattern in raw_rules
    )


_ALARM_RULES = _compile_rules()


def _find_trigger_details(value: str | None) -> list[dict[str, str]]:
    text = _match_text(normalize_patient_text(value))
    details: list[dict[str, str]] = []
    seen: set[str] = set()
    for rule in _ALARM_RULES:
        match = rule.pattern.search(text)
        if match is None or _is_negated(text, match.start()):
            continue
        if rule.code in seen:
            continue
        seen.add(rule.code)
        details.append(
            {
                "code": rule.code,
                "level": rule.level,
                "label": rule.label,
                "matched": match.group(0),
            }
        )
    return details


def find_alarm_triggers(value: str | None) -> list[str]:
    """Return stable trigger codes found in a Spanish patient message."""

    return [item["code"] for item in _find_trigger_details(value)]


def _trigger_level(trigger: Any) -> str | None:
    if isinstance(trigger, Mapping):
        return normalize_level(trigger.get("level"))
    if isinstance(trigger, TriageLevel):
        return trigger.value
    raw = str(trigger).strip().casefold()
    if raw in _LEVEL_ALIASES or raw in _LEVEL_RANK:
        return normalize_level(raw)
    for rule in _ALARM_RULES:
        if raw == rule.code:
            return rule.level
    return None


def highest_level(
    triggers: Iterable[Any] | str | None,
    previous_level: str | TriageLevel | None = None,
) -> str:
    """Choose the most severe level, never lowering a prior decision."""

    previous = normalize_level(previous_level)
    candidate = "green"
    if isinstance(triggers, str):
        trigger_values: Iterable[Any] = (triggers,)
    elif triggers is None:
        trigger_values = ()
    else:
        trigger_values = triggers
    for trigger in trigger_values:
        level = _trigger_level(trigger)
        if level is not None and _LEVEL_RANK[level] > _LEVEL_RANK[candidate]:
            candidate = level
    # Red and yellow are sticky safety decisions.  Unknown is deliberately not
    # sticky: an explicit green statement is the evidence needed to clear it.
    if previous in {"red", "yellow"} and _LEVEL_RANK[previous] > _LEVEL_RANK[candidate]:
        return previous
    return candidate


def _has_possible_symptom(text: str) -> bool:
    return bool(
        re.search(
            r"\b(?:dolor|duele|fiebre|calentura|herida|incision|nausea|vomit|"
            r"diarrea|sangre|sangrado|mareo|hinch|inflam|ardor|tos|respir|"
            r"escalofrio|cansancio|molestia|sintoma)\w*\b",
            text,
        )
    )


def _is_explicitly_well(text: str) -> bool:
    if re.search(
        r"\b(?:me siento bien|estoy bien|todo bien|voy bien|estoy normal|"
        r"sin molestias?|sin sintomas?|no tengo sintomas?|no me duele nada|"
        r"no tengo (?:fiebre|dolor|molestias?|sangrado|sintomas?)|"
        r"sin (?:fiebre|dolor|molestias?|sangrado|sintomas?)|"
        r"recuperandome bien|la recuperacion va bien|hola|buenas)\b",
        text,
    ):
        return True
    return bool(
        re.search(r"\b(?:dolor|molestia)\w*\b.{0,16}\b(?:leve|poquito|ligero)\b", text)
        and not re.search(r"\b(?:empeor|aument|no se quita|no mejora)\w*\b", text)
    )


def _is_general_care_question(text: str) -> bool:
    """Do not make a routine care question look like an ambiguous symptom."""

    return bool(
        re.search(
            r"\b(?:como|que|cual|cuando|puedo|debo)\b.{0,45}\b(?:vigilo|cuido|"
            r"limpio|reviso|hago|tomar|hacer|manejo|manejar|cuidados?|dice|"
            r"indica|significa|recomienda|establece|informacion|protocolo|guia)\b",
            text,
        )
    )


def _questions_for(text: str) -> tuple[str, ...]:
    if re.search(r"\b(?:dolor|duele)\w*\b", text):
        return (
            "\u00bfEn que parte siente el dolor, que intensidad tiene de 0 a 10 y desde "
            "cuando empezo?",
        )
    if re.search(r"\b(?:fiebre|calentura|temperatura|escalofrio)\w*\b", text):
        return ("\u00bfQue temperatura exacta tiene y desde cuando?",)
    if re.search(r"\b(?:herida|incision|punto)\w*\b", text):
        return ("\u00bfLa herida esta abierta, sangra o tiene secrecion?",)
    if re.search(r"\b(?:vomit|nausea|diarrea)\w*\b", text):
        return ("\u00bfCuantas veces ha ocurrido y puede retener agua?",)
    return (
        "\u00bfQue sintoma tiene exactamente, donde lo siente y desde cuando?",
    )


def classify_triage(
    value: str | None,
    previous_level: str | TriageLevel | None = None,
) -> TriageResult:
    """Classify one turn with conservative escalation and ambiguity handling."""

    normalized = normalize_patient_text(value)
    searchable = _match_text(normalized)
    details = _find_trigger_details(normalized)
    triggers = [item["code"] for item in details]
    current_level = highest_level(details)

    if not details:
        if _is_explicitly_well(searchable):
            current_level = "green"
        elif _is_general_care_question(searchable):
            current_level = "green"
        else:
            current_level = "unknown"

    level = highest_level((current_level,), previous_level)
    injection = contains_prompt_injection(normalized)
    needs_clarification = level == "unknown"
    questions = _questions_for(searchable) if needs_clarification else ()

    if level == "red":
        rationale = "Se detecto una senal de alarma que requiere escalamiento inmediato."
    elif level == "yellow":
        rationale = "Se detecto una senal que requiere contacto oportuno con el equipo clinico."
    elif level == "unknown":
        rationale = "La descripcion no permite decidir con seguridad; se necesita aclaracion."
    else:
        rationale = "No se detecto una senal de alarma en la informacion disponible."

    return TriageResult(
        level=level,
        triggers=tuple(triggers),
        needs_clarification=needs_clarification,
        questions=questions,
        alert=level in {"red", "yellow"},
        prompt_injection_detected=injection,
        normalized_text=normalized,
        rationale=rationale,
        trigger_details=tuple(details),
    )


# A few explicit aliases make the functional boundary easy to discover from
# route code and preserve the wording used in the MVP specification.
triage = classify_triage
classify = classify_triage


__all__ = [
    "TRIAGE_LEVELS",
    "TriageLevel",
    "TriageResult",
    "classify",
    "classify_triage",
    "contains_prompt_injection",
    "find_alarm_triggers",
    "highest_level",
    "normalize_level",
    "normalize_patient_text",
    "triage",
]
