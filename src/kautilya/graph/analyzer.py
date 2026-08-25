"""QueryAnalyzer node (ARCHITECTURE.md §4): LLM-first with offline fallback.

The fallback classifier keeps the pipeline testable and usable without a
Gemini key: unicode-range language detection, keyword domains, regex dates.
"""

from __future__ import annotations

import calendar
import re
from datetime import date as _date
from typing import Any

from kautilya.graph.state import KNOWN_DOMAINS
from kautilya.log import get_logger

log = get_logger(__name__)

# ---------------------------------------------------------------- language
_SCRIPT_RANGES = (
    ("hi", (0x0900, 0x097F)),   # Devanagari (covers mr by convention too)
    ("bn", (0x0980, 0x09FF)),
    ("ta", (0x0B80, 0x0BFF)),
    ("te", (0x0C00, 0x0C7F)),
    ("gu", (0x0A80, 0x0AFF)),
    ("kn", (0x0C80, 0x0CFF)),
)
_ROMAN_HI_CUES = (" mein ", " kya ", " hai", " tha", " thi", " ka ", " ki ")

SUPPORTED_LANGS = ("en", "hi", "mr", "bn", "ta", "te", "gu", "kn")


def detect_language(text: str) -> str:
    for lang, (lo, hi_) in _SCRIPT_RANGES:
        if any(lo <= ord(ch) <= hi_ for ch in text):
            return lang
    padded = f" {text.lower()} "
    if any(cue in padded for cue in _ROMAN_HI_CUES):
        return "hi"
    return "en"


# ------------------------------------------------------------------ dates
_MONTHS = {m.lower(): i for i, m in enumerate(calendar.month_name) if m}
for _abbr, _num in ((m.lower(), i) for i, m in enumerate(calendar.month_abbr) if m):
    _MONTHS.setdefault(_abbr, _num)

_ISO_RE = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")
_DMY_RE = re.compile(r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{4})\b")
_MY_RE = re.compile(
    r"\b(" + "|".join(_MONTHS) + r")\.?,?\s+(\d{4})\b", re.IGNORECASE
)
_Y_RE = re.compile(r"\b(19|20)\d{2}\b")


def parse_date(text: str) -> str | None:
    """Best-effort date extraction -> ISO string (partial info = first of period)."""
    if m := _ISO_RE.search(text):
        y, mo, d = map(int, m.groups())
        try:
            return _date(y, mo, d).isoformat()
        except ValueError:
            pass
    if m := _DMY_RE.search(text):
        d, mo, y = map(int, m.groups())
        try:
            return _date(y, mo, d).isoformat()
        except ValueError:
            pass
    if m := _MY_RE.search(text):
        mo = _MONTHS[m.group(1).lower().rstrip(".")]
        return _date(int(m.group(2)), mo, 1).isoformat()
    if m := _Y_RE.search(text):
        return _date(int(m.group(0)), 1, 1).isoformat()
    return None


_PAST_TENSE_CUES = (
    " was ", " were ", " at that time", " back then", " earlier ",
    " before ", " thi ", " tha ", " hui ", " hua ", " pehle",
)


def needs_incident_date(text: str, has_date: bool) -> bool:
    if has_date:
        return False
    padded = f" {text.lower()} "
    return any(cue in padded for cue in _PAST_TENSE_CUES)


