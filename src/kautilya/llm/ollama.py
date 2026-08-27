"""Thin Ollama client wrapper.

Duck-typed as LLMClient (generate_json required) — same interface as
GeminiClient so all pipeline nodes work unchanged.
"""

from __future__ import annotations

import json
import re
import time
from typing import Any

import httpx

from kautilya.log import get_logger

log = get_logger(__name__)

_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)
_BASE_URL = "http://127.0.0.1:11434"


def strip_fences(text: str) -> str:
    return _FENCE_RE.sub("", text.strip()).strip()


class OllamaClient:
    """Lazy Ollama wrapper; talks to a local ``ollama serve`` instance."""

    def __init__(self, model: str = "qwen2.5:3b", temperature: float = 0.1,
                 base_url: str = _BASE_URL, retries: int = 3):
        self.model = model
        self.temperature = temperature
        self.base_url = base_url.rstrip("/")
        self.retries = retries
        self._http: httpx.Client | None = None

    @property
    def http(self) -> httpx.Client:
        if self._http is None:
            self._http = httpx.Client(base_url=self.base_url, timeout=600.0)
        return self._http

    # -- health -----------------------------------------------------------
    def health(self) -> tuple[bool, str]:
        """Cheap liveness probe for the UI status pill / preflight."""
        try:
            with httpx.Client(base_url=self.base_url, timeout=5.0) as http:
                resp = http.get("/api/tags")
                resp.raise_for_status()
                models = [m.get("name", "?")
                          for m in resp.json().get("models", [])]
                return True, ", ".join(models[:5]) or "online"
        except Exception as e:  # noqa: BLE001
            return False, str(e)[:120]

    # -- low level ---------------------------------------------------------
    def generate(self, prompt: str, retries: int | None = None) -> str:
        """Call ``POST /api/generate`` with backoff on transient errors."""
        retries = self.retries if retries is None else retries
        delays = (5.0, 15.0, 30.0)
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": self.temperature},
        }
        for attempt in range(retries + 1):
            try:
                resp = self.http.post("/api/generate", json=payload)
                resp.raise_for_status()
                data = resp.json()
                return data.get("response", "")
            except Exception as e:  # noqa: BLE001
                transient = any(t in str(e) for t in
                                ("503", "429", "500", "connection",
                                 "timeout", "CONNECT"))
                if not transient or attempt == retries:
                    raise
                wait = delays[min(attempt, len(delays) - 1)]
                log.warning("ollama: %s; retry %d/%d in %.0fs",
                            str(e)[:120], attempt + 1, retries, wait)
                time.sleep(wait)
        raise RuntimeError("unreachable")  # pragma: no cover

    # -- high level --------------------------------------------------------
    def generate_json(self, prompt: str, retries: int | None = None) -> dict[str, Any]:
        raw = self.generate(prompt, retries=retries)
        try:
            out = json.loads(strip_fences(raw))
        except json.JSONDecodeError:
            log.warning("ollama returned non-JSON; attempting brace rescue")
            m = re.search(r"\{.*\}", raw, re.DOTALL)
            if not m:
                raise
            out = json.loads(m.group(0))
        if not isinstance(out, dict):
            raise ValueError(f"expected JSON object, got {type(out).__name__}")
        return out
