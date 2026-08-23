"""Resolve landmark SC judgments against the public S3 metadata index and
download only the matching judgment PDFs.

Builds a local full index (one metadata parquet per year) so landmark years
need not match the SCR-volume year used in object keys.

Usage:
    .venv/bin/python scripts/fetch_scj.py [--manifest data/raw/scj_landmarks.json]
        [--out data/raw/scj] [--cache /tmp/opencode/scj_meta]
"""

from __future__ import annotations

import argparse
import json
import re
import string
import sys
import urllib.request
from pathlib import Path

import pyarrow.parquet as pq

BUCKET = "https://indian-supreme-court-judgments.s3.amazonaws.com"
STOP_TOKENS = {"V", "VS", "VERSUS", "OF", "THE", "AND", "IN", "UNION", "STATE",
               "INDIA", "UOI", "ANR", "ORS", "OTHERS"}


def _norm(s: str) -> str:
    s = s.translate(str.maketrans({c: " " for c in string.punctuation})).upper()
    return re.sub(r"\s+", " ", s).strip()


def _tokens(s: str) -> set[str]:
    return {t for t in _norm(s).split() if t not in STOP_TOKENS}


def build_index(cache: Path) -> list[dict]:
    index_path = cache / "index.jsonl"
    if index_path.exists():
        entries = [json.loads(line) for line in index_path.read_text().splitlines()]
        print(f"loaded index: {len(entries)} judgments")
        return entries

    cache.mkdir(parents=True, exist_ok=True)
    entries: list[dict] = []
    year = 1950
    while True:
        dest = cache / f"meta_{year}.parquet"
        if not dest.exists():
            url = f"{BUCKET}/metadata/parquet/year={year}/metadata.parquet"
            try:
                urllib.request.urlretrieve(url, dest)
            except Exception:
                break
        rows = pq.read_table(dest).to_pydict()
        n = len(rows["path"])
        if n == 0:
            break
        for i in range(n):
            hay = _norm(" ".join(filter(None, [
                rows["title"][i] or "",
                rows["petitioner"][i] or "",
                rows["respondent"][i] or "",
                rows["description"][i] or "",
                rows["citation"][i] or "",
            ])))
            entries.append({"path": rows["path"][i], "hay": hay})
        year += 1
    index_path.write_text("".join(json.dumps(e) + "\n" for e in entries))
    print(f"built index: {len(entries)} judgments ({year - 1950} years)")
    return entries


def resolve(entries: list[dict], search: str, aliases: list[str],
            year: int, window: int = 3) -> tuple[float, str | None, bool]:
    wants = [_tokens(s) for s in ([search] + aliases)]
    best: tuple[float, int, str] | None = None
    fallback: tuple[float, int, str] | None = None
    for e in entries:
        m = re.match(r"(?:S_)?(\d{4})_", e["path"])
        if not m:
            continue
        delta = abs(int(m.group(1)) - year)
        have = set(e["hay"].split())
        score = max(len(w & have) / max(1, len(w)) for w in wants)
        if score <= 0:
            continue
        cand = (score, -delta, e["path"])
        if delta <= window and (best is None or cand > best):
            best = cand
        if fallback is None or cand > fallback:
            fallback = cand
    chosen = best or fallback
    if chosen is None:
        return 0.0, None, False
    return chosen[0], chosen[2], best is not None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", type=Path, default=Path("config/scj_landmarks.json"))
    ap.add_argument("--out", type=Path, default=Path("data/raw/scj"))
    ap.add_argument("--cache", type=Path, default=Path("/tmp/opencode/scj_meta"))
    args = ap.parse_args()

    manifest = json.loads(args.manifest.read_text())["landmarks"]
    entries = build_index(args.cache)

    resolved, misses = [], []
    for lm in manifest:
        forced = lm.get("force_key")
        if forced:
            resolved.append((lm, forced, 1.0, True))
            continue
        score, key, in_window = resolve(
            entries, lm["search"], lm.get("aliases", []), lm["year"],
            lm.get("window", 3),
        )
        threshold = 0.5 if in_window else 0.6
        if key and score >= threshold:
            resolved.append((lm, key, score, in_window))
        else:
            misses.append((lm, score))

    print(f"\nresolved {len(resolved)}/{len(manifest)}")
    if misses:
        print("UNRESOLVED (best score):")
        for lm, score in misses:
            print(f"  - [{lm['domain']}] {lm['name']} ({lm['year']}) best={score:.2f}")

    args.out.mkdir(parents=True, exist_ok=True)
    print()
    for lm, key, score, in_window in sorted(resolved, key=lambda r: (r[0]["domain"], r[0]["name"])):
        dest = args.out / f"{key}_EN.pdf"
        status = "cached" if dest.exists() else "fetch"
        flag = "" if in_window else "  !! year-mismatch"
        if not dest.exists():
            year = re.match(r"(?:S_)?(\d{4})_", key).group(1)
            url = f"{BUCKET}/data/pdf/year={year}/english/{key}_EN.pdf"
            urllib.request.urlretrieve(url, dest)
        print(f"[{score:.2f}] {status:6} {lm['domain']:18} {lm['name'][:46]:48} -> {dest.name}{flag}")

    (args.out / "resolved.json").write_text(json.dumps(
        {lm["name"]: {"key": key, "score": score} for lm, key, score, _ in resolved},
        indent=2,
    ))
    return 0


if __name__ == "__main__":
    sys.exit(main())
