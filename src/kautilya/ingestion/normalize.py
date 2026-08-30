from __future__ import annotations

import re

import polars as pl

from kautilya.ingestion import textutils
from kautilya.ingestion.sources import ActSource
from kautilya.schemas import Provision


def _section_key(row: dict) -> str | None:
    num = str(row.get("section_number") or "").strip()
    match = re.match(r"^(\d+[A-Z]?)", num)
    if not match:
        return None
    raw = match.group(1)
    if raw.isdigit():
        return str(int(raw))
    head, tail = re.match(r"^(\d+)([A-Z]?)$", raw).groups()
    return f"{int(head)}{tail}"


def _part_order(chunk_id: str) -> int:
    suffix = re.search(r"_p(\d+)", chunk_id)
    return int(suffix.group(1)) + 1 if suffix else 0


def _pick_title(candidates: list[str | None], act_name: str) -> str | None:
    counts: dict[str, int] = {}
    for cand in candidates:
        cand = (cand or "").strip()
        if not cand or cand == act_name:
            continue
        counts[cand] = counts.get(cand, 0) + 1
    if not counts:
        return None
    return max(counts.items(), key=lambda kv: kv[1])[0]


def _chapter_title_from_text(raw: str) -> str | None:
    match = re.search(r"Chapter\s+[IVXLC]+:?\s*([^|\n]+)", raw)
    if match:
        title = textutils.clean_text(match.group(1))
        return title.strip() or None
    return None


def normalize_act(df: pl.DataFrame, source: ActSource) -> list[Provision]:
    parts: dict[str, list[tuple[int, dict]]] = {}
    titles: dict[str, list[str | None]] = {}
    chapters: dict[str, tuple[str | None, str | None]] = {}

    for row in df.iter_rows(named=True):
        key = _section_key(row)
        if not key:
            continue
        order = _part_order(str(row["chunk_id"]))
        parts.setdefault(key, []).append((order, row))
        titles.setdefault(key, []).append(row.get("section_title"))
        chap = row.get("chapter")
        if chap and key not in chapters:
            chapters[key] = (
                textutils.clean_text(chap),
                _chapter_title_from_text(row.get("text") or ""),
            )

    provisions: list[Provision] = []
    for key in sorted(parts, key=lambda k: (int(re.match(r"\d+", k).group()), k)):
        ordered = [row for _, row in sorted(parts[key], key=lambda t: t[0])]
        raw_text = "\n".join(str(r.get("text") or "") for r in ordered)
        cleaned = textutils.clean_text(raw_text)
        body, illustrations = textutils.extract_illustrations(cleaned)
        body, provisos = textutils.split_provisos(body)
        chapter, chapter_title = chapters.get(key, (None, None))
        source_urls = [r["source_url"] for r in ordered if r.get("source_url")]
        provisions.append(
            Provision(
                id=f"{source.short}_s{key}",
                domain=source.domain,
                act=source.full_name,
                act_short=source.short,
                regime=source.regime,
                effective_from=source.effective_from,
                effective_to=source.effective_to,
                repeals=source.repeals,
                chapter=chapter,
                chapter_title=chapter_title,
                section_no=key,
                title=textutils.extract_section_title(raw_text, key)
                or _pick_title(titles.get(key, []), source.full_name),
                text=body,
                provisos=provisos,
                illustrations=illustrations,
                cross_refs=textutils.internal_refs(body, source.short),
                source_url=source_urls[0] if source_urls else None,
            )
        )
    return provisions
