from __future__ import annotations

from datetime import date

import polars as pl
import pytest

from kautilya.ingestion.normalize import normalize_act
from kautilya.ingestion.sources import ACT_REGISTRY


@pytest.fixture
def ipc_df() -> pl.DataFrame:
    return pl.DataFrame(
        [
            {
                "act_id": "IND_REP_659_1860",
                "chunk_id": "IND_REP_659_1860_s302",
                "title": "The Indian Penal Code, 45 of 1860 (Rep., Act 45 of 2023",
                "chapter": "XXX",
                "section_number": "302",
                "section_title": "Punishment for murder",
                "text": (
                    "Act: The Indian Penal Code, 1860 (1860) | India | Central | Repealed\n"
                    "Chapter XXX: ## OF OFFENCES AFFECTING LIFE | Section 302: Punishment for murder\n"
                    "**302. Punishment for murder.—** Whoever commits murder shall be punished "
                    "with death, or imprisonment for life, and shall also be liable to fine."
                ),
                "source_url": "https://example.test/ipc",
            },
            {
                "act_id": "IND_REP_659_1860",
                "chunk_id": "IND_REP_659_1860_s84_p0",
                "title": None,
                "chapter": "IV",
                "section_number": "84",
                "section_title": "Act of a person of unsound mind",
                "text": (
                    "**84. Act of a person of unsound mind.—** Nothing is an offence which is "
                    "done by a person who, at the time of doing it, by reason of unsoundness "
                    "of mind, is incapable of knowing the nature of the act. Provided that "
                    "the burden of proof lies on the accused."
                ),
                "source_url": "https://example.test/ipc",
            },
        ]
    )


def test_normalize_merges_and_cleans(ipc_df: pl.DataFrame) -> None:
    source = ACT_REGISTRY["IND_REP_659_1860"]
    provisions = {p.section_no: p for p in normalize_act(ipc_df, source)}

    assert set(provisions) == {"302", "84"}

    murder = provisions["302"]
    assert murder.id == "IPC_s302"
    assert murder.regime == "old"
    assert murder.effective_from == date(1862, 1, 1)
    assert murder.chapter == "XXX"
    assert murder.title == "Punishment for murder"
    assert "##" not in murder.text and "**" not in murder.text and "Act:" not in murder.text
    assert "Whoever commits murder" in murder.text
    assert murder.hash

    unsound = provisions["84"]
    assert len(unsound.provisos) == 1
    assert unsound.provisos[0].startswith("Provided that")
    assert "cross_refs" in unsound.model_fields


def test_internal_refs_detected(ipc_df: pl.DataFrame) -> None:
    source = ACT_REGISTRY["IND_REP_659_1860"]
    provisions = {
        p.section_no: p
        for p in normalize_act(ipc_df.with_columns(
            pl.col("text").str.replace(
                "nature of the act", "nature of the act under section 52"
            )
        ), source)
    }

    assert "IPC_s52" in provisions["84"].cross_refs
