"""Tests for the QueryAnalyzer node (no network, no API key needed)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from kautilya.graph.analyzer import (  # noqa: E402
    analyze_query,
    detect_domains,
    detect_language,
    parse_date,
)
from kautilya.llm.gemini import MissingAPIKeyError, strip_fences  # noqa: E402


class FakeLLM:
    def __init__(self, payload: str):
        self.payload = payload
        self.calls: list[str] = []

    def generate_json(self, prompt: str) -> dict:
        self.calls.append(prompt)
        import json

        return json.loads(strip_fences(self.payload))


class BoomLLM:
    def generate_json(self, prompt: str) -> dict:
        raise MissingAPIKeyError("no key")


# ------------------------------------------------------------- primitives
def test_detect_language_scripts():
    assert detect_language("murder punishment section") == "en"
    assert detect_language("हत्या की सजा क्या है") == "hi"
    assert detect_language("এই আইন কী") == "bn"
    assert detect_language("தண்டனை என்ன") == "ta"


def test_detect_language_romanised_hindi():
    assert detect_language("March 2024 mein cheating hui thi") == "hi"


def test_parse_dates():
    assert parse_date("incident on 2024-03-15 ok") == "2024-03-15"
    assert parse_date("dated 05/03/2024 fir") == "2024-03-05"
    assert parse_date("in March 2024 the cheating") == "2024-03-01"
    assert parse_date("during 2023 something") == "2023-01-01"
    assert parse_date("what is the law on murder") is None


def test_detect_domains():
    assert "criminal_substantive" in detect_domains("punishment for murder")
    assert "criminal_procedure" in detect_domains("bail in cognizable case")
    assert "evidence" in detect_domains("65B certificate admissibility")
    assert detect_domains("hello world") == ["general"]


# ------------------------------------------------------------------ node
def test_analyzer_llm_path():
    fake = FakeLLM('{"input_lang": "hi", "domains": ["criminal_substantive",'
                   ' "bogus_domain"], "entities": ["cheating"],'
                   ' "incident_date": null, "needs_date": true,'
                   ' "final_lang": "en"}')
    out = analyze_query({"query_raw": "March 2024 mein cheating hui thi"},
                        llm=fake)
    assert len(fake.calls) == 1
    assert out["domains"] == ["criminal_substantive"]      # bogus filtered
    assert out["input_lang"] == "hi" and out["final_lang"] == "en"
    assert out["needs_date"] is True


def test_analyzer_falls_back_when_llm_raises():
    out = analyze_query({"query_raw": "bail for cognizable offence"},
                        llm=BoomLLM())
    assert out["domains"] == ["criminal_procedure"]
    assert out["input_lang"] == "en"


def test_analyzer_no_llm_offline():
    out = analyze_query({"query_raw":
                         "March 2024 mein cheating hui thi - kaunsa section?"})
    # romanised hindi detected, explicit month-year parsed -> no date ask
    assert out["input_lang"] == "hi"
    assert out["incident_date"] == "2024-03-01"
    assert out["needs_date"] is False
    assert "criminal_substantive" in out["domains"]
    assert out["query_raw"].endswith("section?")


def test_analyzer_past_tense_without_date_asks():
    out = analyze_query({"query_raw": "what was the punishment for cheating then"})
    assert out["incident_date"] is None
    assert out["needs_date"] is True


# ------------------------------------------------------------ gemini glue
def test_strip_fences():
    assert strip_fences('```json\n{"a": 1}\n```') == '{"a": 1}'
    assert strip_fences('{"a": 1}') == '{"a": 1}'


def test_gemini_key_missing_message(monkeypatch):
    from kautilya.llm.gemini import GeminiClient

    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(MissingAPIKeyError, match="AIza"):
        GeminiClient().client
