import sys
import time
from pathlib import Path

sys.path.insert(0, "src")
from kautilya.indexing.build_index import IndexConfig
from kautilya.indexing.search import CrossEncoderReranker, HybridRetriever

cfg = IndexConfig.from_settings(Path("config/settings.yaml"))
t0 = time.time()
r = HybridRetriever(persist=cfg.persist, reranker=CrossEncoderReranker(), final_k=5)
print(f"init {time.time() - t0:.0f}s", flush=True)

QUERIES = [
    {"query_raw": "punishment for murder under section 302",
     "domains": ["criminal_substantive"],
     "regimes": {"criminal_substantive": "old"}},
    {"query_raw": "cheating committed in March 2024 what section applies",
     "domains": ["criminal_substantive"],
     "regimes": {"criminal_substantive": "old"}},
    {"query_raw": "admissibility of electronic evidence certificate 65B",
     "domains": ["evidence"],
     "regimes": {"evidence": "old"}},
]

for q in QUERIES:
    t1 = time.time()
    out = r.retrieve(q)
    dt = time.time() - t1
    print(f"\nQ: {q['query_raw']} ({dt:.2f}s)")
    for c in out[:5]:
        label = c.get("title") or c.get("citation") or ""
        print(f"   {c['chunk_id']:<30} {label[:55]}")

print("SMOKE OK", flush=True)
