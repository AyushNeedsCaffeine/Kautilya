"""Thin Gemini client wrapper (google-genai SDK).

All pipeline nodes receive an LLM object duck-typed as `LLMClient`
(only `generate_json` is required), so tests inject fakes and the
real key is read from the environment at call time — never hardcoded.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any, Protocol

from kautilya.log import get_logger

log = get_logger(__name__)

_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)
# AIza... = classic keys; AQ.Ab8... = Google's 2025+ key format
_KEY_RE = re.compile(r"^(AIza|AQ\.)[A-Za-z0-9_\-]+$")


class MissingAPIKeyError(RuntimeError):
    """Raised when GEMINI_API_KEY is absent/empty."""


class LLMClient(Protocol):
    def generate_json(self, prompt: str) -> dict[str, Any]: ...


def strip_fences(text: str) -> str:
    return _FENCE_RE.sub("", text.strip()).strip()


class GeminiClient:
    """Lazy google-genai wrapper; safe to import without the package."""

    def __init__(self, model: str = "gemini-2.0-flash", temperature: float = 0.1):
        self.model = model
        self.temperature = temperature
        self._client = None  # created on first use

    @property
    def client(self):
        if self._client is None:
            key = (os.environ.get("GEMINI_API_KEY") or "").strip()
            if not _KEY_RE.match(key):
                raise MissingAPIKeyError(
                    "GEMINI_API_KEY missing or malformed - expected an "
                    "AIza... or AQ.Ab8... key (see .env.example; get one at "
                    "https://aistudio.google.com/apikey)"
                )
            try:
                from google import genai
            except ImportError as e:  # pragma: no cover
                raise MissingAPIKeyError(
                    "google-genai package not installed"
                ) from e
            self._client = genai.Client(api_key=key)
        return self._client

    # -- low level ---------------------------------------------------------
    def generate(self, prompt: str) -> str:
        from google.genai import types

        resp = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(temperature=self.temperature),
        )
        return resp.text or ""

    # -- high level --------------------------------------------------------
    def generate_json(self, prompt: str) -> dict[str, Any]:
        raw = self.generate(prompt)
        try:
            out = json.loads(strip_fences(raw))
        except json.JSONDecodeError:
            log.warning("gemini returned non-JSON; attempting brace rescue")
            m = re.search(r"\{.*\}", raw, re.DOTALL)
            if not m:
                raise
            out = json.loads(m.group(0))
        if not isinstance(out, dict):
            raise ValueError(f"expected JSON object, got {type(out).__name__}")
        return out
