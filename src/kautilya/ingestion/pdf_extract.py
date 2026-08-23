from __future__ import annotations

import re
from pathlib import Path

import pymupdf


def extract_pdf_text(pdf_path: Path, drop_lines: list[re.Pattern] | None = None) -> str:
    doc = pymupdf.open(pdf_path)
    pages = []
    for page in doc:
        text = page.get_text("text")
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped or len(stripped) > 200:
                continue
            if stripped.isdigit():
                continue
            if drop_lines and any(p.search(stripped) for p in drop_lines):
                continue
            pages.append(stripped)
        pages.append("")
    return "\n".join(pages)


_NUM_START_RE = re.compile(r"^(?:ARTICLE\s+)?(\d+[A-Z]?)\.\s*(.*)$")
_TITLE_DASH_RE = re.compile(r"\.[ \t]*[—\u2013]")
_DASH_SPLIT_RE = re.compile(r"[—\u2013\u2010]")
_FOOTNOTE_PREFIX_RE = re.compile(r"\d{0,2}\[")
_REF_WORD_RE = re.compile(
    r"(section|article|clause|sub-?clause|item|rule|paragraph|act)\s[^.;]{0,20}$",
    re.IGNORECASE,
)


def split_constitution(text: str) -> list[tuple[str, str | None, str]]:
    """Splitter tuned to the Legislative Department COI edition.

    Handles 'N. Title.—body', dash-less articles ('45. The State shall…'),
    footnote prefixes ('2[226.', '*[45.'), and headers glued mid-paragraph.
    """
    text = _FOOTNOTE_PREFIX_RE.sub("", text).replace("*", "")
    text = re.sub(r"(\d{1,3}[A-Z]?\.\s)\d{1,2}\s+(?=[A-Z(“])", r"\1", text)
    appendix = re.search(r"^\s*(?:APPENDIX|INDEX)\b", text, re.MULTILINE)
    if appendix:
        text = text[: appendix.start()]
    head_iter = list(
        re.finditer(
            r"(?:^|(?<=[.;”\s]))(\d{1,3}[A-Z]?)\.(?:[ \t]+(?=[A-Z(“])|\n+(?=\())",
            text,
        )
    )
    filtered = [
        m
        for m in head_iter
        if not _REF_WORD_RE.search(text[max(0, m.start() - 60) : m.start()])
        and int(re.match(r"\d+", m.group(1)).group()) <= 470
    ]
    best: dict[str, tuple[int, str | None, str]] = {}
    order: list[str] = []
    for pos, match in enumerate(filtered):
        start = match.start()
        end = filtered[pos + 1].start() if pos + 1 < len(filtered) else len(text)
        chunk = text[start:end].strip()
        num = match.group(1)
        if not chunk:
            continue
        score = 1 if _TITLE_DASH_RE.search(chunk[:180]) else 0
        title = None
        dash = _DASH_SPLIT_RE.search(chunk[:180])
        if dash:
            title = re.sub(r"\s*\d+\.\s*", "", chunk[match.group(1).__len__() + 1 : dash.start()])
            title = re.sub(r"\s+", " ", title).strip(" ,").rstrip(".") or None
        if title is None:
            first_line = chunk.splitlines()[0]
            fallback = re.sub(rf"^{re.escape(num)}\.\s*", "", first_line).strip()
            if not fallback or fallback.startswith("("):
                title = None
            else:
                fallback = re.split(r"\s\(\d\)", fallback)[0]
                title = fallback[:90].strip(" ,.—-") or None
        if num not in best:
            best[num] = (score, title, chunk)
            order.append(num)
        elif (score, len(chunk)) > (best[num][0], len(best[num][2])):
            prev_title = best[num][1]
            best[num] = (score, title or prev_title, chunk)
    return [(num, best[num][1], best[num][2]) for num in order]


_AMEND_NOTE_RE = re.compile(
    r"^(?:Ins|Subs|Substituted|Inserted|Omitted|Omit|Renumbered|Rep|Added)\.\s",
)
_HIST_NOTE_RE = re.compile(r"(?:by Act\s+\d+\s+of\s+\d{4}|w\.e\.f\.)")


