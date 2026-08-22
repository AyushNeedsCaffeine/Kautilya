# MASTER_PROMPT.md — Build Prompt for Project Kautilya

> **How to use this file:** Paste the block below into your AI coding agent (opencode,
> Claude Code, Cursor, etc.) when starting the project — or paste a single PHASE section
> at each build session. Keep `PROJECT_PLAN.md` and `ARCHITECTURE.md` in the repo; the
> agent can re-read them anytime.

---

## THE PROMPT (copy everything below this line)

You are my senior AI engineer building **"Kautilya"**, a publishable, student-level Legal
RAG system over Indian law. Work inside the current repo. Read `PROJECT_PLAN.md`,
`ARCHITECTURE.md`, and `MASTER_PROMPT.md` before writing any code, and follow them exactly
when they conflict with your defaults.

### What we are building

A RAG pipeline over 6 Indian legal domains — BNS 2023 + IPC 1860, BNSS 2023 + CrPC 1973,
BSA 2023 + Evidence Act 1872, Constitution of India, the 4 Labour Codes (+ top ~10 repealed
labour laws), Income-tax Act 1961/2025, plus ~150 curated landmark Supreme Court judgments —
served through Streamlit, with three non-negotiable USPs:

1. **USP-1 Time-Aware Legal Intelligence** — extract an optional incident date from the
   query; route to the legally applicable regime per domain:
   criminal < 2024-07-01 → IPC/CrPC/Evidence Act else BNS/BNSS/BSA;
   labour < 2025-11-21 → repealed acts else Labour Codes;
   tax < 2026-04-01 → IT Act 1961 else IT Act 2025.
   Surface old↔new equivalences from mapping tables (`data/mappings/*.json`),
   e.g. "IPC s.302 ≈ BNS s.103".
2. **USP-2 Dual-Register Answers** — every answer in two registers from the SAME verified
   evidence: "Legal" (precise statutory language) and "Simple" (~grade 8 readability,
   measured with Flesch–Kincaid). Identical citations in both; Simple may never add claims.
3. **USP-3 Indic Multilingual Output** — accept queries and return explanations in
   en/hi/mr/bn/ta/te/gu/kn. Multilingual retrieval via BGE-M3; verification happens on the
   English canonical answer BEFORE IndicTrans2 translates only the Simple register;
   citations stay verbatim English.

Plus: claim-level NLI citation verification (refuse or regenerate ungrounded answers,
max 2 retries), hybrid retrieval (bm25s + Qdrant/LanceDB dense → RRF → bge-reranker-v2-m3),
section-aware legal chunking, pluggable LLM provider (Gemini Flash default / OpenAI /
Ollama via one config switch), KautilyaBench eval harness.

### Hard rules

1. Every factual/legal claim in any output must carry a citation to a retrieved span.
   If evidence is insufficient: refuse politely and show nearest relevant sources.
   NEVER invent section numbers, case names, dates, or quotes.
2. Always append the disclaimer: informational purposes, not legal advice.
3. All data files under `data/raw/` are gitignored; never commit API keys (`.env` is
   gitignored; ship `.env.example`).
4. Canonical schema (pydantic models, shared everywhere):
   `{id, domain, act, act_short, regime(new|old|current), effective_from, effective_to,
   repeals, chapter, chapter_title, section_no, title, text, provisos[], illustrations[],
   cross_refs[], mapped_old[{id, equivalence}], lang, source_url, hash}`.
   Judgment chunks add: court, bench, judges, petitioner, respondent, citation,
   decision_date, disposition, case_stage(facts|issues|reasoning|held).
5. LangGraph node contracts are fixed (see ARCHITECTURE.md §4): pure functions over a
   typed `KautilyaState`; no hidden globals; every node logs stage latency.
6. Python 3.11, type hints everywhere, pydantic v2 for schemas, ruff + pytest clean.
   No comments unless something is genuinely non-obvious. No TODOs left in committed code.
7. Config-driven: models, k-values, thresholds, regime cutoff dates, language list all live
   in `config/settings.yaml`. Zero hardcoded model names in code.
