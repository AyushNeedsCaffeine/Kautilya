"""HybridRetriever (ARCHITECTURE.md §4): dense + sparse -> RRF -> rerank.

Dense side honours the routed regime via LanceDB metadata prefilter; the
BM25 side has no metadata, so it over-fetches and filtering happens at
fusion time with a relax-once-on-empty fallback.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Protocol

from kautilya.indexing.build_index import DenseEmbedder, IndexConfig, search_bm25
from kautilya.log import get_logger

log = get_logger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CHUNKS_DIR = REPO_ROOT / "data" / "processed" / "chunks"

# (domain, regime) -> act_shorts searchable; missing combo -> no restriction
_ACTS_FOR: dict[tuple[str, str], set[str]] = {
    ("criminal_substantive", "old"): {"IPC"},
    ("criminal_substantive", "new"): {"BNS"},
    ("criminal_procedure", "old"): {"CRPC"},
    ("criminal_procedure", "new"): {"BNSS"},
    ("evidence", "old"): {"IEA"},
    ("evidence", "new"): {"BSA"},
    # tax: ITA1961 chunks carry regime=current too, so split by act
    ("tax", "old"): {"ITA1961"},
    ("tax", "new"): {"ITA2025"},
    ("tax", "current"): {"ITA2025"},
}
_ALWAYS_IN = {"SCJ", "COI"}          # judgments + constitution always searchable
_LABOUR_CODES = {"IRCODE", "OSHCODE", "SSCODE", "WAGECODE"}

# structured hints: "section 76 of Indian Penal Code" -> ("IPC", "76")
_ACT_ALIASES: list[tuple[tuple[str, ...], str]] = [
    (("indian penal code", "penal code"), "IPC"),
    (("bharatiya nyaya sanhita", "nyaya sanhita"), "BNS"),
    (("nagarik suraksha sanhita", "suraksha sanhita",
      "criminal procedure"), "BNSS"),
    (("bharatiya sakshya adhiniyam", "sakshya adhiniyam", "sakshya"),
     "BSA"),
    (("evidence act", "indian evidence"), "IEA"),
    (("income-tax act, 2025", "income tax act 2025", "income-tax act 2025"),
     "ITA2025"),
    (("constitution",), "COI"),
]
_SECTION_HINT_RE = re.compile(
    r"\bsections?\s+(no\.\s*)?(\d{1,3}[A-Z]{0,2})\b", re.IGNORECASE)


def section_hint(query: str) -> tuple[str | None, str | None]:
    """(act_short, section_no) when the query pins an exact provision."""
    m = _SECTION_HINT_RE.search(query)
    if not m:
        return None, None
    sec = m.group(2)
    low = query.lower()
    for aliases, act in _ACT_ALIASES:
        if any(a in low for a in aliases):
            return act, sec
    return None, sec


class Reranker(Protocol):
    def rerank(self, query: str, docs: list[str]) -> list[float]: ...


class CrossEncoderReranker:
    """bge-reranker-v2-m3 via sentence-transformers (GPU fp16 when available).

    fp16 matters on 4GB cards: fp32 weights (~2.3GB) plus the resident
    embedding model trigger CUDA system-memory fallback -> huge slowdowns.
    """

    def __init__(self, model_name: str = "BAAI/bge-reranker-v2-m3",
                 max_doc_chars: int = 1600, batch_size: int = 8):
        import torch
        from sentence_transformers import CrossEncoder

        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.max_doc_chars = max_doc_chars
        automodel_args = ({"torch_dtype": torch.float16}
                          if self.device == "cuda" else {})
        self.model = CrossEncoder(model_name, device=self.device,
                                  automodel_args=automodel_args)

    def rerank(self, query: str, docs: list[str]) -> list[float]:
        pairs = [(query, d[: self.max_doc_chars]) for d in docs]
        return [float(s) for s in self.model.predict(
            pairs, batch_size=8, show_progress_bar=False)]


def rrf_fuse(rankings: list[list[str]], k: int) -> dict[str, float]:
    """Reciprocal-rank fusion; returns chunk_id -> score (higher=better)."""
    scores: dict[str, float] = {}
    for ranking in rankings:
        for r, cid in enumerate(ranking):
            scores[cid] = scores.get(cid, 0.0) + 1.0 / (k + r + 1)
    return scores


class HybridRetriever:
    def __init__(self,
                 persist: Path,
                 embedder=None,
                 reranker: Reranker | None = None,
                 dense_k: int = 20,
                 sparse_k: int = 20,
                 rrf_k: int = 60,
                 final_k: int = 8,
                 chunks_dir: Path | None = DEFAULT_CHUNKS_DIR):
        self.persist = Path(persist)
        self.embedder = embedder          # lazy DenseEmbedder if None
        self.reranker = reranker          # None -> skip rerank stage
        self.dense_k = dense_k
        self.sparse_k = sparse_k
        self.rrf_k = rrf_k
        self.final_k = final_k
        self.chunks_dir = chunks_dir      # sidecar JSONLs supply `text`
        self._table = None
        self._bm25_ids: list[str] | None = None
        self._texts: dict[str, str] | None = None

    # ------------------------------------------------------------ plumbing
    @property
    def table(self):
        if self._table is None:
            import lancedb

            self._table = lancedb.connect(str(self.persist)).open_table("chunks")
        return self._table

    @property
    def embed(self):
        if self.embedder is None:
            cfg = IndexConfig()
            self.embedder = DenseEmbedder(cfg.model, device=cfg.device,
                                          dtype=cfg.dtype, batch_size=8)
        return self.embedder.embed

    def _bm25_corpus_ids(self) -> list[str]:
        if self._bm25_ids is None:
            self._bm25_ids = json.loads(
                (self.persist / "bm25" / "corpus_ids.json").read_text())
        return self._bm25_ids

    # -------------------------------------------------------------- stages
    @staticmethod
    def _allowed_acts(state: dict) -> set[str] | None:
        """Act allowlist from routed regimes; None = unrestricted."""
        regimes = state.get("regimes") or {}
        domains = state.get("domains") or []
        if not domains:
            return None
        allowed: set[str] = set(_ALWAYS_IN)
        restricted = False
        for dom in domains:
            reg = regimes.get(dom, "current")
            acts = _ACTS_FOR.get((dom, reg))
            if acts:
                allowed |= acts
                restricted = True
            elif dom == "labour":
                allowed |= _LABOUR_CODES      # codes are all we ingested
                restricted = True
            # constitutional/general/current -> only the always-in sets
        return allowed if restricted else None

    def _search_dense(self, query_vec, acts: set[str] | None,
                      k: int) -> list[dict]:
        q = self.table.search(query_vec)
        if acts is not None:
            lst = ", ".join(f"'{a}'" for a in sorted(acts))
            q = q.where(f"act_short IN ({lst})", prefilter=True)
        return q.limit(k).to_list()

    def _sidecar_texts(self) -> dict[str, str]:
        if self._texts is None:
            self._texts = {}
            d = Path(self.chunks_dir) if self.chunks_dir else None
            if d and d.is_dir():
                for f in sorted(d.glob("*.jsonl")):
                    for line in open(f, encoding="utf-8"):
                        c = json.loads(line)
                        self._texts[c["chunk_id"]] = c.get("text", "")
        return self._texts

    def _hydrate(self, ids: list[str]) -> dict[str, dict]:
        sidecar = self._sidecar_texts()
        if not ids:
            return {}
        lst = ", ".join(f"'{i}'" for i in ids)
        rows = (self.table.search()
                .where(f"chunk_id IN ({lst})", prefilter=True)
                .limit(len(ids)).to_list())
        out = {r["chunk_id"]: r for r in rows}
        for cid in ids:                    # text lives in the sidecar, not LanceDB
            row = out.setdefault(cid, {"chunk_id": cid})
            row.setdefault("text", sidecar.get(cid, ""))
        return out

    # ---------------------------------------------------------------- main
    def retrieve(self, state: dict) -> list[dict]:
        """LangGraph node input: reads query_raw + regimes; returns chunks."""
        query = state.get("query_raw", "").strip()
        if not query:
            return []

        vec = self.embed([query])[0]
        acts = self._allowed_acts(state)

        dense_rows = self._search_dense(vec, acts, self.dense_k)
        dense_ids = [r["chunk_id"] for r in dense_rows]

        sparse_hits = search_bm25(query, k=self.sparse_k * 3,
                                  persist=self.persist)
        sparse_ids = [cid for cid, _ in sparse_hits]

        fused = rrf_fuse([dense_ids, sparse_ids], k=self.rrf_k)
        ranked = sorted(fused.items(), key=lambda kv: kv[1], reverse=True)

        pool_ids = [cid for cid, _ in ranked[: max(self.final_k * 3, 24)]]
        if acts is not None:
            keep = [c for c in pool_ids if c.split("_", 1)[0] in acts]
            if keep:                      # regime hits only (relax on empty)
                pool_ids = keep
            else:
                log.info("retriever: regime filter empty -> relaxed")

        # structured boost: an exact (act, section) pin belongs at the front
        hint_act, hint_sec = section_hint(query)
        if hint_sec:
            def _matches(cid: str) -> bool:
                parts = cid.split("_p")[0].split("_s", 1)
                if len(parts) != 2 or parts[1] != hint_sec:
                    return False
                return hint_act is None or parts[0] == hint_act

            # scan the full fusion, not just the pool - pins outrank noise
            fused_order = [cid for cid, _ in ranked]
            pinned = [c for c in fused_order if _matches(c)][: self.final_k]
            if pinned:
                rest = [c for c in pool_ids if c not in set(pinned)]
                pool_ids = (pinned + rest)[: max(self.final_k * 3, 24)]
                log.info("retriever: section hint %s_s%s -> pinned %d",
                         hint_act or "*", hint_sec, len(pinned))

        rows = self._hydrate(pool_ids)
        docs = [(rows[cid]["text"], cid) for cid in pool_ids if cid in rows]

        if self.reranker is not None and len(docs) > 1:
            scores = self.reranker.rerank(query, [d for d, _ in docs])
            order = sorted(range(len(docs)), key=lambda i: scores[i],
                           reverse=True)[: self.final_k]
            final = [docs[i][1] for i in order]
        else:
            final = [cid for _, cid in docs[: self.final_k]]

        out = []
        for rank, cid in enumerate(final):
            r = rows.get(cid, {})
            item = {"chunk_id": cid, "text": r.get("text", ""),
                    "fused_rank": rank,
                    "fused_score": round(fused.get(cid, 0.0), 6)}
            for key in ("act_short", "domain", "regime", "section_no", "title",
                        "court", "citation", "decision_date"):
                item[key] = r.get(key)
            out.append(item)
        log.info("retriever: %d dense + %d sparse -> %d fused -> %d final",
                 len(dense_ids), len(sparse_ids), len(ranked), len(out))
        return out


def retrieve_node(state: dict, retriever: HybridRetriever | None = None) -> dict:
    """LangGraph wrapper so wiring stays `(state) -> partial`."""
    if retriever is None:
        retriever = HybridRetriever(IndexConfig().persist)
    return {"retrieved": retriever.retrieve(state)}
