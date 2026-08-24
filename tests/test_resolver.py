"""Tests for the TemporalResolver node (real mapping tables, no network)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from kautilya.graph.resolver import (  # noqa: E402
    find_equivalences,
    load_mappings,
    mentioned_sections,
    resolve_temporal,
    route_regime,
)

TABLES = load_mappings()


# ------------------------------------------------------------- routing
@pytest.mark.parametrize("dom,before,after", [
    ("criminal_substantive", "2024-03-01", "2024-12-05"),
    ("criminal_procedure", "2024-06-30", "2024-07-01"),
    ("evidence", "2024-06-30", "2025-01-01"),
    ("labour", "2025-11-20", "2025-11-21"),
    ("tax", "2026-03-31", "2026-04-01"),
])
def test_route_regime_cutoffs(dom, before, after):
    assert route_regime(dom, before) == "old"
    assert route_regime(dom, after) == "new"


def test_boundary_date_is_new_regime():
    # BNS/BNSS/BSA came into force ON 2024-07-01
    assert route_regime("criminal_substantive", "2024-07-01") == "new"


def test_no_date_means_current():
    assert route_regime("criminal_substantive", None) == "current"


def test_constitutional_always_current():
    assert route_regime("constitutional", "1950-01-26") == "current"
    assert route_regime("general", "1900-01-01") == "current"


def test_unknown_domain_defaults_current():
    assert route_regime("something_else", "2000-01-01") == "current"


# --------------------------------------------------- section extraction
def test_mentioned_sections():
    q = "under section 420 IPC and s. 498A, also sec 304"
    assert mentioned_sections(q) == ["420", "498A", "304"]
    assert mentioned_sections("no citations here") == []


# --------------------------------------------------------- equivalences
def _state(query, domains, date=None, needs=False):
    regimes = {d: route_regime(d, date) for d in domains}
    return {"query_raw": query, "domains": domains,
            "incident_date": date, "needs_date": needs, "regimes": regimes}


def test_reverse_lookup_old_regime():
    st = _state("punishment for cheating under section 420",
                ["criminal_substantive"], date="2024-03-15")
    out = resolve_temporal(st)
    assert out["regimes"]["criminal_substantive"] == "old"
    eqs = [e for e in out["equivalences"] if e.old_id == "IPC_s420"]
    assert len(eqs) == 1
    assert eqs[0].equivalence == "corresponding"
    assert "BNS s.318" in eqs[0].note


def test_forward_lookup_new_regime():
    st = _state("BNS section 318 cheating punishment",
                ["criminal_substantive"], date="2024-12-01")
    out = resolve_temporal(st)
    assert out["regimes"]["criminal_substantive"] == "new"
    notes = [e.note for e in out["equivalences"] if "318" in e.note]
    assert notes and "IPC" in notes[0]
    assert "s.415" in notes[0] and "(+1 more)" in notes[0]  # capped list


def test_unknown_section_yields_nothing():
    st = _state("what about section 999 punishment",
                ["criminal_substantive"], date="2024-12-01")
    assert resolve_temporal(st)["equivalences"] == []


def test_partial_pairs_flagged():
    crpc = TABLES[("crpc", "bnss")]
    partial_pair = next((p for p in crpc.forward.values() if p.get("partial")), None)
    if partial_pair is None:
        pytest.skip("no partial pairs in crpc_to_bnss")
    old_sec = partial_pair["old"][0]
    st = _state(f"section {old_sec} procedure question",
                ["criminal_procedure"], date="2024-01-01")
    eqs = [e for e in resolve_temporal(st)["equivalences"]
           if e.old_id.endswith(f"_s{old_sec}")]
    assert eqs and any(e.equivalence == "partial" for e in eqs)


def test_ask_date_route():
    st = {"query_raw": "what was the law on cheating then?",
          "domains": ["criminal_substantive"], "needs_date": True,
          "incident_date": None}
    out = resolve_temporal(st)
    assert out["route"] == "ask_date"
    assert out["regimes"] == {}


def test_node_happy_path_full_state():
    st = _state("March 2024 mein cheating hui thi - kaunsa section 420 lagega?",
                ["criminal_substantive"], date="2024-03-01")
    out = resolve_temporal(st)
    assert out["route"] is None
    assert out["regimes"] == {"criminal_substantive": "old"}
    assert any(e.old_id == "IPC_s420" for e in out["equivalences"])
