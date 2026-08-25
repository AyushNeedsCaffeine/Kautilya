# Kautilya

> *Ask the law in your language, as it stood on your date.*

Time-aware, citation-verified, multilingual legal RAG over Indian law:
**BNS · BNSS · BSA · Constitution of India · Labour Codes · Income-tax Acts + landmark Supreme Court judgments.**

## Why it is different (USPs)

1. **Time-Aware Legal Intelligence** — give an incident date; the system routes to the law
   actually in force then (IPC↔BNS, CrPC↔BNSS, Evidence Act↔BSA, old labour laws↔Codes)
   and surfaces old↔new section equivalences.
2. **Dual-Register Answers** — every answer in precise "Legal" mode and plain-language
   "Simple" mode (~grade 8 readability), same verified citations.
3. **Indic Multilingual Output** — ask and get explained in English, Hindi, Marathi,
   Bengali, Tamil, Telugu, Gujarati, Kannada. Citations always stay verbatim.

Every claim is checked by an NLI verifier against retrieved statutory text before it
reaches you; ungrounded answers are refused, never guessed.

## Documentation

| File | Contents |
|---|---|
| [PROJECT_PLAN.md](PROJECT_PLAN.md) | scope, USPs, roadmap, evaluation, IP strategy |
| [ARCHITECTURE.md](ARCHITECTURE.md) | diagrams, LangGraph contracts, index design |
| [MASTER_PROMPT.md](MASTER_PROMPT.md) | build spec used with AI coding agents |

## Quickstart (Phase 0)

```bash
python3 -m venv Kautilya-venv && source Kautilya-venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env          # add your GEMINI_API_KEY
pytest
kautilya --help
```

## Usage

```bash
kautilya ask "March 2024 mein cheating hui thi - kaunsa section lagega?"
# -> routes to the OLD regime (pre-2024-07-01), answers from IPC ss.415-420,
#    both registers, inline citations, old<->new equivalence notes

kautilya ask --date 2025-06-01 "punishment for murder"     # explicit incident date
kautilya ask --lang hi "what is section 420?"               # Hindi translation
kautilya ask --legal-only --json "65B certificate admissibility"
```

Pipeline: `QueryAnalyzer -> TemporalResolver -> HybridRetriever (dense+BM25+RRF
-> GPU reranker) -> Synthesizer (dual-register)`. Past-tense questions without
a date are asked back for one. Answers cite only retrieved chunks; empty
retrieval refuses instead of guessing.

## Status

| Phase | Scope | State |
|---|---|---|
| 0 | Scaffold, config, CLI | ✅ |
| 1a–1e | Ingestion, parsing, temporal mapping tables | ✅ |
| 2a–2b | Section-aware chunker + hybrid index (LanceDB + BM25) | ✅ |
| 3a–3d | Full pipeline: analyzer · resolver · retriever · synthesizer · `ask` CLI | ✅ |
| 4a | Verifier: citation-existence gate + mDeBERTa NLI entailment loop | ✅ |
| 4b | KautilyaBench v1 (115 QA pairs) + `eval` harness — retrieval stage | ✅ |
| 4c | Full-stage bench run + tuning after human review of golds | ⬜ |
| 5a | IndicTrans2 multilingual translation (lazy-load, VRAM eviction) | ✅ |
| 5b | Streamlit chat UI | ⬜ |
| 5c | Paper + final polish | ⬜ |

*Informational purposes only — not legal advice.*

### KautilyaBench v1 (retrieval stage, n=115)
`Kautilya-venv/bin/kautilya eval --bench data/bench/draft.jsonl --stage retrieval`

| Metric | Score |
|---|---|
| Hit@5 (core subset) | 0.785 |
| MRR@8 (core) | 0.674 |
| Temporal routing accuracy | 0.991 |
| ask-date route accuracy | 0.974 |
| Section-lookup Hit@5 (`auto_lookup`) | 0.967 |

Highlights: exact `(act, section)` query pins are boosted ahead of fusion;
regime routing is near-perfect. Known weak spots: romanised-Hindi lexical
gap (Hit@5 0.25 — LLM reformulation lands with the full stage) and labour-code
title variance (0.6).

### Verification (phase 4a)
Every legal-register sentence carrying a `[chunk_id]` citation is checked by
an XNLI model (`MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7`)
against the cited corpus text (max over retrieved context × framing-stripped
phrasings). Unsupported claims trigger up to 2 regenerations with verifier
feedback, then refusal. Invented citations are rejected outright. Skip with
`--no-verify`.
