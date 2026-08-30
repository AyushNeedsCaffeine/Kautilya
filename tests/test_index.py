"""Tests for the hybrid index builder (model-free: injected fake embedder)."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from kautilya.indexing.build_index import (
    IndexConfig,
    build_index,
    load_chunks,
    search_bm25,
)


class FakeEmbedder:
    """Deterministic 32-dim hash embedding for tests."""

    model_name = "fake"

    def embed(self, texts: list[str]) -> np.ndarray:
        out = np.zeros((len(texts), 32), dtype=np.float32)
        for i, t in enumerate(texts):
            h = hashlib.sha256(t.encode()).digest()
            v = np.frombuffer(h[:128], dtype=np.uint8).astype(np.float32)
            out[i] = (v - 128.0) / 128.0
            out[i] /= np.linalg.norm(out[i]) or 1.0
        return out


@pytest.fixture()
def sample_chunks(tmp_path: Path) -> list[dict]:
    chunks = [
        {"chunk_id": "IPC_s302", "act_short": "IPC", "domain": "criminal_substantive",
         "regime": "old", "section_no": "302", "title": "Punishment for murder",
         "text": "Whoever commits murder shall be punished with death or life imprisonment."},
        {"chunk_id": "BNS_s103", "act_short": "BNS", "domain": "criminal_substantive",
         "regime": "new", "section_no": "103", "title": "Punishment for murder",
         "text": "Murder is punished under the Sanhita with death or imprisonment for life."},
        {"chunk_id": "BNSS_s173", "act_short": "BNSS", "domain": "criminal_procedure",
         "regime": "new", "section_no": "173", "title": "Information in cognizable cases",
         "text": "Every information relating to a cognizable offence shall be registered as FIR."},
        {"chunk_id": "SCJ_X_Facts", "act_short": "SCJ", "domain": "judgments",
         "regime": "judgment", "section_no": "Facts", "title": None,
         "text": "The appellant was arrested without notice under section 41A CrPC."},
    ]
    d = tmp_path / "chunks"
    d.mkdir()
    with open(d / "sample.jsonl", "w", encoding="utf-8") as f:
        f.writelines(json.dumps(c) + "\n" for c in chunks)
    return chunks


def test_load_chunks(sample_chunks, tmp_path):
    loaded = load_chunks(tmp_path / "chunks")
    assert [c["chunk_id"] for c in loaded] == ["IPC_s302", "BNS_s103",
                                               "BNSS_s173", "SCJ_X_Facts"]


def test_build_index_and_bm25_search(sample_chunks, tmp_path):
    persist = tmp_path / "lancedb"
    cfg = IndexConfig(persist=persist)
    stats = build_index(load_chunks(tmp_path / "chunks"), cfg,
                        embedder=FakeEmbedder())
    assert stats["chunks"] == 4 and stats["dim"] == 32
    assert stats["table_rows"] == 4

    import lancedb

    tbl = lancedb.connect(str(persist)).open_table("chunks")
    rows = tbl.search().limit(10).to_list()
    assert {r["chunk_id"] for r in rows} == {
        "IPC_s302", "BNS_s103", "BNSS_s173", "SCJ_X_Facts"}
    assert all("vector" in r for r in rows)
    # metadata filters work
    old_rows = tbl.search().where("regime = 'old'", prefilter=True).to_list()
    assert [r["chunk_id"] for r in old_rows] == ["IPC_s302"]

    hits = search_bm25("murder punishment", k=2, persist=persist)
    assert len(hits) <= 2
    assert any(cid in ("IPC_s302", "BNS_s103") for cid, _ in hits)
