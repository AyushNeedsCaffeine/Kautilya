from __future__ import annotations

from datetime import date

import pytest

from kautilya.config import Settings, load_settings


@pytest.fixture
def settings() -> Settings:
    return load_settings()


def test_loads_repo_settings(settings: Settings) -> None:
    assert settings.llm.provider == "gemini"
    assert settings.retrieval.final_k >= 1
    assert settings.verifier.max_regen >= 1


def test_temporal_cutoffs_parse_as_dates(settings: Settings) -> None:
    cutoffs = settings.temporal.cutoffs

    assert cutoffs["criminal_substantive"] == date(2024, 7, 1)
    assert cutoffs["labour"] == date(2025, 11, 21)
    assert cutoffs["tax"] == date(2026, 4, 1)


def test_languages_include_english_and_hindi(settings: Settings) -> None:
    langs = settings.languages

    assert "en" in langs
    assert "hi" in langs
