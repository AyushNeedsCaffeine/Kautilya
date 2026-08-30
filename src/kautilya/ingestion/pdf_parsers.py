from __future__ import annotations

import re
from datetime import date
from pathlib import Path

from kautilya.ingestion.pdf_extract import (
    extract_pdf_text,
    split_constitution,
    split_ita_sections,
    split_numbered_provisions,
)
from kautilya.ingestion.sources import ActSource
from kautilya.log import get_logger
from kautilya.schemas import Provision

logger = get_logger(__name__)

_CRP_FOOTER = re.compile(r"^\d{1,4}\]?$|^THE CODE OF CRIMINAL PROCEDURE.*$", re.IGNORECASE)
_COI_NOISE = re.compile(
    r"^(THE CONSTITUTION OF INDIA|CONTENTS.*|Preamble|APPENDIX.*"
    r"|\(Part\s+[IVXLC]+\b[^)]*$|\(PART\s+[IVXLC]+\b[^)]*"
    r"|^\[?PART\s+[IVXLC]+\]?[A-Z\s]*$|.*\(Sixth Reprint\).*)$",
    re.IGNORECASE,
)
_COI_RUNNING_HEAD_RE = re.compile(r"^\([^()]{0,60}(Part|PART)\s+[IVXLC]+[^)]*\)?$")


def _make_provision(source: ActSource, num: str, title: str | None, body: str) -> Provision:
    from kautilya.ingestion import textutils

    cleaned = textutils.clean_text(body)
    cleaned_body, provisos = textutils.split_provisos(cleaned)
    return Provision(
        id=f"{source.short}_s{num}",
        domain=source.domain,
        act=source.full_name,
        act_short=source.short,
        regime=source.regime,
        effective_from=source.effective_from,
        effective_to=source.effective_to,
        repeals=source.repeals,
        section_no=num,
        title=title,
        text=cleaned_body,
        provisos=provisos,
        cross_refs=textutils.internal_refs(cleaned_body, source.short),
    )


def parse_crpc(pdf_path: Path) -> list[Provision]:
    source = ActSource(
        "crpc_pdf", "CRPC", "Code of Criminal Procedure, 1973",
        "criminal_procedure", "old",
        effective_from=date(1974, 4, 1),
        effective_to=date(2024, 6, 30),
    )
    text = extract_pdf_text(pdf_path, drop_lines=[_CRP_FOOTER])
    provisions = [
        _make_provision(source, num, title, body)
        for num, title, body in split_numbered_provisions(text, stop_marker="485")
    ]
    logger.info("CrPC: %d sections parsed", len(provisions))
    return provisions


def parse_constitution(pdf_path: Path) -> list[Provision]:
    source = ActSource(
        "coi_pdf", "COI", "Constitution of India",
        "constitutional", "current",
        effective_from=date(1950, 1, 26),
    )
    text = extract_pdf_text(
        pdf_path, drop_lines=[_COI_NOISE, _COI_RUNNING_HEAD_RE]
    )
    raw = split_constitution(text)
    seen: set[str] = set()
    provisions: list[Provision] = []
    for num, title, body in raw:
        if num in seen:
            continue
        seen.add(num)
        provisions.append(_make_provision(source, num, title, body))
    logger.info("COI: %d articles parsed", len(provisions))
    return provisions


def parse_ita2025(pdf_path: Path) -> list[Provision]:
    source = ActSource(
        "ita2025_pdf", "ITA2025", "Income-tax Act, 2025",
        "tax", "current",
        effective_from=date(2026, 4, 1),
    )
    text = extract_pdf_text(pdf_path)
    provisions = [
        _make_provision(source, num, title, body)
        for num, title, body in split_ita_sections(text)
    ]
    logger.info("ITA2025: %d sections parsed", len(provisions))
    return provisions


def write_shards(provisions: list[Provision], out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    shard = out_dir / f"{provisions[0].act_short}.jsonl"
    with open(shard, "w", encoding="utf-8") as fh:
        fh.writelines(p.model_dump_json() + "\n" for p in provisions)
    return shard
