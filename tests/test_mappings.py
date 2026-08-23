"""Validation for data/mappings/*.json temporal correspondence tables."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

MAP_DIR = Path("data/mappings")
STATUTES = Path("data/processed/statutes")

TABLES = {
    "ipc_to_bns": ("IPC", "BNS"),
    "crpc_to_bnss": ("CRPC", "BNSS"),
    "iea_to_bsa": ("IEA", "BSA"),
}

ANCHORS = {
    "ipc_to_bns": {("302", "103"), ("375", "63"), ("498A", "85"), ("420", "318")},
    "crpc_to_bnss": {("154", "173"), ("438", "482"), ("125", "144"), ("167", "187")},
    "iea_to_bsa": {("65B", "63"), ("45", "39"), ("32", "26")},
}

SEC_RE = re.compile(r"^\d{1,3}[A-Z]?$")


def _load_shard(short: str) -> set[str]:
    nums = set()
    with open(STATUTES / f"{short}.jsonl", encoding="utf-8") as f:
        for line in f:
            s = json.loads(line)["section_no"]
            if SEC_RE.match(s):
                nums.add(s)
    return nums


@pytest.fixture(scope="module", params=TABLES.keys())
def table(request):
    name = request.param
    doc = json.loads((MAP_DIR / f"{name}.json").read_text(encoding="utf-8"))
    return name, doc


def test_schema_and_counts(table):
    name, doc = table
    assert {"meta", "pairs", "unmapped_old", "unmapped_new"} <= doc.keys()
    assert doc["meta"]["cutoff"] == "2024-07-01"
    assert len(doc["pairs"]) == doc["meta"]["counts"]["pairs"] > 0


def test_pairs_reference_real_sections(table):
    name, doc = table
    old_short, new_short = TABLES[name]
    old_shard, new_shard = _load_shard(old_short), _load_shard(new_short)
    for pair in doc["pairs"]:
        assert SEC_RE.match(pair["new"]) and pair["new"] in new_shard, pair
        assert pair["old"], pair
        for o in pair["old"]:
            assert o in old_shard, (name, o)


def test_unmapped_disjoint_from_pairs(table):
    _, doc = table
    mapped_new = {p["new"] for p in doc["pairs"]}
    mapped_old = {o for p in doc["pairs"] for o in p["old"]}
    assert not mapped_new & set(doc["unmapped_new"])
    assert not mapped_old & set(doc["unmapped_old"])


def test_known_anchors():
    for name, checks in ANCHORS.items():
        doc = json.loads((MAP_DIR / f"{name}.json").read_text(encoding="utf-8"))
        idx: dict[str, set[str]] = {}
        for p in doc["pairs"]:
            for o in p["old"]:
                idx.setdefault(o, set()).add(p["new"])
        for old, want in checks:
            assert want in idx.get(old, set()), (name, old, idx.get(old))


def test_ipc_patch_quality():
    """s.375 patched in; historical repeal-stubs kept out."""
    have: dict[str, str] = {}
    with open(STATUTES / "IPC.jsonl", encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            if SEC_RE.match(r["section_no"]):
                have[r["section_no"]] = r["text"]
    for sec in ("34", "375", "376C", "376D"):
        assert sec in have and len(have[sec]) > 100, sec
    for sec in ("56", "62", "165", "480"):
        assert sec not in have, sec
