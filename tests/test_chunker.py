"""Tests for the section-aware legal chunker."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from kautilya.chunking.legal_chunker import (  # noqa: E402
    ChunkConfig,
    chunk_judgment,
    chunk_statute_row,
)

CFG = ChunkConfig(max_tokens=100, chars_per_token=4)  # 400 chars for fast tests

PROV = {
    "id": "BNS_s103",
    "act": "Bharatiya Nyaya Sanhita, 2023",
    "act_short": "BNS",
    "domain": "criminal_substantive",
    "regime": "new",
    "effective_from": "2024-07-01",
    "effective_to": None,
    "chapter": "II",
    "chapter_title": "Of Punishments",
    "section_no": "103",
    "title": "Punishment for murder",
    "text": "Whoever commits murder shall be punished with death or imprisonment for life.",
}


def test_small_section_single_chunk():
    out = chunk_statute_row(PROV, CFG)
    assert len(out) == 1
    c = out[0]
    assert c["chunk_id"] == "BNS_s103"
    assert c["part"] is None and c["n_parts"] == 1
    assert c["text"].startswith("[Bharatiya Nyaya Sanhita, 2023")
    assert "regime=new" in c["text"]
    assert len(c["hash"]) == 64


def test_oversized_section_splits_at_clauses():
    clauses = "\n".join(
        f"({chr(ord('a') + i)}) Clause number {i} with a reasonably long line of "
        "legal prose that pads the length of this section body considerably." * 3
        for i in range(8)
    )
    row = dict(PROV)
    row["text"] = "Punishment overview follows.\n" + clauses + \
        "\nProvided that nothing herein shall apply to soldiers acting in good faith."
    out = chunk_statute_row(row, CFG)
    assert len(out) > 1
    assert [c["chunk_id"] for c in out] == [f"BNS_s103_p{i}" for i in range(len(out))]
    # every part repeats the context header
    for c in out:
        assert c["text"].startswith("[Bharatiya Nyaya Sanhita, 2023")
        assert "(part " in c["text"]
    # no part starts with a proviso line
    for c in out[1:]:
        body = c["text"].split("\n", 2)[-1]
        assert not body.lstrip().lower().startswith("provided that")


def test_chunk_id_grammar_matches_normalizer():
    from kautilya.ingestion.normalize import _part_order

    out = chunk_statute_row(dict(PROV), CFG)
    assert _part_order(out[0]["chunk_id"]) == 0


def test_judgment_stage_segmentation():
    text = (
        "Leave granted.\n"
        "FACTS\nThe appellant was arrested on 1 March.\n"
        "ISSUES\nWhether the arrest complied with s.41A.\n"
        "HELD\nThe arrest was illegal; bail allowed.\n"
    )
    meta = {
        "case_id": "SCJ_2024_5_10_20", "court": "Supreme Court of India",
        "decision_date": "2024-05-01", "citation": "2024 INSC 1234",
        "petitioner": "A", "respondent": "State",
    }
    out = chunk_judgment(text, meta, CFG)
    stages = [c["section_no"] for c in out]
    assert stages[:4] == ["Preamble", "Facts", "Issues", "Held"]
    assert all(c["text"].startswith("[Supreme Court of India | 2024-05-01") for c in out)
    assert all("v. State" in c["text"] for c in out)


def test_clauseless_wall_gets_soft_split():
    row = dict(PROV)
    row["section_no"] = "12"
    row["id"] = "ITA1961_s12"
    row["act_short"] = "ITA1961"
    # one giant block with no clause markers at all
    para = ("The word referred to in this section shall be construed in accordance "
            "with the provisions thereof; and further explanation follows here. ")
    row["text"] = para * 60
    out = chunk_statute_row(row, CFG)
    assert len(out) > 3
    for c in out:
        est = len(c["text"]) / (CFG.max_tokens * CFG.chars_per_token)
        assert est <= 1.05, (c["chunk_id"], len(c["text"]))


def test_table_wall_splits_by_lines():
    row = dict(PROV)
    row["section_no"] = "531"
    row["id"] = "BNSS_s531"
    row["act_short"] = "BNSS"
    # repeal-table style: many short lines, no terminal punctuation
    line = "Short title of the repealed enactment some old code number 1 of 1860  "
    row["text"] = "\n".join([line] * 400)
    out = chunk_statute_row(row, CFG)
    assert len(out) > 5
    assert all(len(c["text"]) <= CFG.max_tokens * CFG.chars_per_token * 1.05 for c in out)
