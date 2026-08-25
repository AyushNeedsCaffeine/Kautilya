"""Shared LangGraph pipeline state (ARCHITECTURE.md §4 node contracts)."""

from __future__ import annotations

from typing import TypedDict

from kautilya.schemas import Equivalence


class PipelineState(TypedDict, total=False):
    # QueryAnalyzer
    query_raw: str
    input_lang: str          # ISO 639-1, from settings.languages
    domains: list[str]
    entities: list[str]
    incident_date: str | None  # ISO yyyy-mm-dd (strings keep state serializable)
    needs_date: bool
    final_lang: str
    # TemporalResolver
    regimes: dict[str, str]    # domain -> old|new|current|mixed
    equivalences: list[Equivalence]
    route: str | None          # "ask_date" | "refuse" | None(=continue)
    # HybridRetriever
    retrieved: list[dict]
    # Synthesizer
    answer_legal: str
    answer_simple: str
    citations: list[str]       # chunk_ids actually cited
    retries: int
    # Verifier (Phase 4)
    verification: str            # pass | fail | skipped
    verification_notes: list[str]


KNOWN_DOMAINS = (
    "criminal_substantive",
    "criminal_procedure",
    "evidence",
    "labour",
    "tax",
    "constitutional",
    "general",
)
