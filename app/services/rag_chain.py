"""Visible RAG orchestration nodes with deterministic safety boundaries."""

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Sequence

from .messages import voice_message
from .prompts import PromptBundle, build_grounded_prompt, validate_prompt_contract
from .rag import RagService
from .triage import TriageResult, classify_triage, contains_prompt_injection


@dataclass(frozen=True, slots=True)
class ChainResponse:
    text: str
    patient_text: str
    sources: tuple[Mapping[str, Any], ...]
    triage: TriageResult
    grounded: bool
    abstained: bool
    reason: str | None
    prompt_version: str
    node_latency_ms: Mapping[str, float]


def _safe_candidate(candidate: str, sources: Sequence[Mapping[str, Any]]) -> bool:
    if not candidate or len(candidate) > 5_000:
        return False
    if re.search(r"(?:<source|system prompt|ignore previous|dosis de)\b", candidate, re.I):
        return False
    source_ids = {str(source.get("chunk_id")) for source in sources}
    return not sources or any(source_id in candidate for source_id in source_ids)


class RagChain:
    """Small named-node pipeline; model invocation is an injected, bounded callable."""

    def __init__(
        self,
        rag: RagService,
        *,
        model: Callable[[PromptBundle], str] | None = None,
        limit: int = 5,
    ) -> None:
        self.rag = rag
        self.model = model
        self.limit = limit

    def normalize_query(self, message: str) -> str:
        return str(message or "").strip()

    def classify_triage(self, message: str, previous_level: str | None = None) -> TriageResult:
        return classify_triage(message, previous_level=previous_level)

    def retrieve_candidates(self, message: str) -> list[Any]:
        return self.rag.retrieve(message, limit=self.limit)

    def hydrate_and_validate(self, candidates: Sequence[Any]) -> list[Mapping[str, Any]]:
        rows: list[Mapping[str, Any]] = []
        for candidate in candidates:
            if hasattr(candidate, "__dict__"):
                row = dict(candidate.__dict__)
            elif hasattr(candidate, "to_dict"):
                row = dict(candidate.to_dict())
            else:
                row = dict(candidate)
            if row.get("chunk_id") and row.get("text") and row.get("filename"):
                rows.append(row)
        return rows

    def build_context(
        self,
        message: str,
        triage: TriageResult,
        sources: Sequence[Mapping[str, Any]],
    ) -> PromptBundle:
        bundle = build_grounded_prompt(message, triage.level, sources)
        validate_prompt_contract(bundle)
        return bundle

    def validate_answer(self, candidate: str, sources: Sequence[Mapping[str, Any]]) -> str | None:
        return candidate.strip() if _safe_candidate(candidate, sources) else None

    def fallback_or_abstain(self, triage: TriageResult, reason: str) -> tuple[str, bool]:
        if triage.level == "red":
            return voice_message("TRIAGE_RED"), True
        if triage.level == "yellow":
            return voice_message("TRIAGE_YELLOW"), True
        if reason == "prompt_injection":
            return voice_message("PROMPT_INJECTION"), True
        return voice_message("NO_EVIDENCE"), True

    def run(self, message: str, *, previous_level: str | None = None) -> ChainResponse:
        timings: dict[str, float] = {}
        started = time.perf_counter()
        normalized = self.normalize_query(message)
        timings["normalize_query"] = round((time.perf_counter() - started) * 1000, 3)
        triage_started = time.perf_counter()
        triage = self.classify_triage(normalized, previous_level)
        timings["classify_triage"] = round((time.perf_counter() - triage_started) * 1000, 3)
        retrieve_started = time.perf_counter()
        candidates = (
            []
            if contains_prompt_injection(normalized)
            else self.retrieve_candidates(normalized)
        )
        timings["retrieve_candidates"] = round((time.perf_counter() - retrieve_started) * 1000, 3)
        sources = self.hydrate_and_validate(candidates)
        timings["hydrate_and_validate"] = 0.0
        prompt = self.build_context(normalized, triage, sources)
        timings["build_context"] = round((time.perf_counter() - retrieve_started) * 1000, 3)
        reason: str | None = None
        grounded = False
        abstained = False
        candidate_text: str | None = None
        if contains_prompt_injection(normalized):
            reason = "prompt_injection"
        elif triage.needs_clarification:
            reason = "clarification_required"
        elif sources and self.model is not None:
            try:
                candidate_text = self.validate_answer(self.model(prompt), sources)
                reason = None if candidate_text else "invalid_model_output"
            except Exception:
                reason = "model_unavailable"
        else:
            reason = "no_current_evidence" if not sources else "model_not_configured"
        if candidate_text:
            text = candidate_text
            grounded = True
        else:
            text, abstained = self.fallback_or_abstain(triage, reason or "no_evidence")
        timings["validate_answer"] = round((time.perf_counter() - started) * 1000, 3)
        return ChainResponse(
            text=text,
            patient_text=text,
            sources=tuple(sources),
            triage=triage,
            grounded=grounded,
            abstained=abstained,
            reason=reason,
            prompt_version=prompt.version,
            node_latency_ms=timings,
        )


__all__ = ["ChainResponse", "RagChain"]
