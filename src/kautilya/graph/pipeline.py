"""LangGraph pipeline wiring (ARCHITECTURE.md section 2/4).

analyze -> resolve --(ask_date)--> END
                 \\-> retrieve -> synthesize -> verify -> translate -> END
"""

from __future__ import annotations

import time

from kautilya.graph.analyzer import analyze_query
from kautilya.graph.resolver import resolve_temporal
from kautilya.graph.state import PipelineState
from kautilya.graph.synthesizer import synthesize
from kautilya.graph.verifier import NLIVerifier, verify
from kautilya.indexing.search import HybridRetriever, retrieve_node
from kautilya.log import get_logger
from kautilya.translate.indictrans2 import IndicTranslator

log = get_logger(__name__)


def translate_node(state: dict, translator: IndicTranslator | None = None) -> dict:
    """Translate answer_simple into final_lang (after verification passes)."""
    final_lang = state.get("final_lang") or "en"
    if final_lang == "en":
        return {"answer_translated": None}
    answer = state.get("answer_simple") or ""
    if not answer or state.get("route") in ("refuse", "ask_date"):
        return {"answer_translated": None}
    if translator is None:
        translator = IndicTranslator()
    try:
        translated = translator.translate(answer, "en", final_lang)
        log.info("translate: %d chars %s -> %d chars %s",
                 len(answer), "en", len(translated), final_lang)
        return {"answer_translated": translated}
    except Exception as e:
        log.warning("translate failed: %s — falling back to English", e)
        return {"answer_translated": answer}


def build_pipeline(llm=None,
                   retriever: HybridRetriever | None = None,
                   nli: NLIVerifier | None = None,
                   translator: IndicTranslator | None = None,
                   threshold: float = 0.75,
                   max_regen: int = 2):
    """Compile the graph; inject fakes for tests."""
    from langgraph.graph import END, StateGraph

    g = StateGraph(PipelineState)
    g.add_node("analyze", lambda s: analyze_query(s, llm=llm))
    g.add_node("resolve", resolve_temporal)
    g.add_node("retrieve", lambda s: retrieve_node(s, retriever=retriever))
    g.add_node("synthesize", lambda s: synthesize(s, llm=llm))
    g.add_node("verify", lambda s: verify(s, nli=nli, threshold=threshold,
                                          max_regen=max_regen))
    g.add_node("translate", lambda s: translate_node(s, translator=translator))

    g.set_entry_point("analyze")
    g.add_edge("analyze", "resolve")
    g.add_conditional_edges(
        "resolve",
        lambda s: "ask" if s.get("route") == "ask_date" else "continue",
        {"ask": END, "continue": "retrieve"},
    )
    g.add_edge("retrieve", "synthesize")
    g.add_edge("synthesize", "verify")

    def _verify_route(s: dict) -> str:
        if s.get("route") == "error":
            return "error"
        return s.get("route") or "pass"

    g.add_conditional_edges(
        "verify",
        _verify_route,
        {"pass": "translate", "regenerate": "synthesize",
         "refuse": END, "error": END},
    )
    g.add_edge("translate", END)
    return g.compile()


def _init_state(query: str,
                incident_date: str | None = None,
                final_lang: str | None = None) -> dict:
    init: dict = {"query_raw": query.strip(), "retries": 0}
    if incident_date:
        init["incident_date"] = incident_date
        init["needs_date"] = False
    if final_lang:
        init["final_lang"] = final_lang
    return init


def iter_steps(query: str,
               llm=None,
               retriever: HybridRetriever | None = None,
               nli: NLIVerifier | None = None,
               translator: IndicTranslator | None = None,
               incident_date: str | None = None,
               final_lang: str | None = None,
               threshold: float = 0.75,
               max_regen: int = 2,
               timeout_s: float = 0.0):
    """Yield ``(node_name, accumulated_state)`` as the graph executes.

    Lets the UI render live per-node progress; nodes fail fast because the
    UI threads ``retries=1`` through the LLM clients. ``run_query`` is a thin
    wrapper that consumes this generator so all callers share one code path.
    """
    app = build_pipeline(llm=llm, retriever=retriever, nli=nli,
                         translator=translator,
                         threshold=threshold, max_regen=max_regen)
    init = _init_state(query, incident_date=incident_date,
                       final_lang=final_lang)
    yield ("start", dict(init))
    state: dict = dict(init)
    t0 = time.time()
    for update in app.stream(init, stream_mode="updates"):
        for node, partial in update.items():
            state.update(partial)
            if timeout_s and (time.time() - t0) > timeout_s:
                raise TimeoutError(
                    f"query exceeded the {timeout_s:.0f}s safety timeout")
            yield (node, dict(state))
    yield ("end", state)


def run_query(query: str,
              llm=None,
              retriever: HybridRetriever | None = None,
              nli: NLIVerifier | None = None,
              translator: IndicTranslator | None = None,
              incident_date: str | None = None,
              final_lang: str | None = None,
              threshold: float = 0.75,
              max_regen: int = 2) -> dict:
    out: dict = {}
    for _node, state in iter_steps(
            query, llm=llm, retriever=retriever, nli=nli, translator=translator,
            incident_date=incident_date, final_lang=final_lang,
            threshold=threshold, max_regen=max_regen):
        out = state
    log.info("pipeline: route=%s verification=%s citations=%d",
             out.get("route"), out.get("verification"),
             len(out.get("citations", [])))
    return out