# ----------------------------------------------------------------- domains
_DOMAIN_KEYWORDS: dict[str, tuple[str, ...]] = {
    "criminal_substantive": (
        "murder", "cheating", "cheated", "fraud", "theft", "assault", "hurt",
        "culpable", "kidnap", "dowry", "defamation", "dacoit", "rape",
        "criminal conspiracy", "punishment for", "sedition",
        "cruelty", "modesty", "personation", "extortion", "mischief",
        "302", "303", "304", "306", "307", "318", "320", "420", "498a",
        # romanised-Hindi crime terms
        "hatya", "dhokha", "chori", "dakaity", "balatkar", "dahej",
    ),
    "criminal_procedure": (
        "fir", "bail", "arrest", "police", "chargesheet", "charge sheet",
        "cognizable", "summons", "warrant", "magistrate", "anticipatory",
        "trial", "investigation", "maintenance", "legal aid",
        "incrimination", "girftari", "zero fir",
        "154", "173", "437", "438", "482", "480",
    ),
    "evidence": (
        "evidence", "witness", "admissib", "presumption", "burden of proof",
        "electronic record", "electronic evidence", "digital record",
        "certificate", "confession", "relevant fact", "dying declaration",
        "expert opinion", "opinions of experts",
        "65b", "63",
    ),
    "labour": (
        "gratuity", "provident", "pf ", "esi", "wages", "salary", "bonus",
        "maternity", "factory", "retrenchment", "layoff", "notice period",
        "labour code", "industrial dispute", "worker", "employee",
    ),
    "tax": (
        "income tax", "itr", "gst", "assessment", "refund", "deduction",
        "tds", "pan ", "capital gains", "80c", "80d", "surcharge",
    ),
    "constitutional": (
        "constitution", "article 14", "article 19", "article 21",
        "fundamental right", "writ", "public interest litigation", "pil",
        "amendment",
    ),
}


def detect_domains(text: str) -> list[str]:
    low = text.lower()
    hits = [dom for dom, kws in _DOMAIN_KEYWORDS.items()
            if any(kw in low for kw in kws)]
    return hits[:3] or ["general"]


# ------------------------------------------------------------------- node
ANALYZER_PROMPT = """You are the query analyzer of an Indian-law RAG system.
Analyse the user's question and reply with STRICT JSON only (no prose):

{{
  "input_lang": "<ISO 639-1 code of the question's language>",
  "domains": "<subset of: criminal_substantive, criminal_procedure, evidence, labour, tax, constitutional, general>",
  "entities": ["<key legal concepts / acts / section numbers>"],
  "incident_date": "<YYYY-MM-DD or null — the date the incident happened, not today>",
  "needs_date": <true only if a past-tense question implies an incident date that is missing>,
  "final_lang": "<ISO 639-1 code the answer should be written in>"
}}

Question: {query}
"""


def _coerce(raw: dict[str, Any]) -> dict[str, Any]:
    domains = [d for d in raw.get("domains", []) if d in KNOWN_DOMAINS][:3]
    out: dict[str, Any] = {
        "input_lang": raw.get("input_lang") or "en",
        "domains": domains or ["general"],
        "entities": [str(e)[:60] for e in (raw.get("entities") or [])][:10],
        "incident_date": parse_date(str(raw.get("incident_date") or "")),
        "needs_date": bool(raw.get("needs_date")),
        "final_lang": raw.get("final_lang") or "en",
    }
    if out["incident_date"]:
        out["needs_date"] = False
    for k in ("input_lang", "final_lang"):
        if out[k] not in SUPPORTED_LANGS:
            out[k] = "en"
    return out


def analyze_query(state: dict, llm=None) -> dict:
    """LangGraph node: `(state) -> partial state`."""
    q = state.get("query_raw", "").strip()
    kw_domains = detect_domains(q)

    if llm is not None:
        try:
            coerced = _coerce(llm.generate_json(
                ANALYZER_PROMPT.format(query=q)))
            # Union LLM + keyword signals: retrieval only widens, and a
            # confident-but-wrong LLM label (e.g. "general" for a cheating
            # query) must not starve the retriever's act allowlist.
            merged = [d for d in dict.fromkeys(
                coerced["domains"] + kw_domains) if d != "general"][:3]
            coerced["domains"] = merged or ["general"]
            coerced["query_raw"] = q
            log.info("analyzer: LLM path ok (%s)", coerced["domains"])
            return coerced
        except Exception as e:  # noqa: BLE001 - degrade gracefully
            log.warning("analyzer: LLM failed (%s); using fallback", e)

    lang = detect_language(q)
    has_date = parse_date(q) is not None
    partial: dict[str, Any] = {
        "query_raw": q,
        "input_lang": lang,
        "domains": kw_domains,
        "entities": [],
        "incident_date": parse_date(q),
        "needs_date": needs_incident_date(q, has_date),
        "final_lang": lang if lang in SUPPORTED_LANGS else "en",
    }
    log.info("analyzer: fallback path (%s)", partial["domains"])
    return partial
