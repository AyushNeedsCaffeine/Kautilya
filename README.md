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
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env          # add your GEMINI_API_KEY
pytest
kautilya --help
```

## Status

| Phase | Scope | State |
|---|---|---|
| 0 | Scaffold, config, CLI | ✅ |
| 1 | Ingestion, parsing, mapping tables | ⬜ |
| 2 | Indexing + baseline RAG | ⬜ |
| 3 | USP features (temporal / dual-register / multilingual) | ⬜ |
| 4 | KautilyaBench + evaluation | ⬜ |
| 5 | UI polish + paper | ⬜ |

*Informational purposes only — not legal advice.*
