"""Tests for the KautilyaBench harness (metrics + runner, all offline)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from kautilya.eval.bench import (  # noqa: E402
    Record, citation_precision, evaluate, hit_at_k, load_bench,
    mrr_at_k, refusal_correct, route_matches, temporal_correct)


def test_hit_and_mrr_basics():
    gold = ["IPC_s302"]
    assert hit_at_k(["A", "B", "IPC_s302"], gold, 5)
    assert not hit_at_k(["A", "B", "C"], gold, 5)
    # rank 3 -> 1/3; miss -> 0
    assert mrr_at_k(["X", "Y", "IPC_s302"], gold, 8) == pytest.approx(1 / 3)
    assert mrr_at_k(["X"], gold, 8) == 0.0


def test_citation_precision_ignores_part_suffixes():
    rec = Record(id="t", query="q", gold_chunk_ids=["IPC_s125"],
                 related_chunk_ids=["BNSS_s144"])
    prec, n = citation_precision(["IPC_s125_p0", "BNSS_s144_p2",
                                  "SCJ_whatever"], rec)
    assert (prec, n) == (pytest.approx(2 / 3), 3)
    prec0, _ = citation_precision([], rec)
    assert prec0 == 1.0


def test_temporal_correct_prefix_matching():
    rec = Record(id="t", query="q",
                 expected_regimes={"criminal_substantive": "old"})
    assert temporal_correct(rec, {"criminal_substantive": "old"})
    assert not temporal_correct(rec, {"criminal_substantive": "new"})
    assert not temporal_correct(rec, {})
    # rows without expectations are vacuously correct
    bare = Record(id="t2", query="q")
    assert temporal_correct(bare, None)


def test_route_and_refusal():
    r_answer = Record(id="a", query="q")
    r_ask = Record(id="b", query="q", expected_route="ask_date")
    r_refuse = Record(id="c", query="q", must_refuse=True)
    assert refusal_correct(r_refuse, {"route": "refuse"})
    assert not refusal_correct(r_refuse, {"route": None})
    assert refusal_correct(r_answer, {"route": None})
    assert not route_matches(r_ask, {"route": None})
    assert route_matches(r_ask, {"route": "ask_date"})


def _tmp_bench(tmp_path: Path) -> Path:
    rows = [
        {"id": "r1", "query": "murder punishment", "category": "regime_old",
         "gold_chunk_ids": ["IPC_s302"],
         "expected_regimes": {"criminal_substantive": "old"}},
        {"id": "r2", "query": "65B certificate", "category": "landmark",
         "gold_chunk_ids": ["IEA_s65B"], "must_refuse": False},
        {"id": "r3", "query": "register a company?", "category": "gap",
         "gold_chunk_ids": [], "must_refuse": True},
    ]
    p = tmp_path / "bench.jsonl"
    p.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    return p


def test_load_bench_roundtrip(tmp_path):
    recs = load_bench(_tmp_bench(tmp_path))
    assert len(recs) == 3 and recs[0].id == "r1"
    assert recs[2].must_refuse is True


class FakeRetriever:
    """Returns fixed top-k per query via a lookup."""

    def __init__(self, mapping):
        self.mapping = mapping

    def retrieve(self, state):
        ids = self.mapping.get(state["query_raw"], [])
        return [{"chunk_id": i} for i in ids]


def test_evaluate_retrieval_stage_aggregates(tmp_path):
    retr = FakeRetriever({
        "murder punishment": ["BNS_s103", "IPC_s302"],   # gold at rank 2
        "65B certificate": ["IEA_s65B"],                 # direct hit
        "register a company?": ["IPC_s420"],             # should refuse-ish
    })
    report = evaluate(load_bench(_tmp_bench(tmp_path)), retriever=retr,
                      final_k=8, trace_path=tmp_path / "trace.jsonl")
    assert report["stage"] == "retrieval"
    assert report["hit5"] == 0.667                    # rounded to 3dp
    assert report["mrr8"] == pytest.approx((0.5 + 1.0 + 0.0) / 3)
    # retrieval stage cannot refuse -> gap row counts as incorrect
    assert report["refusal_correctness"] == 0.667
    trace = [json.loads(l) for l in (tmp_path / "trace.jsonl").open()]
    assert len(trace) == 3 and trace[0]["mrr8"] == pytest.approx(0.5)


def test_evaluate_full_stage_with_fakes(tmp_path):
    def pipeline_fn(query, incident_date=None):
        if "company" in query:
            return {"route": "refuse", "retrieved": [],
                    "citations": [], "regimes": {},
                    "answer_simple": "", "answer_legal": ""}
        cited = ("IEA_s65B" if "65B" in query else "IPC_s302")
        return {"route": None, "verification": "pass",
                "retrieved": [{"chunk_id": cited}],
                "citations": [cited],
                "regimes": {"criminal_substantive": "old"},
                "answer_simple": "Jail for life under section 302 IPC.",
                "answer_legal": f"Claim supported [{cited}]."}

    report = evaluate(load_bench(_tmp_bench(tmp_path)),
                      pipeline_fn=pipeline_fn, final_k=8)
    assert report["stage"] == "full"
    assert report["temporal_accuracy"] == 1.0     # only r1 has expectations
    assert report["refusal_correctness"] == 1.0
    assert report["citation_precision"] == 1.0


def test_synthesis_failure_disqualified_and_resumed(tmp_path):
    legit = {"id": "r1", "query": "murder punishment",
             "category": "regime_old", "gold_chunk_ids": ["IPC_s302"],
             "expected_regimes": {"criminal_substantive": "old"}}
    trace = tmp_path / "trace.jsonl"
    trace.write_text(json.dumps({
        "id": "r1", "route": "refuse", "regimes": {}, "verification": "n/a",
        "answer_simple": "Answer generation failed (ClientError). "
                         "Please try again.",
        "answer_legal": "", "citations": [], "hit5": True, "hit8": True,
        "mrr8": 1.0, "cit_prec": 1.0, "n_cited": 0, "temporal_ok": True,
        "route_ok": False, "refusal_ok": True, "latency_s": 2873.9,
        "gold": ["IPC_s302"]}) + "\n")

    def pipeline_fn(query, incident_date=None):
        return {"route": None, "verification": "pass",
                "retrieved": [{"chunk_id": "IPC_s302"}],
                "citations": ["IPC_s302"],
                "regimes": {"criminal_substantive": "old"},
                "answer_simple": "Jail for life under section 302 IPC.",
                "answer_legal": "Claim supported [IPC_s302]."}

    # resume must NOT treat the failed row as done -> it reruns r1
    report = evaluate([Record(id="r1", query="murder punishment",
                              category="regime_old",
                              gold_chunk_ids=["IPC_s302"],
                              incident_date="2024-03-15",
                              expected_regimes={"criminal_substantive": "old"})],
                      pipeline_fn=pipeline_fn, final_k=8,
                      trace_path=trace, resume=True)
    assert report["n_records"] == 1                  # re-ran the failed row
    assert report["n_errors"] == 0
    rows = [json.loads(l) for l in trace.open()]
    assert len(rows) == 2                            # appended after old row
    # the last (valid) row carries the real answer
    assert "Answer generation failed" not in rows[-1]["answer_simple"]
