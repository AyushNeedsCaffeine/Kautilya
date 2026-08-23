"""Build temporal mapping tables (old act <-> new act section correspondences)
from the official NCRB "Corresponding Section Table" pages (cytrain.ncrb.gov.in),
which mirror the MHA/state-police correlation tables for the 2023 criminal laws.

Outputs data/mappings/{ipc_to_bns,crpc_to_bnss,iea_to_bsa}.json with schema:

    {"meta": {...},
     "pairs": [{"old": [...], "new": "...", "partial": bool}],
     "unmapped_old": [...], "unmapped_new": [...]}

Usage: .venv/bin/python scripts/build_mappings.py
"""

from __future__ import annotations

import html as htmllib
import json
import re
import sys
import urllib.request
from datetime import date
from pathlib import Path

OUT_DIR = Path("data/mappings")
STATUTES = Path("data/processed/statutes")

SOURCES = {
    "ipc_to_bns": "https://cytrain.ncrb.gov.in/staticpage/web_pages/SectionTableBNS.html",
    "crpc_to_bnss": "https://cytrain.ncrb.gov.in/staticpage/web_pages/SectionTableBNSS.html",
    "iea_to_bsa": "https://cytrain.ncrb.gov.in/staticpage/web_pages/SectionTableBSA.html",
}

ENTRY_RE = re.compile(r"^(\d{1,3}[A-Z]?)\s*(?:\(([^)]{1,8})\))?\s*[.:\u2013\u2014-]?\s*(.*)$")
NEW_MARKER_RE = re.compile(r"^new\s+(section|sub-?section|addition|clause|entry)", re.I)
GONE_MARKER_RE = re.compile(r"^(deleted|omitted|repealed)\b", re.I)
CHAPTER_RE = re.compile(r"^(chapter\b|part\b|schedule\b|the first|appendix)", re.I)


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read().decode("utf-8", errors="replace")


def table_rows(html: str) -> tuple[list[list[list[str]]], int]:
    """Return (rows_of_cells_of_paragraph_texts, new_col_index)."""
    head = html[:html.find("<tbody")]
    headers = [re.sub(r"<[^>]+>", "", h) for h in re.findall(r"<th[^>]*>(.*?)</th>", head, re.S)]
    headers = [htmllib.unescape(re.sub(r"\s+", " ", h)).strip().lower() for h in headers]
    new_idx = 0
    for i, h in enumerate(headers):
        if re.search(r"sanhita|sakshya|nyaya", h):
            new_idx = i
            break

    rows: list[list[list[str]]] = []
    body = html[html.find("<tbody"):]
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", body, re.S):
        tds = re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)
        if len(tds) < 2:
            continue
        row = []
        for td in tds:
            ps = re.findall(r"<p[^>]*>(.*?)</p>|<br\s*/?>", td, re.S)
            chunks = ps or [td]
            texts = []
            for c in chunks:
                t = htmllib.unescape(re.sub(r"<[^>]+>", " ", c))
                t = re.sub(r"\s+", " ", t).strip()
                if t and t != "&nbsp;":
                    texts.append(t)
            row.append(texts)
        rows.append(row)
    return rows, new_idx


def parse_entry(text: str):
    """-> ('sec', base, sub, rest) | ('marker', kind) | ('noise',)"""
    m = NEW_MARKER_RE.match(text)
    if m:
        return ("marker", "new")
    if GONE_MARKER_RE.match(text):
        return ("marker", "gone")
    m = ENTRY_RE.match(text)
    if m:
        return ("sec", m.group(1), m.group(2), m.group(3))
    return ("noise",)


def extract_edges(rows: list[list[list[str]]], new_idx: int) -> tuple[list[tuple[str, str, bool]], set[str]]:
    """Walk rows; emit (new_section, old_section, partial) edges + directly-deleted old secs."""
    old_idx = 1 - new_idx if new_idx in (0, 1) else 0
    edges: list[tuple[str, str, bool]] = []
    gone: set[str] = set()
    cur_new: str | None = None
    pending_gone = False

    for row in rows:
        left, right = row[new_idx], row[old_idx]
        pending_gone = False

        for text in left:
            kind = parse_entry(text)
            if kind[0] == "sec":
                base, sub = kind[1], kind[2]
                if CHAPTER_RE.match(text) and not sub:
                    continue
                cur_new = base

        for j, text in enumerate(right):
            kind = parse_entry(text)
            if kind == ("marker", "gone"):
                pending_gone = True
                continue
            if kind[0] != "sec":
                continue
            base, sub = kind[1], kind[2]
            if CHAPTER_RE.match(text) and not sub:
                continue
            if pending_gone:
                gone.add(base)
                pending_gone = False
                continue
            partial = bool(sub) or "(" in text.split(base, 1)[1][:12]
            if cur_new is not None:
                edges.append((cur_new, base, partial))

    return edges, gone


