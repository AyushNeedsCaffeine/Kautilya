"""Patch sections missing from the new-criminal-law shards (BNS/BNSS/BSA)
using the official Gazette PDFs downloaded from bprd.nic.in / mha.gov.in.

Usage: .venv/bin/python scripts/patch_new_act_gaps.py
"""

from __future__ import annotations

import json
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from kautilya.ingestion.pdf_extract import split_numbered_provisions

STATUTES = Path("data/processed/statutes")

ACTS = {
    "BNS": {
        "pdf": Path("/tmp/opencode/bns_gaz.pdf"),
        "start_re": re.compile(r"BHARATIYA\s+NYAYA\s+SANHITA", re.IGNORECASE),
    },
    "BNSS": {
        "pdf": Path("/tmp/opencode/bnss_gaz.pdf"),
        "start_re": re.compile(r"BHARATIYA\s+NAGARIK\s+SURAKSHA\s+SANHITA", re.IGNORECASE),
    },
    "BSA": {
        "pdf": Path("/tmp/opencode/bsa_gaz.pdf"),
        "start_re": re.compile(r"BHARATIYA\s+SAKSHYA\s+ADHINIYAM", re.IGNORECASE),
    },
}


def english_text(cfg: dict) -> str:
    import pymupdf

    doc = pymupdf.open(cfg["pdf"])
    start = 0
    for i, page in enumerate(doc):
        if cfg["start_re"].search(page.get_text()):
            start = i
            break
    pages = [p.get_text() for p in doc[start:]]
    return "\n".join(pages)


def main() -> int:
    overall_ok = True
    for short, cfg in ACTS.items():
        shard_path = STATUTES / f"{short}.jsonl"
        rows = [json.loads(l) for l in open(shard_path, encoding="utf-8")]
        template = dict(rows[0])
        have = {r["section_no"] for r in rows}

        text = english_text(cfg)
        provisions = dict(
            (num, (title, body)) for num, title, body in split_numbered_provisions(text)
        )

        missing = []
        for num in provisions:
            if num not in have and re.match(r"^\d{1,3}[A-Z]?$", num):
                title, body = provisions[num]
                if len(body) < 30 or re.search(r"\(Repealed\)", body[:80]):
                    continue
                missing.append(num)

        # numeric order for readable report
        missing.sort(key=lambda s: (int(re.match(r"\d+", s).group()), s))
        print(f"{short}: shard={len(rows)}  patchable={len(missing)} -> {missing}")

        new_rows = []
        for num in missing:
            title, body = provisions[num]
            row = dict(template)
            row.update({
                "id": f"{short}_s{num}",
                "chapter": None,
                "chapter_title": None,
                "section_no": num,
                "title": title,
                "text": f"{num}. {title}\n{body}".strip() if title else f"{num}. {body}",
                "source": "official gazette PDF (patched)",
                "patched_on": date.today().isoformat(),
            })
            new_rows.append(row)

        still_missing = [n for n in missing if False]
        if new_rows:
            with open(shard_path, "a", encoding="utf-8") as f:
                f.writelines(json.dumps(r, ensure_ascii=False) + "\n" for r in new_rows)

        # any referenced-but-still-absent numbers?
        left = [n for n in missing if n not in {r['section_no'] for r in new_rows}] + still_missing
        if left:
            overall_ok = False
            print(f"  !! still absent after patch: {left}")

    return 0 if overall_ok else 1


if __name__ == "__main__":
    sys.exit(main())
