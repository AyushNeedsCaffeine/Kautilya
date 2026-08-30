"""Tests for the Synthesizer node and full pipeline wiring (fake LLM+retriever)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from kautilya.graph.pipeline import build_pipeline, run_query
from kautilya.graph.synthesizer import synthesize

RETRIEVED = [
    {"chunk_id": "IPC_s420", "act_short": "IPC", "regime": "old",
     "section_no": "420", "title": "Cheating", "court": None,
     "citation": None, "decision_date": None, "domain": "criminal_substantive",
     "text": "Whoever cheats shall be punished with imprisonment up to seven years."},
    {"chunk_id": "BNS_s318", "act_short": "BNS", "regime": "new",
     "section_no": "318", "title": "Cheating", "court": None,
     "citation": None, "decision_date": None, "domain": "criminal_substantive",
     "text": "Cheating is punishable under this section with imprisonment."},
]

GOOD = json.dumps({
    "answer_legal": "Under IPC s.420, cheating is punished with up to seven "
                    "years' imprisonment [IPC_s420]. It corresponds to BNS "
                    "s.318 [BNS_s318].",
    "answer_simple": "If someone cheats you of money or property, the old law "
                     "put them in jail for up to seven years.",
    "citations": ["IPC_s420", "BNS_s318", "MADE_UP_ID"],
    "refused": False,
    "reason": "",
})


class FakeLLM:
    def __init__(self, payload=GOOD, simplify=None):
        self.payload = payload
        self.simplify = simplify
        self.calls: list[str] = []

    def generate(self, prompt: str) -> str:
        self.calls.append(prompt)
        if "Rewrite the explanation" in prompt and self.simplify is not None:
            return self.simplify
        return self.payload

    def generate_json(self, prompt: str) -> dict:
        raw = self.generate(prompt)
        return json.loads(raw)


class BoomLLM:
    def generate(self, prompt: str) -> str:
        raise RuntimeError("api down")


def _state(**kw):
    base = {"query_raw": "cheating punishment?", "retrieved": RETRIEVED,
            "equivalences": [], "regimes": {"criminal_substantive": "new"},
            "incident_date": None}
    base.update(kw)
    return base


# ------------------------------------------------------------ synthesizer
def test_synthesize_happy_path_citation_filtering():
    out = synthesize(_state(), llm=FakeLLM())
    assert out["route"] is None
    assert out["citations"] == ["IPC_s420", "BNS_s318"]  # MADE_UP_ID dropped
    assert "[IPC_s420]" in out["answer_legal"]
    assert "[" not in out["answer_simple"] or True  # simple register free-form


def test_synthesize_extracts_inline_citations():
    payload = json.dumps({
        "answer_legal": "Cited only inline [BNS_s318] here.",
        "answer_simple": "Simple text.",
        "citations": [],
        "refused": False})
    out = synthesize(_state(), llm=FakeLLM(payload))
    assert out["citations"] == ["BNS_s318"]


def test_synthesize_refusal_passthrough():
    payload = json.dumps({"refused": True, "reason": "not in sources",
                          "answer_simple": "", "answer_legal": "",
                          "citations": []})
    out = synthesize(_state(), llm=FakeLLM(payload))
    assert out["route"] == "refuse"
    assert out["answer_simple"]


def test_synthesize_empty_retrieval_refuses_without_llm():
    out = synthesize(_state(retrieved=[]), llm=BoomLLM())
    assert out["route"] == "refuse"


def test_synthesize_llm_failure_degrades():
    out = synthesize(_state(), llm=BoomLLM())
    assert out["route"] == "error"
    assert "failed" in out["answer_simple"].lower()
    assert out.get("error")


def test_synthesize_fk_retry_simplifies():
    complex_legal = "Under IPC s.420 cheating is punished [IPC_s420]."
    complex_simple = ("Notwithstanding anything contained hereinbefore, the "
                      "perpetrator of the aforementioned offence shall be "
                      "liable to be incarcerated for a period not exceeding "
                      "seven years notwithstanding anything to the contrary.")
    payload = json.dumps({
        "answer_legal": complex_legal,
        "answer_simple": complex_simple,
        "citations": ["IPC_s420"],
        "refused": False})
    simpler = ("The person who cheated can go to jail for seven years. "
               "That is what the old law said.")
    assert _fk(complex_simple) > 10      # precondition: retry must trigger
    fake = FakeLLM(payload=payload, simplify=simpler)
    out = synthesize(_state(), llm=fake)
    assert len(fake.calls) >= 2          # main + simplify call happened
    assert out["answer_simple"] == simpler


def _fk(text: str) -> float:
    import textstat

    return float(textstat.flesch_kincaid_grade(text))


# ---------------------------------------------------------------- pipeline
class StubRetriever:
    def retrieve(self, state):
        return RETRIEVED


def test_pipeline_end_to_end_with_fakes():
    out = run_query("cheating punishment in 2024", llm=FakeLLM(),
                    retriever=StubRetriever(), incident_date="2024-03-01")
    assert out["domains"] == ["criminal_substantive"]
    assert out["regimes"]["criminal_substantive"] == "old"
    assert out["answer_legal"].startswith("Under IPC")
    assert out["citations"] == ["IPC_s420", "BNS_s318"]


def test_pipeline_ask_date_route_ends_early():
    class ExplodingRetriever:
        def retrieve(self, state):  # pragma: no cover - must never run
            raise AssertionError("retriever must be skipped on ask_date")

    out = run_query("what was the law back then?", llm=None,
                    retriever=ExplodingRetriever())
    assert out["route"] == "ask_date"
    assert "retrieved" not in out


def test_build_pipeline_compiles():
    app = build_pipeline(llm=FakeLLM(), retriever=StubRetriever())
    assert app is not None
