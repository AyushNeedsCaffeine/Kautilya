"""Patch sections missing from data/processed/statutes/IPC.jsonl using the
devgan.in bare-act mirror (statute text is public-domain government work).

Only appends sections that are absent from the shard AND present in the
mirror, so historically repealed provisions stay absent.

Usage: .venv/bin/python scripts/patch_ipc_gaps.py
"""

from __future__ import annotations

import json
import re
import sys
import urllib.request
from datetime import date
from pathlib import Path

SHARD = Path("data/processed/statutes/IPC.jsonl")
BASE = "https://devgan.in/ipc/chapter_{:02d}.php"
CHAPTERS = range(1, 24)

SEC_RE = re.compile(
    r"Section\s*(\d{1,3}[A-Z]?)\s*[:\-]+\s*(.*?)\s*?\n(.*?)(?=Section\s*\d{1,3}[A-Z]?\s*[:\-]+|\Z)",
    re.S,
)
CHAPTER_TITLE_RE = re.compile(r"Chapter\s+[IVXLC]+\s*[&#8211;\u2013-]\s*(.+)", re.I)


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read().decode("utf-8", errors="replace")


def strip_tags(html: str) -> str:
    html = re.sub(r"<script.*?</script>|<style.*?</style>", "", html, flags=re.S)
    html = re.sub(r"<br\s*/?>|</p>|</div>|</li>|</h\d>", "\n", html)
    return re.sub(r"<[^>]+>", "", html)


def parse_chapter(page: str) -> tuple[str | None, dict[str, tuple[str, str]]]:
    """-> (chapter_title, {section_no: (title, body)})"""
    import html as H

    text = H.unescape(strip_tags(page))
    lines = [l.strip() for l in text.split("\n")]
    blob = "\n".join(l for l in lines if l)

    m = CHAPTER_TITLE_RE.search(blob)
    ch_title = re.sub(r"\s+", " ", m.group(1)).strip().rstrip(".") if m else None

    secs = {}
    for num, title, body in SEC_RE.findall(blob):
        title = re.sub(r"\s+", " ", title).strip()
        body = "\n".join(l for l in (x.strip() for x in body.split("\n")) if l)
        if title or body:
            secs[num] = (title, body)
    return ch_title, secs


def main() -> int:
    rows = [json.loads(l) for l in open(SHARD, encoding="utf-8")]
    template = dict(rows[0])
    have = {r["section_no"] for r in rows}

    all_secs: dict[str, tuple[str, str]] = {}
    ch_of: dict[str, str] = {}
    ch_title_of: dict[str, str] = {}
    for n in CHAPTERS:
        try:
            page = fetch(BASE.format(n))
        except Exception as e:  # noqa: BLE001
            print(f"chapter {n}: fetch failed ({e})", file=sys.stderr)
            continue
        ch_title, secs = parse_chapter(page)
        for num, tt in secs.items():
            all_secs.setdefault(num, tt)
            ch_of.setdefault(num, f"{n}")
            if ch_title:
                ch_title_of.setdefault(num, ch_title)
        print(f"chapter {n:02d}: {len(secs)} sections")

    missing = []
    seen = set()
    for num in sorted(all_secs, key=lambda s: (int(re.match(r"\d+", s).group()), s)):
        if num in have or num in seen:
            continue
        title, body = all_secs[num]
        if re.search(r"\(Repealed\)|\[Repealed", f"{title} {body}"[:120]):
            continue  # repeal stub in mirror; keep absent
        missing.append(num)
        seen.add(num)

    print(f"\nmirror total={len(all_secs)}  shard={len(have)}  patchable missing={len(missing)}")
    print("patching:", ", ".join(missing))

    new_rows = []
    for num in missing:
        title, body = all_secs[num]
        row = dict(template)
        row.update({
            "id": f"IPC_s{num}",
            "chapter": ch_of.get(num),
            "chapter_title": ch_title_of.get(num),
            "section_no": num,
            "title": title,
            "text": f"{num}. {title}\n{body}".strip(),
            "source": "devgan.in bare act mirror (patched)",
            "patched_on": date.today().isoformat(),
        })
        new_rows.append(row)

    if new_rows:
        with open(SHARD, "a", encoding="utf-8") as f:
            for r in new_rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"\nappended {len(new_rows)} rows -> {SHARD}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
