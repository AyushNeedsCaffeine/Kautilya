"""Chunk the 56 landmark SC judgments (data/raw/scj/*.pdf) into
data/processed/chunks/SCJ.jsonl using metadata from the cached S3 parquets.

Usage: Kautilya-venv/bin/python scripts/build_scj_chunks.py \
         [--raw data/raw/scj] [--meta-cache /tmp/opencode/scj_meta]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from kautilya.chunking.legal_chunker import ChunkConfig, chunk_judgment

COURT = "Supreme Court of India"
NOISE_PATTERNS = [
    re.compile(r"^\s*Page\s+\d+\s*$", re.IGNORECASE),
    re.compile(r"^\s*\d{1,4}\s*$"),
    re.compile(r"^\s*\[\s*\d{4}\s*(SUPREME COURT|SCC|SCR)", re.IGNORECASE),
]


def load_meta_for_keys(meta_cache: Path, keys: dict[str, str]) -> dict[str, dict]:
    """keys: {key: pdf_name} -> {key: metadata_row}"""
    import pyarrow.parquet as pq

    years = {k.split("_")[1] if k.startswith("S_") else k.split("_")[0] for k in keys}
    rows: list[dict] = []
    for y in sorted(years):
        p = meta_cache / f"meta_{y}.parquet"
        if not p.exists():
            continue
        t = pq.read_table(p)
        cols = {c.lower(): c for c in t.column_names}
        keep = [cols[c] for c in
                ("title", "petitioner", "respondent", "citation",
                 "decision_date", "judge", "case_id", "path") if c in cols]
        sub = t.select(keep).to_pylist()
        for r in sub:
            rows.append({k.lower(): v for k, v in r.items()})

    out: dict[str, dict] = {}
    for key in keys:
        for r in rows:
            path = str(r.get("path", ""))
            if key in path or key.replace("S_", "") in path:
                out[key] = r
                break
    return out


def extract_judgment_text(pdf: Path) -> str:
    """Page-aware extraction: strip margin junk and running heads/footers."""
    import pymupdf

    doc = pymupdf.open(pdf)
    out_pages: list[str] = []
    for page in doc:
        lines = [l.rstrip() for l in page.get_text().split("\n")]
        # margin artefacts: bullets, lone letters, page-number fragments
        lines = [l for l in lines if len(l.strip()) > 3]
        # running head: up to 4 leading short lines
        lead = 0
        while lead < min(4, len(lines)) and len(lines[lead].strip()) < 80:
            lead += 1
        lines = lines[lead:]
        # footer: up to 2 trailing short lines
        tail = 0
        while tail < min(2, len(lines)) and len(lines[-1 - tail].strip()) < 80:
            tail += 1
        if tail:
            lines = lines[:-tail]
        if lines:
            out_pages.append("\n".join(lines))
    return "\n".join(out_pages)


def clean_text(raw: str, corpus_heads: set[str] | None = None) -> tuple[str, int]:
    lines = [l for l in raw.split("\n")
             if not any(p.match(l) for p in NOISE_PATTERNS)]
    # drop running heads/footers: short lines repeating >= 3x within one case
    from collections import Counter

    freq = Counter(l.strip() for l in lines if l.strip() and len(l.strip()) < 70)
    heads = {l for l, n in freq.items() if n >= 3}
    if corpus_heads:
        heads |= corpus_heads
    kept = [l for l in lines if l.strip() not in heads]
    return "\n".join(kept), len(lines) - len(kept)


def detect_corpus_heads(pdf_texts: dict[str, str]) -> set[str]:
    """Lines that repeat >= 25x across the whole landmark corpus are running heads."""
    from collections import Counter

    freq: Counter = Counter()
    for text in pdf_texts.values():
        freq.update(l.strip() for l in text.split("\n")
                    if l.strip() and len(l.strip()) < 70)
    return {l for l, n in freq.items() if n >= 25}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", type=Path, default=Path("data/raw/scj"))
    ap.add_argument("--out", type=Path, default=Path("data/processed/chunks/SCJ.jsonl"))
    ap.add_argument("--meta-cache", type=Path, default=Path("/tmp/opencode/scj_meta"))
    ap.add_argument("--settings", type=Path, default=Path("config/settings.yaml"))
    args = ap.parse_args()

    resolved = json.loads((args.raw / "resolved.json").read_text(encoding="utf-8"))
    keys = {info["key"]: name for name, info in resolved.items()}
    meta = load_meta_for_keys(args.meta_cache, keys)
    print(f"metadata matched for {len(meta)}/{len(keys)} judgments")

    cfg = ChunkConfig.from_settings(args.settings)

    # pass 1: extract + corpus-level running-head detection
    texts: dict[str, str] = {}
    for name, info in sorted(resolved.items()):
        key = info["key"]
        pdf = args.raw / f"{key}_EN.pdf"
        if not pdf.exists():
            continue
        cleaned, _ = clean_text(extract_judgment_text(pdf))
        if len(cleaned) >= 200:
            texts[name] = cleaned
    corpus_heads = detect_corpus_heads(texts)
    print(f"corpus running-heads detected: {len(corpus_heads)}")

    n_cases = n_chunks = 0
    missing_meta = []
    with open(args.out, "w", encoding="utf-8") as out:
        for name, text in texts.items():
            key = resolved[name]["key"]
            m = meta.get(key, {})
            decision_date = str(m.get("decision_date") or "")
            mm = re.search(r"(\d{4})-(\d{2})-(\d{2})", decision_date)
            meta_out = {
                "case_id": f"SCJ_{key}",
                "court": COURT,
                "decision_date": mm.group(0) if mm else None,
                "citation": (m.get("citation") or "").strip() or None,
                "petitioner": (m.get("petitioner") or "").strip() or name.split(" v ")[0],
                "respondent": (m.get("respondent") or "").strip()
                              or (name.split(" v ")[:2] + ["State"])[-1],
                "title": (m.get("title") or name).strip(),
                "bench": (m.get("judge") or "").strip() or None,
            }
            chunks = chunk_judgment(text, meta_out, cfg)
            for c in chunks:
                c["landmark"] = name
                out.write(json.dumps(c, ensure_ascii=False,
                                     separators=(",", ":")) + "\n")
            n_cases += 1
            n_chunks += len(chunks)
            if key not in meta:
                missing_meta.append(name)

    print(f"{n_cases} judgments -> {n_chunks} chunks -> {args.out}")
    if missing_meta:
        print(f"(no parquet metadata for {len(missing_meta)}: "
              f"{missing_meta[:5]}{'...' if len(missing_meta) > 5 else ''})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
