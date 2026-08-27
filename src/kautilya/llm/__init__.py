"""LLM client factory — creates the right client from settings + CLI override."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from kautilya.config import load_settings


def create_llm(provider: str | None = None,
               model: str | None = None,
               temperature: float | None = None,
               config_path: Path | None = None,
               retries: int | None = None) -> Any:
    """Return a GeminiClient or OllamaClient.

    Priority: explicit args > settings.yaml values.
    ``provider`` must be ``"gemini"`` or ``"ollama"`` (or ``None`` to
    read from settings).
    ``retries`` caps transient-backoff retries (None = client default).
    """
    settings = load_settings(config_path or Path("config/settings.yaml"))
    prov = (provider or settings.llm.provider).lower()
    mdl = model or settings.llm.model
    temp = temperature if temperature is not None else settings.llm.temperature

    if prov == "ollama":
        from kautilya.llm.ollama import OllamaClient
        default = "qwen2.5:3b"
        return OllamaClient(model=mdl if model else default, temperature=temp,
                            retries=retries if retries is not None else 3)
    else:
        from kautilya.llm.gemini import GeminiClient
        return GeminiClient(model=mdl, temperature=temp,
                            retries=retries if retries is not None else 6)
