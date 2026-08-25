"""Streamlit chat UI for Kautilya — legal RAG over Indian law.

Run:  Kautilya-venv/bin/streamlit run src/kautilya/ui/app.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# ensure src/ is importable when launched via `streamlit run`
_src = str(Path(__file__).resolve().parents[2])
if _src not in sys.path:
    sys.path.insert(0, _src)

import streamlit as st

st.set_page_config(page_title="Kautilya", page_icon="⚖️", layout="centered")

# ── heavy resources (cached across Streamlit reruns) ──────────────────────

@st.cache_resource(show_spinner="Loading LLM...")
def _get_llm():
    from kautilya.llm.gemini import GeminiClient
    from kautilya.graph.pipeline import load_settings
    settings = load_settings(Path("config/settings.yaml"))
    return GeminiClient(model=settings.llm.model,
                        temperature=settings.llm.temperature), settings


@st.cache_resource(show_spinner="Loading retriever (bge-m3 + reranker)...")
def _get_retriever(settings):
    from kautilya.indexing.build_index import IndexConfig
    from kautilya.indexing.search import HybridRetriever
    idx = IndexConfig.from_settings(Path("config/settings.yaml"))
    ret = settings.retrieval
    return HybridRetriever(persist=idx.persist, dense_k=ret.dense_k,
                           sparse_k=ret.sparse_k, rrf_k=ret.rrf_k,
                           final_k=ret.final_k)


@st.cache_resource(show_spinner="Loading NLI verifier...")
def _get_nli(settings):
    from kautilya.graph.verifier import NLIVerifier
    return NLIVerifier(settings.verifier.nli_model)


@st.cache_resource(show_spinner="Loading translator (IndicTrans2)...")
def _get_translator():
    from kautilya.translate.indictrans2 import IndicTranslator
    return IndicTranslator()


# ── sidebar ───────────────────────────────────────────────────────────────

st.sidebar.title("⚖️ Kautilya")
st.sidebar.caption("Time-aware legal RAG over Indian law")

legal_only = st.sidebar.toggle("Legal register only", value=False)
simple_only = st.sidebar.toggle("Simple register only", value=True)

LANGUAGES = {
    "English": "en", "Hindi": "hi", "Marathi": "mr",
    "Bengali": "bn", "Tamil": "ta", "Telugu": "te",
    "Gujarati": "gu", "Kannada": "kn",
}
lang_name = st.sidebar.selectbox("Answer language", list(LANGUAGES.keys()),
                                  index=0)
final_lang = LANGUAGES[lang_name]

incident_date = st.sidebar.date_input("Incident date (optional)", value=None)
date_str = incident_date.isoformat() if incident_date else None

no_verify = st.sidebar.toggle("Skip NLI verification", value=False)

st.sidebar.divider()
st.sidebar.caption("Built with LangGraph + bge-m3 + mDeBERTa + IndicTrans2")

# ── chat history ──────────────────────────────────────────────────────────

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ── user input ────────────────────────────────────────────────────────────

query = st.chat_input("Ask a legal question about Indian law...")

if not query:
    st.stop()

# display user message
st.session_state.messages.append({"role": "user", "content": query})
with st.chat_message("user"):
    st.markdown(query)

# ── run pipeline ──────────────────────────────────────────────────────────

with st.chat_message("assistant"):
    with st.spinner("Thinking..."):
        try:
            llm, settings = _get_llm()
            retriever = _get_retriever(settings)
            nli = None if no_verify else _get_nli(settings)
            translator = _get_translator()

            from kautilya.graph.pipeline import run_query
            result = run_query(
                query, llm=llm, retriever=retriever, nli=nli,
                translator=translator,
                incident_date=date_str,
                final_lang=final_lang,
            )
        except Exception as exc:
            st.error(f"Pipeline error: {exc}")
            st.stop()

    # ── render result ─────────────────────────────────────────────────
    route = result.get("route")

    if route == "ask_date":
        st.info("This looks like a past-incident question. "
                "Please set an incident date in the sidebar and try again.")
        st.session_state.messages.append(
            {"role": "assistant",
             "content": "Please set an incident date and re-ask."})
        st.stop()

    if route == "refuse":
        note = (result.get("answer_simple")
                or "Could not verify an answer from the retrieved sources.")
        st.warning(note)
        notes = result.get("verification_notes") or []
        if notes:
            st.caption("Verifier: " + "; ".join(n[:120] for n in notes[:3]))
        st.session_state.messages.append({"role": "assistant", "content": note})
        st.stop()

    # ── success: show answer(s) ───────────────────────────────────────
    answer_parts: list[str] = []

    if not simple_only:
        legal = result.get("answer_legal", "")
        if legal:
            st.markdown(f"**Legal register:**\n\n{legal}")
            answer_parts.append(legal)

    if not legal_only:
        # show translated version if available, else simple English
        translated = result.get("answer_translated")
        if translated and final_lang != "en":
            st.markdown(f"**Simple register ({lang_name}):**\n\n{translated}")
            answer_parts.append(translated)
        else:
            simple = result.get("answer_simple", "")
            if simple:
                st.markdown(f"**Simple register:**\n\n{simple}")
                answer_parts.append(simple)

    # ── citations / sources ───────────────────────────────────────────
    citations = result.get("citations") or []
    if citations:
        with st.expander(f"Sources ({len(citations)})", expanded=False):
            for c in citations:
                st.code(c, language=None)

    # ── verification badge ────────────────────────────────────────────
    verification = result.get("verification")
    if verification == "pass":
        st.success("✓ Verified (NLI entailment check passed)")
    elif verification == "fail":
        st.warning("Verification failed — answer may contain unsupported claims")

    # ── equivalences ──────────────────────────────────────────────────
    equivs = result.get("equivalences") or []
    if equivs:
        notes = "\n".join(f"- {e.note}" for e in equivs)
        with st.expander("Regime equivalences", expanded=False):
            st.markdown(notes)

    # ── disclaimer ────────────────────────────────────────────────────
    st.caption("*For informational purposes only — not legal advice.*")

    # store assistant response
    full_answer = "\n\n".join(answer_parts)
    st.session_state.messages.append({"role": "assistant", "content": full_answer})