def load_shard(short: str) -> dict[str, dict]:
    out = {}
    for line in open(STATUTES / f"{short}.jsonl", encoding="utf-8"):
        p = json.loads(line)
        out[p["section_no"]] = p
    return out


def _sec_key(s: str) -> tuple[int, str]:
    m = re.match(r"(\d+)([A-Z]?)", s)
    return (int(m.group(1)), m.group(2))


def build(name: str, old_short: str, new_short: str, cutoff: str,
          url: str) -> dict:
    html = fetch(url)
    rows, new_idx = table_rows(html)
    edges, gone = extract_edges(rows, new_idx)

    old_corpus = load_shard(old_short)
    new_corpus = load_shard(new_short)

    by_new: dict[str, dict] = {}
    for new_sec, old_sec, partial in edges:
        slot = by_new.setdefault(new_sec, {"old": set(), "partial": False})
        slot["old"].add(old_sec)
        slot["partial"] = slot["partial"] or partial

    pairs, mapped_old, mapped_new = [], set(), set()
    for new_sec, slot in sorted(by_new.items(), key=lambda kv: _sec_key(kv[0])):
        valid = sorted((o for o in slot["old"] if o in old_corpus), key=_sec_key)
        if not valid:
            continue
        pairs.append({"old": valid, "new": new_sec, "partial": slot["partial"]})
        mapped_old.update(valid)
        mapped_new.add(new_sec)

    known_old = {s for s in old_corpus if re.match(r"^\d{1,3}[A-Z]?$", s)}
    known_new = {s for s in new_corpus if re.match(r"^\d{1,3}[A-Z]?$", s)}

    doc = {
        "meta": {
            "old_act": old_short,
            "new_act": new_short,
            "cutoff": cutoff,
            "source": url,
            "source_note": "NCRB corresponding-section table (mirrors MHA/state-police correlation charts)",
            "built_on": date.today().isoformat(),
            "counts": {
                "pairs": len(pairs),
                "old_mapped": len(mapped_old),
                "old_total": len(known_old),
                "new_mapped": len(mapped_new),
                "new_total": len(known_new),
            },
        },
        "pairs": pairs,
        "unmapped_old": sorted((known_old - mapped_old) | (gone & known_old), key=_sec_key),
        "unmapped_new": sorted(known_new - mapped_new, key=_sec_key),
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / f"{name}.json"
    out_path.write_text(json.dumps(doc, indent=2) + "\n")
    c = doc["meta"]["counts"]
    print(f"{name:14} pairs={c['pairs']:3}  old {c['old_mapped']:3}/{c['old_total']}"
          f" ({c['old_mapped']/max(1,c['old_total']):.0%})  "
          f"new {c['new_mapped']:3}/{c['new_total']} ({c['new_mapped']/max(1,c['new_total']):.0%})"
          f" -> {out_path}")
    return doc


ANCHORS = {
    "ipc_to_bns": [("302", "103"), ("375", "63"), ("498A", "85"), ("420", "318")],
    "crpc_to_bnss": [("154", "173"), ("438", "482"), ("125", "144"), ("167", "187")],
    "iea_to_bsa": [("65B", "63"), ("45", "39"), ("32", "26")],
}


def main() -> int:
    docs = {}
    for name, url in SOURCES.items():
        old_short, new_short = {
            "ipc_to_bns": ("IPC", "BNS"),
            "crpc_to_bnss": ("CRPC", "BNSS"),
            "iea_to_bsa": ("IEA", "BSA"),
        }[name]
        docs[name] = build(name, old_short, new_short, "2024-07-01", url)

    failures = []
    for name, checks in ANCHORS.items():
        idx_new: dict[str, set[str]] = {}
        for pair in docs[name]["pairs"]:
            for o in pair["old"]:
                idx_new.setdefault(o, set()).add(pair["new"])
        for old, want in checks:
            got = idx_new.get(old, set())
            ok = want in got
            print(f"anchor {name}: {old}->{want}: {'ok' if ok else f'MISMATCH (got {sorted(got) or None})'}")
            if not ok:
                failures.append((name, old, sorted(got)))

    if failures:
        print(f"\nANCHOR FAILURES: {failures}", file=sys.stderr)
        return 1
    print("\nall anchors pass")
    return 0


if __name__ == "__main__":
    sys.exit(main())
