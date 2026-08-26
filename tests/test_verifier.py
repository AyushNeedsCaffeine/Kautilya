"""Tests for the Verifier node + regenerate loop (fake NLI, no network)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from kautilya.graph.pipeline import run_query  # noqa: E402
from kautilya.graph.verifier import (  # noqa: E402
    NLIVerifier, hypothesis_variants, split_sentences, verify)

RETRIEVED = [
    {"chunk_id": "IPC_s420", "act_short": "IPC", "regime": "old",
     "section_no": "420", "title": "Cheating", "court": None,
     "citation": None, "decision_date": None,
     "domain": "criminal_substantive",
     "text": "Whoever cheats shall be punished with imprisonment which may "
             "extend to seven years and shall also be liable to fine."},
]


class FakeNLI:
    """Returns ENTAILMENT=score for every pair."""

    def __init__(self, score: float = 0.95):
        self.score = score
        self.pairs: list[tuple[str, str]] = []

    def entailment_scores(self, premise, hypotheses):
        self.pairs.extend((premise[:20], h) for h in hypotheses)
        return [self.score] * len(hypotheses)

    def best_support(self, contexts, hypotheses):
        return [self.score] * len(hypotheses)


GOOD_LEGAL = ("Under IPC s.420, cheating is punishable with imprisonment "
              "which may extend to seven years and fine [IPC_s420].")


def _state(legal=GOOD_LEGAL, retries=0, **kw):
    base = {"query_raw": "q", "retrieved": RETRIEVED,
            "answer_legal": legal, "answer_simple": "simple",
            "citations": ["IPC_s420"], "retries": retries,
            "route": None}
    base.update(kw)
    return base


def test_split_sentences():
    parts = split_sentences("One two. Three four!\nFive")
    assert parts == ["One two.", "Three four!", "Five"]


def test_variants_strip_scaffolding():
    s = ("Under IPC s.420, Section 415 defines cheating as deceiving a "
         "person to deliver property.")
    vs = hypothesis_variants(s)
    assert vs[0] == s
    assert "s." not in vs[1] and "Section 415" not in vs[1]
    assert "defines" not in vs[1]
    assert "is deceiving a person to deliver property" in vs[1]


def test_attribution_only_sentences_skipped():
    assert hypothesis_variants(
        "The primary provision for cheating is Section 415.") == []
    # substantive sentence is kept
    assert hypothesis_variants("Cheating is punishable with seven years.")


def test_pass_when_entailed():
    out = verify(_state(), nli=FakeNLI(0.95), threshold=0.75)
    assert out["route"] is None and out["verification"] == "pass"


def test_regenerate_on_low_entailment():
    out = verify(_state(), nli=FakeNLI(0.40), threshold=0.75, max_regen=2)
    assert out["route"] == "regenerate"
    assert out["retries"] == 1
    assert any("unsupported" in n for n in out["verification_notes"])


def test_refuse_after_max_regen():
    out = verify(_state(retries=2), nli=FakeNLI(0.10), max_regen=2)
    assert out["route"] == "refuse"
    assert "refusing" in out["answer_simple"].lower()


def test_invalid_citation_detected():
    bad = "Totally invented [FAKE_s999] claim here."
    out = verify(_state(legal=bad), nli=None)
    assert any("not present" in n for n in out["verification_notes"])
    assert out["verification"] == "fail"


def test_no_citations_flags_note_and_regenerates():
    bare = "Cheating is punishable with seven years."
    out = verify(_state(legal=bare), nli=None)
    assert any("no inline citations" in n for n in out["verification_notes"])
    # empty answer_legal also routes back for a real answer
    empty = verify(_state(legal=""), nli=None)
    assert empty["route"] == "regenerate"


def test_skip_when_already_refused():
    out = verify({"route": "refuse"})
    assert out["verification"] == "skipped"


# ------------------------------------------------- pipeline regen cycle
class FlakySynthLLM:
    """First answer cites an invented chunk; second attempt is clean."""

    def __init__(self):
        self.calls = 0

    def generate(self, prompt: str) -> str:
        self.calls += 1
        if "rejected by the verifier" not in prompt:
            return json.dumps({
                "answer_legal": "Magic section says ten years [MADE_UP_x].",
                "answer_simple": "Simple.",
                "citations": ["MADE_UP_x"], "refused": False})
        return json.dumps({
            "answer_legal": GOOD_LEGAL,
            "answer_simple": "Up to seven years and a fine under IPC 420.",
            "citations": ["IPC_s420"], "refused": False})

    def generate_json(self, prompt: str) -> dict:
        return json.loads(self.generate(prompt))


class StubRetriever:
    def retrieve(self, state):
        return RETRIEVED


@pytest.mark.parametrize("nli_score", [0.95])
def test_pipeline_regen_cycle_recovers(nli_score):
    out = run_query("cheating punishment?", llm=FlakySynthLLM(),
                    retriever=StubRetriever(), nli=FakeNLI(nli_score),
                    incident_date="2024-03-01")
    assert out["retries"] == 1                    # one regeneration happened
    assert out["verification"] == "pass"
    assert "[IPC_s420]" in out["answer_legal"]