8. Work phase by phase (below). After each phase: run its acceptance test, print results,
   stop, and wait for my go-ahead. Do not skip ahead.

### Phase order & acceptance criteria

**P0 Scaffold** — repo layout per PROJECT_PLAN §11, pyproject, config loader, logging,
pytest skeleton. ✅ `pip install -e . && pytest && kautilya --help` green.

**P1 Data engineering** — downloader (India Code PDFs, AWS SC judgments S3 sample,
respecting robots.txt + rate limits), pymupdf text extraction, parsers emitting canonical
JSON for ALL corpora, pydantic validation script, mapping-table builder seeded from MHA/PRS
comparison charts, bench v0 (≥60 QA pairs). ✅ ≥99% target sections parsed & validated;
mapping tables cover all IPC headline offences; `python -m kautilya.ingestion.validate`
passes.

**P2 Indexing + baseline** — legal_chunker (Act→Chapter→Section→proviso-aware; provisos &
illustrations attach to their section; judgment chunks by case_stage), BM25 index, vector
index with metadata filters (domain/regime/effective window), naive flat RAG baseline +
minimal Streamlit chat. ✅ baseline Hit@5 printed; query round-trip < 8 s (API mode).

**P3 USP features** — QueryAnalyzer (LLM-structured-output: domains, entities, normalized
incident_date incl. relative-date resolution, input language), TemporalResolver (cutoff
logic + mapping lookup + regime-filter injection into retriever), hybrid retriever + rerank,
dual-register Synthesizer, NLI Verifier loop (mDeBERTa XNLI; regenerate on unsupported
claims, refuse after 2 fails), Translator (IndicTrans2 with LLM-translation fallback flag),
language detection. ✅ demo script `scripts/demo_usps.py` exercises all three USPs end to
end; verifier catches 10 seeded wrong-citation tests.

**P4 Evaluation** — KautilyaBench v1 (150 pairs: 100 general / 30 temporal / 20
cross-domain; gold section labels), harness computing Hit@k, MRR, citation precision/recall,
NLI faithfulness, Flesch–Kincaid grades, temporal routing accuracy, p50/p95 latency;
ablation matrix runner (chunking × retrieval × regime-filter × verifier) writing markdown
tables to `reports/`. ✅ targets met: Hit@5 ≥ 0.85, citation precision ≥ 0.90, temporal acc
≥ 0.95, simple-register grade ≤ 10; tables generated.

**P5 Polish** — full Streamlit UI (chat, language selector, Legal/Simple toggle, incident
date picker, expandable source cards with highlighted spans, disclaimer banner), README,
demo video script, IEEE paper skeleton in `paper/`. ✅ fresh-clone quickstart works from
README alone.

### When I say a phase is approved
Update PROJECT_PLAN checklist, commit with message `phase(N): summary`, then proceed.

### Start now with Phase 0. Before coding, reply with: your understanding of the 3 USPs
in one line each, and any blocking questions.

---

## PHASE KICK-OFF SUB-PROMPTS (optional, one per session)

**P1:** "Execute Phase 1 of MASTER_PROMPT.md. Start with the BNS parser end-to-end
(download → parse → validate → JSON shard), get it perfect, then generalize to the other
acts. Show me 3 parsed sections including one with a proviso."

**P3:** "Implement the TemporalResolver first (pure function + unit tests with edge cases:
no date given → ask user; ambiguous date → current law + note). Then wire it into the
graph. Show me the answer difference for 'punishment for murder' vs 'punishment for murder
for an incident in March 2024'."

**P4:** "Build the eval harness before extending the bench. It must run offline-cached LLM
calls so ablations don't re-bill. Generate reports/ablation.md."

---

## ANTI-PATTERNS TO REJECT IN CODE REVIEWS

- Fixed-size chunking of statutes (destroys proviso context)
- One flat index for everything (kills USP-1 filtering)
- Translating BEFORE verification (verifier must see English canonical)
- LLM-as-judge as the ONLY faithfulness metric (pair it with NLI)
- Any answer path that can emit an uncited claim
