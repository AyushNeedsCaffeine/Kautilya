"""IndicTrans2 translation module (ARCHITECTURE.md §4 translator node).

Lazy-loads the 200M distilled EN↔Indic models; VRAM is managed by evicting
the caller's heavy models (embedder / reranker) before loading the translator.

Language mapping: ISO 639-1 → Florence notation used by IndicTrans2.
"""

from __future__ import annotations

import gc
from typing import Protocol

from kautilya.log import get_logger

log = get_logger(__name__)

# ISO 639-1 → Florence BCP-47 notation (IndicTrans2 native)
_LANG_MAP: dict[str, str] = {
    "en": "eng_Latn",
    "hi": "hin_Deva",
    "mr": "mar_Deva",
    "bn": "ben_Beng",
    "ta": "tam_Taml",
    "te": "tel_Telu",
    "gu": "guj_Gujr",
    "kn": "kan_Knda",
}

# Models: distilled 200M variants fit comfortably in fp16 on 4GB VRAM
_EN_INDIC_MODEL = "ai4bharat/indictrans2-en-indic-dist-200M"
_INDIC_EN_MODEL = "ai4bharat/indictrans2-indic-en-dist-200M"


class Translator(Protocol):
    def translate(self, text: str, src_lang: str, tgt_lang: str) -> str: ...


def _evict_heavy_models() -> None:
    """Best-effort VRAM cleanup before loading translation models."""
    try:
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except Exception:
        pass
    gc.collect()


class IndicTranslator:
    """Lazy-loading IndicTrans2 wrapper with per-direction model caching.

    Only the direction needed (EN→Indic or Indic→EN) is loaded; the other
    stays on disk.  Models are loaded in fp16 on GPU, fp32 on CPU.
    """

    def __init__(self, device: str | None = None):
        import torch
        self._device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self._dtype = None  # set on first load
        self._en_indic_model = None
        self._en_indic_tok = None
        self._en_indic_ip = None
        self._indic_en_model = None
        self._indic_en_tok = None
        self._indic_en_ip = None

    def _load_en_indic(self) -> None:
        if self._en_indic_model is not None:
            return
        _evict_heavy_models()
        import torch
        from IndicTransToolkit.processor import IndicProcessor
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

        dtype = torch.float16 if self._device == "cuda" else torch.float32
        log.info("loading EN→Indic model (%s, %s)", _EN_INDIC_MODEL, self._device)
        self._en_indic_tok = AutoTokenizer.from_pretrained(
            _EN_INDIC_MODEL, trust_remote_code=True)
        self._en_indic_model = AutoModelForSeq2SeqLM.from_pretrained(
            _EN_INDIC_MODEL, trust_remote_code=True,
            torch_dtype=dtype).to(self._device)
        self._en_indic_ip = IndicProcessor(inference=True)
        log.info("EN→Indic model loaded")

    def _load_indic_en(self) -> None:
        if self._indic_en_model is not None:
            return
        _evict_heavy_models()
        import torch
        from IndicTransToolkit.processor import IndicProcessor
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

        dtype = torch.float16 if self._device == "cuda" else torch.float32
        log.info("loading Indic→EN model (%s, %s)", _INDIC_EN_MODEL, self._device)
        self._indic_en_tok = AutoTokenizer.from_pretrained(
            _INDIC_EN_MODEL, trust_remote_code=True)
        self._indic_en_model = AutoModelForSeq2SeqLM.from_pretrained(
            _INDIC_EN_MODEL, trust_remote_code=True,
            torch_dtype=dtype).to(self._device)
        self._indic_en_ip = IndicProcessor(inference=True)
        log.info("Indic→EN model loaded")

    def translate(self, text: str, src_lang: str, tgt_lang: str) -> str:
        """Translate text between English and an Indic language.

        Args:
            text: Input text.
            src_lang: ISO 639-1 code (en/hi/mr/bn/ta/te/gu/kn).
            tgt_lang: ISO 639-1 code (same set).

        Returns:
            Translated text, or original text on failure.
        """
        if src_lang == tgt_lang:
            return text

        src_flo = _LANG_MAP.get(src_lang)
        tgt_flo = _LANG_MAP.get(tgt_lang)
        if not src_flo or not tgt_flo:
            log.warning("unsupported lang pair %s→%s, returning original", src_lang, tgt_lang)
            return text

        try:
            if src_lang == "en":
                return self._translate_en_indic(text, tgt_flo)
            elif tgt_lang == "en":
                return self._translate_indic_en(text, src_flo)
            else:
                # Indic→Indic: translate via English pivot
                english = self._translate_indic_en(text, src_flo)
                return self._translate_en_indic(english, tgt_flo)
        except Exception as e:
            log.warning("translation failed (%s→%s): %s", src_lang, tgt_lang, e)
            return text

    def _translate_en_indic(self, text: str, tgt_flo: str) -> str:
        import torch
        self._load_en_indic()
        batch = self._en_indic_ip.preprocess_batch(
            [text], src_lang="eng_Latn", tgt_lang=tgt_flo)
        inputs = self._en_indic_tok(
            batch, padding="longest", truncation=True,
            max_length=256, return_tensors="pt").to(self._device)
        with torch.inference_mode():
            tokens = self._en_indic_model.generate(
                **inputs, num_beams=5, max_length=256)
        decoded = self._en_indic_tok.batch_decode(
            tokens, skip_special_tokens=True, clean_up_tokenization_spaces=True)
        return self._en_indic_ip.postprocess_batch(decoded, lang=tgt_flo)[0]

    def _translate_indic_en(self, text: str, src_flo: str) -> str:
        import torch
        self._load_indic_en()
        batch = self._indic_en_ip.preprocess_batch(
            [text], src_lang=src_flo, tgt_lang="eng_Latn")
        inputs = self._indic_en_tok(
            batch, padding="longest", truncation=True,
            max_length=256, return_tensors="pt").to(self._device)
        with torch.inference_mode():
            tokens = self._indic_en_model.generate(
                **inputs, num_beams=5, max_length=256)
        decoded = self._indic_en_tok.batch_decode(
            tokens, skip_special_tokens=True, clean_up_tokenization_spaces=True)
        return self._indic_en_ip.postprocess_batch(decoded, lang="eng_Latn")[0]
