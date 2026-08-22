from __future__ import annotations

import re

_MARKDOWN_NOISE = [
    re.compile(r"^Act: .*$", re.MULTILINE),
    re.compile(r"^Chapter\s+[IVXLC]+\b[^\n]*\|[^\n]*$", re.MULTILINE),
    re.compile(r"^#{1,6}\s*", re.MULTILINE),
    re.compile(r"^>\s*", re.MULTILINE),
    re.compile(r"\*{1,3}"),
    re.compile(r"_([^_\n]{1,200})_"),
]

_PROVISO_RE = re.compile(r"(?=(?:^|\.\s+)Provided (?:further )?that\b)", re.IGNORECASE)
_ILLUSTRATION_RE = re.compile(
    r"Illustration[sd]?\s*:?(.*?)(?=\n[A-Z]|\Z)", re.DOTALL | re.IGNORECASE
)
_INTERNAL_REF_RE = re.compile(r"section[s]?\s+(\d+[A-Z]?\b)", re.IGNORECASE)
_FOOTNOTE_BRACKET_RE = re.compile(r"(?<!\w)\d{1,2}\[")
_BREADCRUMB_TITLE_RE = re.compile(r"Section\s+\d+[A-Z]?:?\s*([^|\n*]+)")
_BODY_TITLE_DASH = "[\u2010\u2011\u2012\u2013\u2014\u2015-]"
_BODY_TITLE_RE = re.compile(rf"^\s*\d+[A-Z]?\.?\s*(.+?)\s*{_BODY_TITLE_DASH}", re.MULTILINE)


def extract_section_title(raw: str, section_no: str) -> str | None:
    match = _BREADCRUMB_TITLE_RE.search(raw)
    if match:
        title = clean_text(match.group(1)).strip()
        if title and not title.lower().startswith(("the ", "an ")):
            return title
    match = re.search(
        rf"^\s*{re.escape(section_no)}\.\s*(.+?)\s*{_BODY_TITLE_DASH}", raw, re.MULTILINE
    )
    if match:
        return clean_text(match.group(1)).strip()
    return None


def clean_text(raw: str) -> str:
    text = raw
    text = _MARKDOWN_NOISE[0].sub("", text)
    for pattern in _MARKDOWN_NOISE[1:]:
        text = pattern.sub(lambda m: m.group(1) if m.lastindex else "", text)
    text = _FOOTNOTE_BRACKET_RE.sub("[", text)
    text = re.sub(r"\(\s*_?(\d+[A-Za-z]?)_?\s*\)", r"(\1)", text)
    text = re.sub(r"—\s+", "—", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{2,}", "\n", text)
    return text.strip()


def split_provisos(text: str) -> tuple[str, list[str]]:
    parts = [p.strip() for p in _PROVISO_RE.split(text) if p.strip()]
    if len(parts) <= 1:
        return text, []
    body = re.sub(r"[\s.;,]+$", "", parts[0]).strip()
    provisos = [re.sub(r"^[\s.,;]+", "", p).strip() for p in parts[1:]]
    return body, provisos


def extract_illustrations(text: str) -> tuple[str, list[str]]:
    match = _ILLUSTRATION_RE.search(text)
    if not match:
        return text, []
    body = match.group(1).strip()
    illustrations = [i.strip() for i in re.split(r"(?:^|\n)(?=[A-Z(])", body) if i.strip()]
    return _ILLUSTRATION_RE.sub("", text).strip(), illustrations


def internal_refs(text: str, act_short: str) -> list[str]:
    refs = set()
    for num in _INTERNAL_REF_RE.findall(text):
        refs.add(f"{act_short}_s{num}")
    return sorted(refs)


def parse_chapter_header(raw: str | None) -> tuple[str | None, str | None]:
    if not raw:
        return None, None
    cleaned = clean_text(raw)
    return cleaned, None
