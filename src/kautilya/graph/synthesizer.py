"""Synthesizer node (ARCHITECTURE.md §4): dual-register answers.

Legal register carries inline [chunk_id] citations; Simple register targets
Flesch-Kincaid grade <= 10 (one automatic simplification retry). Refuses
when retrieval is empty or the model reports insufficient context.
NLI claim verification arrives in Phase 4 (scope decision).
"""

from __future__ import annotations

import json
import re
from typing import Any

from kautilya.log import get_logger
from kautilya.llm.gemini import strip_fences

log = get_logger(__name__)

_CITE_RE = re.compile(r"\[([A-Za-z][A-Za-z0-9_]{2,60})\]")

SYNTH_PROMPT = """You are a careful assistant on Indian law. Answer STRICTLY \
from the sources given below - never invent sections or facts.

Return STRICT JSON only (no prose outside it):
{{
  "answer_legal": "<precise legal register; every claim cited inline as [CHUNK_ID]>",
  "answer_simple": "<same facts in plain language, Flesch-Kincaid grade <= 10, short sentences, no brackets>",
  "citations": ["<chunk_ids actually used>"],
  "refused": false,
  "reason": ""
}}

If the sources are insufficient, set "refused": true, leave answer_legal \
empty, and explain in answer_simple what is missing.

Incident date: {incident}
Regime routing: {regimes}
Old<->new equivalence notes: {equivalences}

Sources:
{sources}

Question: {query}"""


def _fmt_sources(retrieved: list[dict]) -> str:
    blocks = []
    for i, c in enumerate(retrieved, 1):
        label = c.get("title") or c.get("citation") or c.get("court") or ""
        head = f"[{c['chunk_id']}] {c.get('act_short', '')}"
        if c.get("section_no"):
            head += f" s.{c['section_no']}"
        if label:
            head += f" | {str(label)[:80]}"
        blocks.append(f"{head}\n{c.get('text', '')[:2400]}")
    return "\n\n".join(blocks)


def _parse_json(raw: str) -> dict[str, Any]:
    try:
        return json.loads(strip_fences(raw))
    except json.JSONDecodeError:
        m = json.loads(
            # last resort: outermost braces
            raw[raw.index("{"): raw.rindex("}") + 1])
        return m


def _fk_grade(text: str) -> float:
    try:
        import textstat

        return float(textstat.flesch_kincaid_grade(text))
    except Exception:  # noqa: BLE001 - metric must never break the pipeline
        return 0.0


_SIMPLIFY_PROMPT = """Rewrite the explanation below so a school student can \
understand it: short sentences (max ~15 words), everyday words, Flesch-Kincaid \
grade <= 8. Keep the meaning and section numbers. Reply with ONLY the \
rewritten text, no preamble.

Text: {text}"""


def synthesize(state: dict, llm=None) -> dict:
    """LangGraph node: `(state) -> partial state`."""
    retrieved = state.get("retrieved") or []
    if not retrieved:
        return {"route": "refuse",
                "answer_legal": "",
                "answer_simple": "I could not find any relevant legal "
                                 "provisions for this question in my "
                                 "database, so I cannot answer safely.",
                "citations": []}
    if llm is None:
        raise ValueError("synthesize requires an LLM client (generate method)")

    equiv_notes = "; ".join(e.note for e in state.get("equivalences", [])) or "none"
    prompt = SYNTH_PROMPT.format(
        incident=state.get("incident_date") or "not specified",
        regimes=state.get("regimes") or {},
        equivalences=equiv_notes,
        sources=_fmt_sources(retrieved),
        query=state.get("query_raw", ""),
    )
    if state.get("verification") == "fail":
        notes = "; ".join(state.get("verification_notes") or [])[:400]
        prompt += ("\n\nIMPORTANT: your previous attempt was rejected by the "
                   f"verifier for: {notes}. Cite only chunk_ids from the "
                   "sources above, and state each claim in words that appear "
                   "(or follow directly) from the cited text.")
    try:
        out = _parse_json(llm.generate(prompt))
    except Exception as e:  # noqa: BLE001
        log.warning("synthesizer: generation failed (%s)", e)
        return {"route": "refuse", "answer_legal": "", "answer_simple":
                f"Answer generation failed ({type(e).__name__}). "
                "Please try again.",
                "citations": []}

    if out.get("refused"):
        log.info("synthesizer: model refused (%s)", out.get("reason", ""))
        return {"route": "refuse", "answer_legal": "",
                "answer_simple": out.get("answer_simple") or
                out.get("reason") or "Insufficient context to answer.",
                "citations": []}

    valid_ids = {c["chunk_id"] for c in retrieved}
    cited = [cid for cid in dict.fromkeys(out.get("citations") or [])
             if cid in valid_ids]
    for m in _CITE_RE.findall(out.get("answer_legal", "")):
        if m in valid_ids and m not in cited:
            cited.append(m)

    simple = (out.get("answer_simple") or "").strip()
    grade = _fk_grade(simple)
    if grade > 10.0:
        try:
            simpler = strip_fences(
                llm.generate(_SIMPLIFY_PROMPT.format(text=simple)).strip())
            if simpler and _fk_grade(simpler) < grade:
                simple, grade = simpler, _fk_grade(simpler)
        except Exception as e:  # noqa: BLE001
            log.warning("synthesizer: simplify retry failed (%s)", e)
    if grade > 10.0:
        log.info("synthesizer: FK grade %.1f still above target", grade)

    return {"answer_legal": (out.get("answer_legal") or "").strip(),
            "answer_simple": simple,
            "citations": cited[:10],
            "route": None}
