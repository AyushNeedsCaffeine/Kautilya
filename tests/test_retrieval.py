"""Tests for the HybridRetriever (fake embedder/reranker, tmp LanceDB+BM25)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from kautilya.indexing.build_index import IndexConfig, build_index
from kautilya.indexing.search import (
    HybridRetriever,
    retrieve_node,
    rrf_fuse,
)

CHUNKS = [
    {"chunk_id": "IPC_s302", "act_short": "IPC", "domain": "criminal_substantive",
     "regime": "old", "section_no": "302", "title": "Punishment for murder",
     "court": None, "citation": None, "decision_date": None,
     "text": "murder punishment death penalty life imprisonment whoever commits"},
    {"chunk_id": "BNS_s103", "act_short": "BNS", "domain": "criminal_substantive",
     "regime": "new", "section_no": "103", "title": "Punishment for murder",
     "court": None, "citation": None, "decision_date": None,
     "text": "sanhita murder provision punishment imprisonment for life"},
    {"chunk_id": "CRPC_s437", "act_short": "CRPC", "domain": "criminal_procedure",
     "regime": "old", "section_no": "437", "title": "Bail",
     "court": None, "citation": None, "decision_date": None,
     "text": "bail non bailable offence magistrate may grant bail"},
    {"chunk_id": "SCJ_X_Facts", "act_short": "SCJ", "domain": "judgments",
     "regime": "judgment", "section_no": "Facts", "title": None,
     "court": "Supreme Court of India", "citation": "2013 SCR 713",
     "decision_date": "2013-04-15",
     "text": "murder appeal facts accused bail rejected supreme court judgment"},
    {"chunk_id": "ITA2025_s5", "act_short": "ITA2025", "domain": "tax",
     "regime": "current", "section_no": "5", "title": "Scope of total income",
     "court": None, "citation": None, "decision_date": None,
     "text": "total income tax scope previous year accrual"},
]

_VOCAB = ["murder", "punishment", "bail", "tax", "income", "judgment"]


class VocabEmbedder:
    """One-hot bag-of-words over a fixed vocab -> deterministic semantics."""

    def embed(self, texts):
        out = np.zeros((len(texts), len(_VOCAB) + 1), dtype=np.float32)
        for i, t in enumerate(texts):
            low = t.lower()
            for w in low.split():
                if w in _VOCAB:
                    out[i][_VOCAB.index(w)] += 1.0
                elif w.rstrip("s") in _VOCAB:
                    out[i][_VOCAB.index(w.rstrip("s"))] += 0.5
            n = np.linalg.norm(out[i])
            if n:
                out[i] /= n
        return out


class PreferShortReranker:
    def rerank(self, query, docs):
        return [-float(len(d)) for d in docs]


@pytest.fixture(scope="module")
def index(tmp_path_factory):
    root = tmp_path_factory.mktemp("lance")
    persist = root / "db"
    chunks_dir = root / "chunks"
    chunks_dir.mkdir(parents=True)
    with open(chunks_dir / "test.jsonl", "w", encoding="utf-8") as f:
        f.writelines(json.dumps(c) + "\n" for c in CHUNKS)
    cfg = IndexConfig(persist=persist)
    build_index(CHUNKS, cfg, embedder=VocabEmbedder())
    return persist, chunks_dir


def _retriever(index, **kw):
    persist, chunks_dir = index
    return HybridRetriever(persist=persist, chunks_dir=chunks_dir, **kw)


def _state(query, domains=("criminal_substantive",), regimes=None, date=None):
    regs = regimes or {d: ("old" if date and date < "2024-07-01" else "new")
                       for d in domains}
    return {"query_raw": query, "domains": list(domains), "regimes": regs,
            "incident_date": date}


# --------------------------------------------------------------- fusion
def test_rrf_fusion_prefers_multi_list_hits():
    scores = rrf_fuse([["a", "b", "c"], ["b", "d"]], k=60)
    assert scores["b"] > scores["a"] > scores["c"]
    assert "d" in scores


# ------------------------------------------------------------ retrieval
def test_old_regime_restricts_to_ipc(index):
    r = _retriever(index, embedder=VocabEmbedder(), final_k=3)
    out = r.retrieve(_state("murder punishment", date="2024-03-01"))
    ids = [c["chunk_id"] for c in out]
    assert ids[0] == "IPC_s302"
    assert "BNS_s103" not in ids          # filtered by regime allowlist
    assert any(c.startswith("SCJ_") for c in ids)   # judgments stay searchable


def test_new_regime_switches_acts(index):
    r = _retriever(index, embedder=VocabEmbedder(), final_k=2)
    out = r.retrieve(_state("murder punishment sanhita", date="2024-12-01"))
    ids = [c["chunk_id"] for c in out]
    assert ids[0] == "BNS_s103"
    assert "IPC_s302" not in ids


def test_relax_when_filter_empties_pool(index):
    # old-regime route but only the BNS chunk lexically matches
    r = _retriever(index, embedder=VocabEmbedder(),
                   dense_k=5, sparse_k=5, final_k=2)
    out = r.retrieve(_state("sanhita murder provision",
                            domains=("criminal_substantive",),
                            regimes={"criminal_substantive": "old"}))
    assert out, "relax-on-empty must still return something"


def test_reranker_changes_order(index):
    no_rr = _retriever(index, embedder=VocabEmbedder(),
                       reranker=None, final_k=3)
    short_rr = _retriever(index, embedder=VocabEmbedder(),
                          reranker=PreferShortReranker(), final_k=3)
    q = _state("murder punishment", date="2024-03-01")
    base = [c["chunk_id"] for c in no_rr.retrieve(q)]
    pref = [c["chunk_id"] for c in short_rr.retrieve(q)]
    assert base[0] == "IPC_s302"
    assert pref != base                   # deterministic reorder applied
    assert set(pref) == set(base)         # same pool, reranked order
    assert len(pref) == 2                 # only regime-eligible docs survive


def test_retrieved_items_carry_metadata(index):
    r = _retriever(index, embedder=VocabEmbedder(), final_k=1)
    out = r.retrieve(_state("murder punishment", date="2024-03-01"))
    item = out[0]
    for key in ("chunk_id", "text", "act_short", "regime", "fused_rank"):
        assert key in item
    assert item["act_short"] == "IPC"


def test_retrieve_node_wrapper(index):
    partial = retrieve_node(_state("bail offence", ("criminal_procedure",),
                                   regimes={"criminal_procedure": "old"}),
                            retriever=_retriever(
                                index, embedder=VocabEmbedder(),
                                dense_k=4, sparse_k=4, final_k=2))
    assert partial["retrieved"][0]["chunk_id"] == "CRPC_s437"


def test_allowed_acts_mapping():
    f = HybridRetriever._allowed_acts
    assert f({"domains": ["labour"], "regimes": {"labour": "current"}}) == \
        {"SCJ", "COI"} | {"IRCODE", "OSHCODE", "SSCODE", "WAGECODE"}
    assert f({"domains": ["tax"], "regimes": {"tax": "old"}}) == \
        {"SCJ", "COI", "ITA1961"}
    assert f({"domains": ["constitutional"], "regimes":
              {"constitutional": "current"}}) is None
    assert f({}) is None
