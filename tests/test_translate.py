"""Tests for kautilya.translate — language mapping, IndicTranslator, translate_node."""

from __future__ import annotations

from kautilya.graph.pipeline import translate_node
from kautilya.graph.state import PipelineState
from kautilya.translate.indictrans2 import (
    _LANG_MAP,
    IndicTranslator,
    _evict_heavy_models,
)

# ── language mapping ──────────────────────────────────────────────────────

class TestLangMap:
    def test_all_expected_codes_present(self):
        expected = {"en", "hi", "mr", "bn", "ta", "te", "gu", "kn"}
        assert set(_LANG_MAP.keys()) == expected

    def test_florence_format(self):
        for iso, flo in _LANG_MAP.items():
            assert "_" in flo, f"{iso} -> {flo} missing underscore"
            assert len(flo.split("_")) == 2

    def test_en_maps_to_latn(self):
        assert _LANG_MAP["en"] == "eng_Latn"

    def test_hi_maps_to_deva(self):
        assert _LANG_MAP["hi"] == "hin_Deva"


# ── FakeTranslator ────────────────────────────────────────────────────────

class FakeTranslator:
    """Deterministic translator for tests — prefixes target lang code."""

    def __init__(self, fail: bool = False):
        self._fail = fail
        self.calls: list[tuple[str, str, str]] = []

    def translate(self, text: str, src_lang: str, tgt_lang: str) -> str:
        self.calls.append((text, src_lang, tgt_lang))
        if self._fail:
            raise RuntimeError("simulated translation failure")
        if src_lang == tgt_lang:
            return text
        return f"[{tgt_lang}]{text}"


# ── IndicTranslator (language validation only, no model load) ─────────────

class TestIndicTranslator:
    def test_same_lang_passthrough(self):
        t = IndicTranslator.__new__(IndicTranslator)
        assert t.translate("hello", "en", "en") == "hello"

    def test_unsupported_lang_fallback(self):
        t = IndicTranslator.__new__(IndicTranslator)
        assert t.translate("hello", "en", "fr") == "hello"

    def test_unsupported_tgt_fallback(self):
        t = IndicTranslator.__new__(IndicTranslator)
        assert t.translate("hello", "en", "xyz") == "hello"


# ── translate_node ────────────────────────────────────────────────────────

class TestTranslateNode:
    def test_no_final_lang(self):
        """When final_lang is None/en, answer_translated stays None."""
        state: PipelineState = {
            "answer_simple": "Section 420 punishes cheating.",
            "route": None,
        }
        out = translate_node(state, translator=FakeTranslator())
        assert out["answer_translated"] is None

    def test_en_to_hi(self):
        state: PipelineState = {
            "answer_simple": "Cheating is punished.",
            "final_lang": "hi",
            "route": None,
        }
        tr = FakeTranslator()
        out = translate_node(state, translator=tr)
        assert out["answer_translated"] == "[hi]Cheating is punished."
        assert len(tr.calls) == 1
        assert tr.calls[0][1:] == ("en", "hi")

    def test_refuse_skips_translation(self):
        state: PipelineState = {
            "answer_simple": "Could not verify.",
            "final_lang": "hi",
            "route": "refuse",
        }
        out = translate_node(state, translator=FakeTranslator())
        assert out["answer_translated"] is None

    def test_empty_answer_skips(self):
        state: PipelineState = {
            "answer_simple": "",
            "final_lang": "hi",
            "route": None,
        }
        out = translate_node(state, translator=FakeTranslator())
        assert out["answer_translated"] is None

    def test_translation_failure_fallback(self):
        """On exception, translate_node returns original text (not None)."""
        state: PipelineState = {
            "answer_simple": "Some answer.",
            "final_lang": "hi",
            "route": None,
        }
        out = translate_node(state, translator=FakeTranslator(fail=True))
        assert out["answer_translated"] == "Some answer."


# ── pipeline integration ──────────────────────────────────────────────────

class TestPipelineTranslate:
    def test_translate_reaches_end(self):
        """Full pipeline with a FakeLLM hits translate then END."""
        import json as _json

        from kautilya.graph.pipeline import build_pipeline

        class FakeLLM:
            def generate_json(self, *a, **kw):
                return {"answer_legal": "Under BNS s.420 [BNS_s420].",
                        "answer_simple": "Cheating is punished.",
                        "citations": ["BNS_s420"], "refused": False}
            def generate(self, *a, **kw):
                return _json.dumps({"answer_legal": "Under BNS s.420 [BNS_s420].",
                                    "answer_simple": "Cheating is punished.",
                                    "citations": ["BNS_s420"]})

        class FakeRetriever:
            def retrieve(self, state):
                return [{"chunk_id": "BNS_s420", "text": "Punishment for cheating.",
                         "act_short": "BNS", "section_no": "420",
                         "domain": "criminal_substantive", "regime": "new",
                         "title": "Cheating"}]

        tr = FakeTranslator()
        pipeline = build_pipeline(llm=FakeLLM(), retriever=FakeRetriever(),
                                  translator=tr)
        out = pipeline.invoke({"query_raw": "what is section 420?",
                               "final_lang": "hi", "retries": 0})
        assert out.get("answer_translated") == "[hi]Cheating is punished."
        assert out.get("route") is None


# ── evict helper ──────────────────────────────────────────────────────────

class TestEvict:
    def test_evict_does_not_crash(self):
        _evict_heavy_models()  # no GPU in CI, should be no-op
