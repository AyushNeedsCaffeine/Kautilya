from __future__ import annotations

import hashlib
from datetime import date

from pydantic import BaseModel, Field


class Equivalence(BaseModel):
    old_id: str
    equivalence: str = "uncertain"
    note: str = ""


class Provision(BaseModel):
    id: str
    domain: str
    act: str
    act_short: str
    regime: str = Field(pattern="^(new|old|current)$")
    effective_from: date
    effective_to: date | None = None
    repeals: str | None = None
    chapter: str | None = None
    chapter_title: str | None = None
    section_no: str
    title: str | None = None
    text: str
    provisos: list[str] = []
    illustrations: list[str] = []
    cross_refs: list[str] = []
    mapped_old: list[Equivalence] = []
    lang: str = "en"
    source_url: str | None = None
    hash: str = ""

    def model_post_init(self, __context) -> None:
        if not self.hash:
            self.hash = hashlib.sha256(self.text.encode()).hexdigest()[:16]


class BenchQA(BaseModel):
    id: str
    question: str
    answer_legal: str
    answer_simple: str = ""
    gold_citations: list[str]
    domains: list[str]
    temporal: bool = False
    incident_date: date | None = None
    language: str = "en"
