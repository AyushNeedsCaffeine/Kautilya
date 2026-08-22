from __future__ import annotations

from datetime import date
from pathlib import Path

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field, field_validator


class LLMConfig(BaseModel):
    provider: str = "gemini"
    model: str
    temperature: float = 0.1


class EmbeddingsConfig(BaseModel):
    model: str


class RerankerConfig(BaseModel):
    model: str
    enabled: bool = True


class RetrievalConfig(BaseModel):
    dense_k: int = 20
    sparse_k: int = 20
    rrf_k: int = 60
    final_k: int = 8


class VerifierConfig(BaseModel):
    nli_model: str
    threshold: float = Field(ge=0.0, le=1.0)
    max_regen: int = 2


class TemporalConfig(BaseModel):
    cutoffs: dict[str, date]


class TranslateConfig(BaseModel):
    engine: str = "indictrans2"
    fallback_llm: bool = True


class VectorStoreConfig(BaseModel):
    backend: str = "lancedb"
    path: Path = Path("data/processed/lancedb")


class UIConfig(BaseModel):
    page_title: str = "Kautilya"


class Settings(BaseModel):
    llm: LLMConfig
    embeddings: EmbeddingsConfig
    reranker: RerankerConfig
    retrieval: RetrievalConfig
    verifier: VerifierConfig
    temporal: TemporalConfig
    languages: list[str]
    translate: TranslateConfig
    vector_store: VectorStoreConfig
    ui: UIConfig

    @field_validator("languages")
    @classmethod
    def _has_english(cls, v: list[str]) -> list[str]:
        if "en" not in v:
            raise ValueError("language list must contain 'en'")
        return v


DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "settings.yaml"


def load_settings(path: Path | None = None) -> Settings:
    load_dotenv()
    cfg_path = path or DEFAULT_CONFIG_PATH
    with open(cfg_path, encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)
    return Settings.model_validate(raw)
