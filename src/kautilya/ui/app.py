"""Kautilya chat UI — dark theme with startup loading phase.

Run:  Kautilya-venv/bin/streamlit run src/kautilya/ui/app.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

_src = str(Path(__file__).resolve().parents[2])
if _src not in sys.path:
    sys.path.insert(0, _src)

import streamlit as st
from kautilya.ui.styles import (
    APP_CSS, header_html, answer_card_html, citation_chips_html,
    status_badge_html, equivalence_table_html, info_panel_html,
)

st.set_page_config(
    page_title="Kautilya",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(APP_CSS, unsafe_allow_html=True)

# ── settings (load once, fast) ─────────────────────────────────────────

@st.cache_resource(show_spinner=False)
def _load_settings():
    from kautilya.config import load_settings
    return load_settings(Path("config/settings.yaml"))

settings = _load_settings()

# ── LLM (cached per provider) ──────────────────────────────────────────

_llm_cache: dict[str, object] = {}

def _get_llm(provider: str):
    if provider in _llm_cache:
        return _llm_cache[provider]
    from kautilya.llm import create_llm
    llm = create_llm(
        provider=provider,
        model=settings.llm.model if provider == "gemini" else "qwen2.5:3b",
        temperature=settings.llm.temperature,
        config_path="config/settings.yaml",
    )
    _llm_cache[provider] = llm
    return llm

# ── heavy resources (lazy, cached) ─────────────────────────────────────

@st.cache_resource(show_spinner=False)
def _get_retriever():
    from kautilya.indexing.build_index import IndexConfig
    from kautilya.indexing.search import HybridRetriever
    idx = IndexConfig.from_settings(Path("config/settings.yaml"))
    ret = settings.retrieval
    return HybridRetriever(
        persist=idx.persist, dense_k=ret.dense_k,
        sparse_k=ret.sparse_k, rrf_k=ret.rrf_k,
        final_k=ret.final_k,
    )

@st.cache_resource(show_spinner=False)
def _get_nli():
    from kautilya.graph.verifier import NLIVerifier
    return NLIVerifier(settings.verifier.nli_model)

@st.cache_resource(show_spinner=False)
def _get_translator():
    from kautilya.translate.indictrans2 import IndicTranslator
    return IndicTranslator()


# ══════════════════════════════════════════════════════════════════════
#  STARTUP PHASE — show loading progress before chat is enabled
# ══════════════════════════════════════════════════════════════════════

def _render_startup():
    """Show loading progress for each model. Returns True when all loaded."""
    if "models_loaded" not in st.session_state:
        st.session_state.models_loaded = False
    if "load_log" not in st.session_state:
        st.session_state.load_log = []

    if st.session_state.models_loaded:
        return True

    st.markdown(header_html(), unsafe_allow_html=True)

    st.markdown("""
    <div style="text-align:center; padding: 20px 0 8px 0;">
        <p style="color: #9e9e9e; font-family: Inter, sans-serif; font-size: 0.95em;">
            Loading models — first query takes a minute…
        </p>
    </div>
    """, unsafe_allow_html=True)

    progress = st.progress(0, text="Initializing...")
    log_area = st.empty()

    steps = [
        ("Retriever (bge-m3 embeddings)", lambda: _get_retriever()),
        ("NLI Verifier (mDeBERTa)", lambda: _get_nli()),
        ("Translator (IndicTrans2)", lambda: _get_translator()),
    ]

    total = len(steps)
    for i, (label, loader) in enumerate(steps):
        pct = int((i / total) * 100)
        progress.progress(pct, text=f"Loading {label}...")
        log_area.caption(f"⏳ {label}")
        t0 = time.time()
        try:
            loader()
            elapsed = round(time.time() - t0, 1)
            st.session_state.load_log.append(f"✅ {label} ({elapsed}s)")
        except Exception as e:
            st.session_state.load_log.append(f"⚠️ {label} — {e}")

        # show completed log
        log_area.caption("\n".join(st.session_state.load_log))

    progress.progress(100, text="All models loaded!")
    time.sleep(0.3)
    st.session_state.models_loaded = True
    st.rerun()


# ── sidebar ────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("### ⚖️ Kautilya")
    st.caption("Time-aware legal RAG over Indian law")
    st.divider()

    llm_provider = st.selectbox(
        "LLM Backend", ["ollama", "gemini"], index=0,
        help="Ollama runs locally (default). Gemini requires API key.",
    )

    st.divider()
    legal_only = st.toggle("Legal register only", value=False)
    simple_only = st.toggle("Simple register only", value=True)

    LANGUAGES = {
        "English": "en", "Hindi": "hi", "Marathi": "mr",
        "Bengali": "bn", "Tamil": "ta", "Telugu": "te",
        "Gujarati": "gu", "Kannada": "kn",
    }
    lang_name = st.selectbox("Answer language", list(LANGUAGES.keys()), index=0)
    final_lang = LANGUAGES[lang_name]

    incident_date = st.date_input("Incident date (optional)", value=None)
    date_str = incident_date.isoformat() if incident_date else None

    no_verify = st.toggle("Skip NLI verification", value=False)

    st.divider()
    st.caption("LangGraph + bge-m3 + mDeBERTa + IndicTrans2")


# ── run startup phase ──────────────────────────────────────────────────

if not _render_startup():
    st.stop()

# ── header (after models loaded) ───────────────────────────────────────

st.markdown(header_html(), unsafe_allow_html=True)

# ── session state ──────────────────────────────────────────────────────

if "messages" not in st.session_state:
    st.session_state.messages = []

# ── render history ─────────────────────────────────────────────────────

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if msg.get("html"):
            st.markdown(msg["html"], unsafe_allow_html=True)
        else:
            st.markdown(msg["content"])

# ── chat input ─────────────────────────────────────────────────────────

query = st.chat_input("Ask a legal question about Indian law…")

if not query:
    st.stop()

# display user message
st.session_state.messages.append({"role": "user", "content": query})
with st.chat_message("user"):
    st.markdown(query)

# ── run pipeline ───────────────────────────────────────────────────────

with st.chat_message("assistant"):
    loading_html = """
    <div class="loading-container">
        <div class="loading-spinner"></div>
        <div class="loading-text">Thinking…</div>
    </div>
    """
    loading_slot = st.empty()
    loading_slot.markdown(loading_html, unsafe_allow_html=True)
    info_slot = st.empty()

    t0 = time.time()
    try:
        llm = _get_llm(provider=llm_provider)
        retriever = _get_retriever()
        nli = None if no_verify else _get_nli()
        translator = _get_translator()

        from kautilya.graph.pipeline import run_query
        result = run_query(
            query, llm=llm, retriever=retriever, nli=nli,
            translator=translator,
            incident_date=date_str,
            final_lang=final_lang,
        )
        latency = round(time.time() - t0, 1)
        result["_latency"] = latency
    except Exception as exc:
        loading_slot.empty()
        st.error(f"Pipeline error: {exc}")
        st.session_state.messages.append(
            {"role": "assistant", "content": f"Error: {exc}"}
        )
        st.stop()

    loading_slot.empty()

    # ── render result ──────────────────────────────────────────────────

    route = result.get("route")

    if route == "ask_date":
        info_slot.markdown(info_panel_html(result), unsafe_allow_html=True)
        st.info("This looks like a past-incident question. "
                "Please set an incident date in the sidebar and try again.")
        st.session_state.messages.append(
            {"role": "assistant",
             "content": "Please set an incident date and re-ask."}
        )
        st.stop()

    if route == "refuse":
        info_slot.markdown(info_panel_html(result), unsafe_allow_html=True)
        note = (result.get("answer_simple")
                or "Could not verify an answer from the retrieved sources.")
        st.warning(note)
        notes = result.get("verification_notes") or []
        if notes:
            with st.expander("Verifier details"):
                for n in notes[:5]:
                    st.caption(n[:200])
        st.session_state.messages.append(
            {"role": "assistant", "content": note}
        )
        st.stop()

    # ── success ────────────────────────────────────────────────────────

    info_slot.markdown(info_panel_html(result), unsafe_allow_html=True)

    answer_parts: list[str] = []

    if not simple_only:
        legal = result.get("answer_legal", "")
        if legal:
            st.markdown(
                answer_card_html("legal", "Legal Register", legal),
                unsafe_allow_html=True,
            )
            answer_parts.append(legal)

    if not legal_only:
        translated = result.get("answer_translated")
        if translated and final_lang != "en":
            st.markdown(
                answer_card_html("simple", f"Simple Register ({lang_name})",
                                 translated),
                unsafe_allow_html=True,
            )
            answer_parts.append(translated)
        else:
            simple = result.get("answer_simple", "")
            if simple:
                st.markdown(
                    answer_card_html("simple", "Simple Register", simple),
                    unsafe_allow_html=True,
                )
                answer_parts.append(simple)

    # citations
    citations = result.get("citations") or []
    if citations:
        st.markdown(citation_chips_html(citations), unsafe_allow_html=True)

    # verification
    verification = result.get("verification")
    badge = status_badge_html(verification)
    if badge:
        st.markdown(badge, unsafe_allow_html=True)

    # equivalences
    equivs = result.get("equivalences") or []
    if equivs:
        with st.expander("Regime equivalences (old ↔ new)"):
            st.markdown(
                equivalence_table_html(equivs), unsafe_allow_html=True
            )

    # latency + disclaimer
    st.caption(f"⏱ {latency}s")
    st.markdown(
        '<div class="disclaimer">'
        "For informational purposes only — not legal advice."
        "</div>",
        unsafe_allow_html=True,
    )

    full_answer = "\n\n".join(answer_parts)
    st.session_state.messages.append({
        "role": "assistant",
        "content": full_answer,
    })
