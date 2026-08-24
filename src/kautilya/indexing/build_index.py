"""Hybrid index builder: BGE-M3 dense vectors (LanceDB) + BM25s sparse.

Usage (CLI): Kautilya-venv/bin/kautilya build-index
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[3]


@dataclass(frozen=True)
class IndexConfig:
    model: str = "BAAI/bge-m3"
    persist: Path = REPO_ROOT / "data" / "processed" / "lancedb"
    batch_size: int = 32
    device: str = "auto"
    dtype: str = "float32"

    @classmethod
    def from_settings(cls, path: Path) -> "IndexConfig":
        import yaml

        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        vs = raw.get("vector_store", {})
        emb = raw.get("embeddings", {})
        return cls(
            model=emb.get("model", cls.model),
            persist=REPO_ROOT / vs.get("path", "data/processed/lancedb"),
            batch_size=int(emb.get("batch_size", cls.batch_size)),
            device=emb.get("device", cls.device),
            dtype=emb.get("dtype", cls.dtype),
        )


def resolve_device(device: str) -> str:
    if device in ("auto", None, ""):
        import torch

        return "cuda" if torch.cuda.is_available() else "cpu"
    return device


def load_chunks(chunks_dir: Path) -> list[dict]:
    chunks: list[dict] = []
    for f in sorted(chunks_dir.glob("*.jsonl")):
        for line in open(f, encoding="utf-8"):
            c = json.loads(line)
            if (c.get("text") or "").strip():
                chunks.append(c)
    return chunks


def _meta_columns(chunk: dict) -> dict:
    keep = {}
    for k in ("chunk_id", "act_short", "act", "domain", "regime", "section_no",
              "title", "chapter", "chapter_title", "lang", "court",
              "decision_date", "citation", "landmark"):
        v = chunk.get(k)
        if isinstance(v, str) and len(v) > 400:
            v = v[:400]
        keep[k] = v
    keep["effective_from"] = chunk.get("effective_from")
    keep["effective_to"] = chunk.get("effective_to")
    return keep


class DenseEmbedder:
    """BGE-M3 dense embeddings via sentence-transformers."""

    def __init__(self, model_name: str, device: str = "auto",
                 dtype: str = "float32", batch_size: int = 32):
        os.environ.setdefault("HF_HOME", str(REPO_ROOT / "hf_cache"))
        os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
        from sentence_transformers import SentenceTransformer

        self.device = resolve_device(device)
        self.batch_size = int(batch_size)
        model_kwargs = {}
        if self.device == "cuda" and dtype == "float16":
            import torch

            model_kwargs["torch_dtype"] = torch.float16
        self.model = SentenceTransformer(model_name, device=self.device,
                                         model_kwargs=model_kwargs)

    def embed(self, texts: list[str]) -> np.ndarray:
        vecs = self.model.encode(
            texts,
            batch_size=self.batch_size,
            normalize_embeddings=True,
            show_progress_bar=False,
            convert_to_numpy=True,
        )
        return np.asarray(vecs, dtype=np.float32)


def build_bm25(chunks: list[dict], persist: Path) -> None:
    import bm25s

    corpus_tokens = bm25s.tokenize(
        [c["text"] for c in chunks], stopwords=None, show_progress=False
    )
    bm25 = bm25s.BM25()
    bm25.index(corpus_tokens, show_progress=False)
    out = persist / "bm25"
    out.mkdir(parents=True, exist_ok=True)
    bm25.save(str(out), corpus=None)
    ids = [c["chunk_id"] for c in chunks]
    (out / "corpus_ids.json").write_text(json.dumps(ids) + "\n")


def build_index(
    chunks: list[dict],
    cfg: IndexConfig,
    embedder=None,
    skip_bm25: bool = False,
) -> dict:
    """Build LanceDB dense table (+BM25 files). Returns stats."""
    t0 = time.time()
    injected = embedder is not None
    if embedder is None:
        embedder = DenseEmbedder(cfg.model, device=cfg.device, dtype=cfg.dtype,
                                 batch_size=cfg.batch_size)

    vectors = []
    for i in range(0, len(chunks), cfg.batch_size):
        batch = [c["text"] for c in chunks[i : i + cfg.batch_size]]
        vectors.append(embedder.embed(batch))
    vecs = np.vstack(vectors) if vectors else np.zeros((0, 1), dtype=np.float32)

    import lancedb
    import pyarrow as pa

    rows = []
    for c, v in zip(chunks, vecs):
        row = _meta_columns(c)
        row["vector"] = v.tolist()
        rows.append(row)

    db = lancedb.connect(str(cfg.persist))
    tbl_name = "chunks"
    if tbl_name in db.table_names():
        db.drop_table(tbl_name)
    tbl = db.create_table(tbl_name, data=rows)

    if not skip_bm25:
        build_bm25(chunks, cfg.persist)

    model_name = "injected-embedder" if injected else cfg.model

    stats = {
        "chunks": len(chunks),
        "dim": int(vecs.shape[1]),
        "model": model_name,
        "device": getattr(embedder, "device", "cpu"),
        "persist": str(cfg.persist),
        "seconds": round(time.time() - t0, 1),
        "table_rows": tbl.count_rows(),
    }
    return stats


def search_bm25(query: str, k: int, persist: Path) -> list[tuple[str, float]]:
    import bm25s

    bm25 = bm25s.BM25.load(str(persist / "bm25"))  # classmethod -> new instance
    ids = json.loads((persist / "bm25" / "corpus_ids.json").read_text())
    q = bm25s.tokenize([query], stopwords=None, show_progress=False)
    results, scores = bm25.retrieve(q, k=min(k, len(ids)), show_progress=False)
    return [(ids[int(i)], float(s)) for i, s in zip(results[0], scores[0])]