def split_ita_sections(text: str) -> list[tuple[str, str | None, str]]:
    """Splitter tuned to the incometaxindia.gov.in bare-act layout.

    Section numbers start a line ('14.\\t(1) ...'), the descriptive title
    sits on one or two lines ABOVE the number, and FA amendment footnotes
    are numbered lines ('1.\\t Substituted by ...').
    """
    raw_lines = text.splitlines()
    stop = None
    for i, ln in enumerate(raw_lines):
        if re.match(r"^(?:THE\s+)?(?:FIRST|SECOND|THIRD|FOURTH|FIFTH)\s+SCHEDULE\b", ln.strip(), re.I):
            stop = i
            break
    lines = raw_lines[:stop] if stop else raw_lines
    lines = [_FOOTNOTE_PREFIX_RE.sub("", ln) for ln in lines]

    consumed: set[int] = set()
    heads: list[tuple[int, str, str | None]] = []
    for i, ln in enumerate(lines):
        stripped = ln.strip()
        m = re.match(r"^(\d{1,3}[A-Z]?)\.[ \t]*(.*)$", stripped)
        if not m:
            continue
        num, rest = m.group(1), m.group(2).strip()
        if int(re.match(r"\d+", num).group()) > 600:
            continue
        if _AMEND_NOTE_RE.match(rest) or _HIST_NOTE_RE.search(rest[:120]):
            continue
        if rest and not (rest.startswith("(") or rest[0].isupper() or rest[0] in "“\""):
            continue
        title_lines: list[str] = []
        j = i - 1
        while j >= 0 and len(title_lines) < 3 and lines[j].strip():
            t = lines[j].strip()
            if (
                not (t[0].isupper() or t[0] in "“\"")
                or t.startswith("(")
                or re.match(r"^[A-Z]\.\s*—", t)
                or re.match(r"^\d+\.", t)
                or (t.isupper() and len(t) < 40)
                or len(t) > 140
            ):
                break
            title_lines.append(t)
            j -= 1
        title_lines.reverse()
        total = sum(len(t) for t in title_lines)
        while title_lines and total > 170:
            total -= len(title_lines[0])
            title_lines.pop(0)
        for k in range(j + 1, i):
            consumed.add(k)
        title = " ".join(title_lines).strip() or None
        heads.append((i, num, title))

    provisions: list[tuple[str, str | None, str]] = []
    for pos, (line_idx, num, title) in enumerate(heads):
        end = heads[pos + 1][0] if pos + 1 < len(heads) else len(lines)
        body = "\n".join(
            lines[k]
            for k in range(line_idx, end)
            if k not in consumed
        ).strip()
        if body:
            provisions.append((num, title, body))

    best: dict[str, tuple[str | None, str]] = {}
    order: list[str] = []
    for num, title, body in provisions:
        if num not in best:
            best[num] = (title, body)
            order.append(num)
    return [(num, *best[num]) for num in order]


def split_numbered_provisions(
    text: str,
    stop_marker: str | None = None,
) -> list[tuple[str, str | None, str]]:
    """Split bare-act text into (number, title, body) provisions.

    Handles '12. Definition.—In this Part...' and multi-line section bodies.
    """
    lines = text.splitlines()
    heads: list[tuple[int, str, str | None]] = []
    for idx, line in enumerate(lines):
        match = _NUM_START_RE.match(line.strip())
        if not match or _AMEND_NOTE_RE.match(match.group(2)):
            continue
        if _HIST_NOTE_RE.search(match.group(2)[:120]):
            continue
        rest = match.group(2)
        title: str | None = None
        dash = _TITLE_DASH_RE.search(rest)
        if dash and len(rest[: dash.start()]) < 120:
            title = re.sub(r"\s*\*+\s*", "", rest[: dash.start()]).strip()
            lines[idx] = rest[dash.end() :].strip()
            heads.append((idx, match.group(1), title))
        elif len(rest) < 100 and not rest.rstrip().endswith((".", ")")):
            title = re.sub(r"\s*\*+\s*", "", rest).strip()
            lines[idx] = ""
            heads.append((idx, match.group(1), title))
        else:
            heads.append((idx, match.group(1), title))

    if not heads:
        return []

    if stop_marker:
        stop_idx = next(
            (i for i, (_, num, _) in enumerate(heads) if num == stop_marker), None
        )
        if stop_idx is not None:
            heads = heads[: stop_idx + 1]

    provisions: list[tuple[str, str | None, str]] = []
    for pos, (line_idx, num, title) in enumerate(heads):
        end = heads[pos + 1][0] if pos + 1 < len(heads) else len(lines)
        body = "\n".join(lines[line_idx:end]).strip()
        if body:
            provisions.append((num, title, body))

    best: dict[str, tuple[int, str | None, str]] = {}
    order: list[str] = []
    for num, title, body in provisions:
        score = (1 if _TITLE_DASH_RE.search(body[:180]) else 0, len(body))
        if num not in best:
            best[num] = (*score, title, body)
            order.append(num)
            continue
        prev = best[num]
        if score > (prev[0], prev[1]):
            best[num] = (*score, title or prev[2], body)
    return [(num, best[num][2], best[num][3]) for num in order]
