"""LangGraph pipeline wiring (ARCHITECTURE.md §2/§4).

analyze -> resolve --(ask_date)--> END
                 \--> retrieve -> synthesize -> END
"""

from __future__ import annotations

from kautilya.graph.analyzer import analyze_query
from kautilya.graph.resolver import resolve_temporal
from kautilya.graph.state import PipelineState
from kautilya.graph.synthesizer import synthesize
from kautilya.indexing.search import HybridRetriever, retrieve_node
from kautilya.log import get_logger

log = get_logger(__name__)


def build_pipeline(llm=None, retriever: HybridRetriever | None = None):
    """Compile the graph; inject fakes for tests."""
    from langgraph.graph import END, StateGraph

    g = StateGraph(PipelineState)
    g.add_node("analyze", lambda s: analyze_query(s, llm=llm))
    g.add_node("resolve", resolve_temporal)
    g.add_node("retrieve", lambda s: retrieve_node(s, retriever=retriever))
    g.add_node("synthesize", lambda s: synthesize(s, llm=llm))

    g.set_entry_point("analyze")
    g.add_edge("analyze", "resolve")
    g.add_conditional_edges(
        "resolve",
        lambda s: "ask" if s.get("route") == "ask_date" else "continue",
        {"ask": END, "continue": "retrieve"},
    )
    g.add_edge("retrieve", "synthesize")
    g.add_edge("synthesize", END)
    return g.compile()


def run_query(query: str,
              llm=None,
              retriever: HybridRetriever | None = None,
              incident_date: str | None = None,
              final_lang: str | None = None) -> dict:
    app = build_pipeline(llm=llm, retriever=retriever)
    init: dict = {"query_raw": query.strip(), "retries": 0}
    if incident_date:
        init["incident_date"] = incident_date
        init["needs_date"] = False
    if final_lang:
        init["final_lang"] = final_lang
    out = app.invoke(init)
    log.info("pipeline: route=%s citations=%d", out.get("route"),
             len(out.get("citations", [])))
    return out
