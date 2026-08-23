"""Section-aware legal chunker (ARCHITECTURE.md §3).

Rules:
- One chunk = one section/article; provisos/illustrations/clauses stay attached.
- Every chunk carries a context header
  `[Act | Chapter | Section no: Title | regime | effective window]`.
- Max chunk ~ max_tokens (cheap estimator); oversized sections split ONLY at
  clause boundaries, and a part never starts with a proviso line.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path

import yaml

CLAUSE_RE = re.compile(r"^\((?:[a-z]{1,3}|\d{1,2}|[ivxlcdm]{1,6})[\).]\s")
STAGE_RE = re.compile(
    r"^(proviso|provided\s+that|explanation|illustrations?|comments?|annotations?)\b",
    re.I,
)
PART_SUFFIX = "_p{0}"


@dataclass(frozen=True)
class ChunkConfig:
    max_tokens: int = 1200
    chars_per_token: int = 4
    keep_proviso_attached: bool = True

    @classmethod
    def from_settings(cls, path: Path) -> "ChunkConfig":
        cfg = yaml.safe_load(path.read_text(encoding="utf-8")).get("chunking", {})
        return cls(
            max_tokens=int(cfg.get("max_tokens", 1200)),
            chars_per_token=int(cfg.get("chars_per_token", 4)),
            keep_proviso_attached=bool(cfg.get("keep_proviso_attached", True)),
        )


def _header(row: dict) -> str:
    ch = row.get("chapter") or "-"
    ch_title = row.get("chapter_title") or "-"
    title = row.get("title") or ""
    ef = row.get("effective_from") or "?"
    et = row.get("effective_to") or "present"
    return (
        f"[{row.get('act', row.get('act_short', '?'))}"
        f" | Chapter {ch}: {ch_title}"
        f" | Section {row['section_no']}: {title}"
        f" | regime={row.get('regime', '?')}"
        f" | effective {ef} to {et}]"
    )


def _split_blocks(body: str) -> list[str]:
    """Break a section body into clause/stage blocks."""
    blocks: list[str] = []
    for line in body.split("\n"):
        if CLAUSE_RE.match(line) or STAGE_RE.match(line) or not blocks:
            blocks.append(line)
        else:
            blocks[-1] += "\n" + line
    return blocks


def _split_paragraphs(block: str) -> list[str]:
    return [p.strip() for p in block.split("\n\n") if p.strip()]


_SENT_SPLIT_RE = re.compile(r"(?<=[.;:])\s+(?=[A-Z(\u2018\u201c])")


def _hard_split(block: str, limit_chars: int) -> list[str]:
    """Last-resort split for an un-splittable block: by lines, then sentences."""
    out: list[str] = []
    cur = ""

    def push():
        nonlocal cur
        if cur.strip():
            out.append(cur.strip())
        cur = ""

    for line in block.split("\n"):
        if len(line) > limit_chars:
            push()
            for sent in _SENT_SPLIT_RE.split(line):
                if len(sent) > limit_chars:
                    while len(sent) > limit_chars:
                        cut = sent.rfind(" ", 0, limit_chars)
                        cut = cut if cut > limit_chars // 2 else limit_chars
                        out.append(sent[:cut].strip())
                        sent = sent[cut:]
                if cur and len(cur) + len(sent) > limit_chars:
                    push()
                cur += (" " if cur else "") + sent
            push()
            continue
        if cur and len(cur) + len(line) > limit_chars:
            push()
        cur += ("\n" if cur else "") + line
    push()
    return out or [block]


def _pack_blocks(blocks: list[str], limit_chars: int, keep_proviso: bool,
                 allow_soft_split: bool = True) -> list[str]:
    parts: list[str] = []
    cur: list[str] = []

    def flush():
        nonlocal cur
        if cur:
            parts.append("\n".join(cur).strip())
            cur = []

    for b in blocks:
        # a lone block bigger than the limit can never satisfy clause-only rules;
        # soften it via paragraphs -> sentences so every chunk stays embeddable.
        if allow_soft_split and len(b) > limit_chars:
            flush()
            pieces: list[str] | None = None
            paras = _split_paragraphs(b)
            if len(paras) > 1:
                packed = _pack_blocks(paras, limit_chars, False,
                                      allow_soft_split=False)
                pieces = packed if max(len(x) for x in packed) <= limit_chars else None
            if pieces is None:
                pieces = _hard_split(b, limit_chars)
            parts.extend(pieces)
            continue
        candidate_len = sum(len(x) + 1 for x in cur) + len(b)
        if cur and candidate_len > limit_chars:
            flush()
        cur.append(b)
    flush()

    if keep_proviso:
        fixed: list[str] = []
        for p in parts:
            first = p.split("\n", 1)[0]
            if (
                fixed
                and STAGE_RE.match(first)
                and len(p) < limit_chars // 2
                and len(fixed[-1]) + len(p) + 1 <= limit_chars
            ):
                prev_head = fixed[-1].split("\n")[0]
                if not STAGE_RE.match(prev_head):
                    fixed[-1] += "\n" + p
                    continue
            fixed.append(p)
        parts = fixed
    return parts


def chunk_statute_row(row: dict, cfg: ChunkConfig) -> list[dict]:
    """One provision row -> one or more chunk records."""
    limit = cfg.max_tokens * cfg.chars_per_token
    body = (row.get("text") or "").strip()
    head = _header(row)
    base_text = f"{head}\n{body}"

    n_parts = 1
    if len(base_text) > limit:
        parts = _pack_blocks(_split_blocks(body), limit - len(head) - 1,
                             cfg.keep_proviso_attached)
        n_parts = max(1, len(parts))
    else:
        parts = [body]

    chunks = []
    sec = str(row["section_no"])
    for i, part_body in enumerate(parts):
        text = base_text if n_parts == 1 else f"{head}\n(part {i + 1}/{n_parts} of section {sec})\n{part_body}"
        chunk_id = row.get("id") or f"{row.get('act_short', 'ACT')}_s{sec}"
        if n_parts > 1:
            chunk_id += PART_SUFFIX.format(i)
        chunks.append({
            "chunk_id": chunk_id,
            "act": row.get("act"),
            "act_short": row.get("act_short"),
            "domain": row.get("domain"),
            "regime": row.get("regime"),
            "effective_from": row.get("effective_from"),
            "effective_to": row.get("effective_to"),
            "repeals": row.get("repeals"),
            "chapter": row.get("chapter"),
            "chapter_title": row.get("chapter_title"),
            "section_no": sec,
            "title": row.get("title"),
            "part": None if n_parts == 1 else i,
            "n_parts": n_parts,
            "lang": "en",
            "text": text,
            "hash": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        })
    return chunks


def build_chunks(shard_dir: Path, out_dir: Path, cfg: ChunkConfig) -> dict:
    """Chunk every statute shard -> data/processed/chunks/{ACT}.jsonl"""
    out_dir.mkdir(parents=True, exist_ok=True)
    stats = {}
    for shard in sorted(shard_dir.glob("*.jsonl")):
        act_short = shard.stem
        n_in = n_out = oversized = 0
        with open(out_dir / shard.name, "w", encoding="utf-8") as out:
            for line in open(shard, encoding="utf-8"):
                row = json.loads(line)
                if not (row.get("text") or "").strip():
                    continue
                n_in += 1
                chunks = chunk_statute_row(row, cfg)
                if len(chunks) > 1:
                    oversized += 1
                n_out += len(chunks)
                for c in chunks:
                    c["act_short"] = c["act_short"] or act_short
                    out.write(json.dumps(c, ensure_ascii=False,
                                         separators=(",", ":")) + "\n")
        stats[act_short] = {"sections": n_in, "chunks": n_out,
                            "oversized_sections": oversized}
    return stats


def chunk_judgment(text: str, meta: dict, cfg: ChunkConfig) -> list[dict]:
    """Split a judgment by case-stage headings; header carries court/date/citation.

    meta keys: case_id, court, decision_date, citation, petitioner, respondent.
    """
    limit = cfg.max_tokens * cfg.chars_per_token
    stage_re = re.compile(
        r"^((?:[A-Z][A-Z\s/&-]{3,80})|(?:(?:I+|Held|Ruling|Judgment|Order)[\s\S]{0,60}?))$"
    )
    known_stages = {
        "FACTS", "ISSUES", "CONTENTIONS", "SUBMISSIONS", "REASONING", "ANALYSIS",
        "HELD", "RULING", "ORDER", "JUDGMENT", "DISPOSITION", "BACKGROUND",
        "COUNSEL", "CASES CITED", "CONCLUSION", "FINAL ORDER", "OBSERVATIONS",
    }
    lines = text.split("\n")
    segments: list[tuple[str, list[str]]] = [("Preamble", [])]
    for line in lines:
        stripped = line.strip()
        is_stage = (
            stripped in known_stages
            or (len(stripped) <= 80 and stage_re.match(stripped) and stripped.isupper())
        )
        if is_stage and segments[-1][1]:
            segments.append((stripped.title(), []))
        else:
            segments[-1][1].append(line)

    head = (
        f"[{meta.get('court', 'Supreme Court of India')} | {meta.get('decision_date', '?')}"
        f" | {meta.get('citation', '')} | {meta.get('petitioner', '')} v. {meta.get('respondent', '')}"
        f" | case_id={meta.get('case_id', '')}]"
    )

    chunks = []
    for stage, body_lines in segments:
        body = "\n".join(body_lines).strip()
        if not body:
            continue
        segs = [body]
        if len(head) + len(body) > limit:
            segs = _pack_blocks(_split_blocks(body), limit - len(head) - 1, False)
        for i, seg in enumerate(segs):
            cid = f"{meta.get('case_id', 'SCJ')}_{stage.upper()[:12]}"
            if len(segs) > 1:
                cid += PART_SUFFIX.format(i)
            full = f"{head}\n[{stage}]\n{seg}" if len(segs) > 1 else f"{head}\n[{stage}]\n{seg}"
            chunks.append({
                "chunk_id": cid,
                "act": "Supreme Court of India",
                "act_short": "SCJ",
                "domain": meta.get("domain", "judgments"),
                "regime": "judgment",
                "section_no": stage,
                "title": meta.get("title"),
                "court": meta.get("court"),
                "decision_date": meta.get("decision_date"),
                "citation": meta.get("citation"),
                "petitioner": meta.get("petitioner"),
                "respondent": meta.get("respondent"),
                "part": None if len(segs) == 1 else i,
                "n_parts": len(segs),
                "lang": "en",
                "text": full,
                "hash": hashlib.sha256(full.encode("utf-8")).hexdigest(),
            })
    return chunks
