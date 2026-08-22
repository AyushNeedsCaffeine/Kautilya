# Project Kautilya — Time-Aware, Multilingual Legal RAG for Indian Law

> **Tagline:** *"Ask the law in your language, as it stood on your date."*
>
> A Retrieval-Augmented Generation system over Indian law (BNS, BNSS, BSA, Constitution of India,
> Labour Codes, Income-tax Acts + landmark Supreme Court judgments) with three defensible USPs:
> temporal regime routing, dual-register answers, and Indic multilingual explanations.

---

## 1. Problem Statement

India's legal landscape changed more between 2023 and 2026 than in the previous 60 years:

| Transition | Effective | Old → New |
|---|---|---|
| Criminal substantive law | 1 Jul 2024 | IPC 1860 → **BNS 2023** (358 sections) |
| Criminal procedure | 1 Jul 2024 | CrPC 1973 → **BNSS 2023** (531 sections) |
| Evidence law | 1 Jul 2024 | Evidence Act 1872 → **BSA 2023** (170 sections) |
| Labour law | 21 Nov 2025 | 29 laws → **4 Labour Codes** |
| Direct tax | 1 Apr 2026 | Income-tax Act 1961 → **Income-tax Act 2025** |

Every existing legal-AI system indexes a *single snapshot* of the law. None can answer
*"I was cheated of ₹2 lakh in March 2024 — which section applies?"* correctly, because the
answer is IPC §420 (not BNS §318(4)), determined purely by the incident date. Meanwhile,
ordinary citizens cannot parse statutory language at all, and most cannot read English.

**Kautilya** solves all three gaps: correct law-as-of-date retrieval, plain-language
explanations, and output in major Indian languages — with every claim citation-verified.

## 2. Novelty Positioning (why this is publishable)

The space (as of Aug 2026) contains: NyayaAI (multi-agent assistant), HyRAG (KG+RAG),
Falkor-IRAC (graph-constrained IRAC verification), IndLaw-QA (fine-tuned LLM+RAG), and ≥3
BNS/BNSS-only RAG chatbots. **None handles temporal validity, answer simplification, or
Indic multilingualism together with verified citations.** A generic "legal RAG" is no longer
novel; these three pillars are.

### The 3 USPs

#### USP-1 · Time-Aware Legal Intelligence
- Query Analyzer extracts an optional **incident/event date** from natural language.
- Temporal Resolver selects the legally applicable regime per domain:
  - criminal: `< 1 Jul 2024 → IPC/CrPC/Evidence Act`, else `BNS/BNSS/BSA`
  - labour: `< 21 Nov 2025 → repealed acts`, else `Labour Codes`
  - tax: `< 1 Apr 2026 → IT Act 1961`, else `IT Act 2025`
- Answers cite the correct code **and surface the equivalence**
  (`IPC s.302 ≈ BNS s.103`) from curated mapping tables.
- Constitutional anchor: Art. 20(1) prohibits ex-post-facto criminal liability — this makes
  date-routing a *legal requirement*, not a convenience feature. Strong paper narrative.
- **Metric:** temporal routing accuracy on a dedicated benchmark subset (target ≥ 95%).

#### USP-2 · Dual-Register Answers ("Legal ⇄ Simple")
- Every answer is produced twice from the same verified evidence:
  - **Legal register:** precise statutory language, exact terminology, full citations.
  - **Simple register:** same meaning rewritten at ~grade 8 reading level, analogies allowed,
    zero invented facts.
- Citations are identical across both registers; the Simple register never introduces claims
  absent from the Legal one (enforced by the verifier).
- **Metric:** Flesch–Kincaid grade drop (e.g., 19 → ≤10) while citation fidelity stays ≥ 0.9.
  This yields an original evaluable contribution: *simplification without grounding loss*.

#### USP-3 · Indic Multilingual Output
- Input: any of 7 languages (English, Hindi, Marathi, Bengali, Tamil, Telugu, Gujarati,
  Kannada). Multilingual embeddings (BGE-M3) retrieve the right English provision even when
  the query is in Hindi/Tamil/etc.
- Pipeline order is fixed: **verify in English first → then translate the Simple register**
  via IndicTrans2 (AI4Bharat, open-source, 22 scheduled languages).
- Citations always remain verbatim English (legally authoritative); only explanation prose
  is translated.
- **Metric:** language coverage × translation spot-check quality (human rubric or QE score).

### Supporting contributions (paper material, not headline claims)
- Claim-level **NLI entailment verification** (refuse/regenerate unsupported answers).
- Hybrid retrieval ablation: BM25 vs dense vs hybrid vs hybrid+rerank.
- **Section-aware chunking ablation**: proviso/clause-preserving chunks vs naive 512-token
  windows — quantified evidence for a known open problem (flagged in 2025 legal-RAG surveys).
- **KautilyaBench**: released QA benchmark (~150 pairs, incl. 30 temporal + 20 cross-domain).

## 3. Corpus Scope (curated core)

| # | Domain | In force now | Predecessor (temporal mapping) | Sections |
|---|--------|--------------|-------------------------------|----------|
| 1 | Criminal – substantive | BNS 2023 | IPC 1860 | 358 / 511 |
| 2 | Criminal – procedure | BNSS 2023 | CrPC 1973 | 531 / 484 |
| 3 | Criminal – evidence | BSA 2023 | Indian Evidence Act 1872 | 170 / 167 |
| 4 | Constitutional | Constitution of India (as amended to 106th) | — | ~470 arts. |
| 5 | Labour | Code on Wages 2019; Industrial Relations Code 2020; Social Security Code 2020; OSH Code 2020 | Payment of Wages Act, ID Act 1947, Factories Act 1948, ESI/EPF Acts, Minimum Wages Act … (top ~10) | varies |
| 6 | Tax | Income-tax Act 2025 (+ key Rules) | Income-tax Act 1961 (+ key Rules) | ~536 / 298 |
| 7 | Case law | ~150 landmark SC judgments spanning all domains | — | full texts |

### Data sources (all free/open)

| Source | What | License |
|---|---|---|
| indiacode.nic.in | Official PDFs of all central acts | Govt publication (free access) |
| AWS Open Data `s3://indian-supreme-court-judgments` | SC judgments 1950–present, PDF+metadata | CC-BY-4.0 |
| HF `vaquill/open-india-law` | Pre-parsed section-aware legislation (fallback / parser validation) | CC-BY-4.0 |
| Zenodo record 5088102 | 858 structured Central Acts JSON (parser reference) | open |
| MHA / PRS comparison charts | IPC↔BNS, old-labour↔Codes correspondence | free access |

### Mapping tables (build ourselves = highest-value data asset)
- `ipc_to_bns.json` — every IPC section → BNS equivalent(s) + notes on modifications
- `crpc_to_bnss.json`, `evidence_to_bsa.json`
- `old_labour_to_codes.json` — repealed act → absorbing Code + section
- `ita1961_to_ita2025.json` — chapter-level mapping minimum
Format: `{old_id, new_id, equivalence: "identical|renumbered|modified|split|omitted", note}`

## 4. Canonical Data Schema

Every parsed provision becomes one JSON object:

```json
{
  "id": "BNS_2023_s103",
  "domain": "criminal_substantive",
  "act": "Bharatiya Nyaya Sanhita, 2023",
  "act_short": "BNS",
  "regime": "new",
  "effective_from": "2024-07-01",
  "effective_to": null,
  "repeals": "IPC_1860",
  "chapter": "II",
  "chapter_title": "Of Punishments",
  "section_no": "103",
  "title": "Punishment for murder",
  "text": "...full section text...",
  "provisos": ["...proviso text..."],
  "illustrations": ["..."],
  "cross_refs": ["BNS_s101", "BNSS_s193"],
  "mapped_old": [{"id": "IPC_1860_s302", "equivalence": "modified"}],
  "lang": "en",
  "source_url": "https://...",
  "hash": "sha256..."
}
```

SC judgment chunks add: `court, bench, judges, petitioner, respondent, citation,
decision_date, disposition, case_stage(facts/issues/reasoning/held)`.

## 5. Architecture Summary

Full detail with diagrams & contracts: see **ARCHITECTURE.md**.

```
Streamlit UI ──► LangGraph pipeline
   1 QueryAnalyzer     : domain(s), entities, incident_date, input_lang
   2 TemporalResolver  : regime selection + mapping-table lookup
   3 HybridRetriever   : BM25 + BGE-M3 dense → RRF → cross-encoder rerank
   4 Synthesizer       : pluggable LLM → Legal register + Simple register, cited
   5 Verifier          : NLI entailment per claim → pass / regenerate / refuse
   6 Translator        : IndicTrans2 on Simple register only; citations untouched
```

## 6. Tech Stack

| Layer | Choice | Why |
|---|---|---|
| Language | Python 3.11 | ecosystem |
| Orchestration | LangGraph | explicit state machine, checkpointing, you know it |
| LLM abstraction | LangChain provider interface | Gemini Flash default, OpenAI/Ollama swappable via config |
| Embeddings | BAAI/bge-m3 | multilingual (query in Hindi → English statute), 8k ctx |
| Sparse | bm25s | fast pure-python BM25 |
| Vector store | Qdrant (local docker) or LanceDB (embedded) | metadata filters for regime/domain |
| Reranker | bge-reranker-v2-m3 | strong multilingual cross-encoder |
| NLI verifier | mDeBERTa-v3 XNLI | runs on CPU, multilingual fallback checks |
| Translation | AI4Bharat IndicTrans2 | open-source, 22 languages, citable |
| UI | Streamlit | fastest demo path, already familiar |
| Eval | pytest + custom harness + LLM-as-judge | reproducible numbers for paper |

## 7. Roadmap (6 weeks, aggressive)

### Phase 0 — Scaffold (2 days)
Repo layout, `pyproject.toml`, config system (`config/settings.yaml`), `.env.example`,
CI stub, logger, pytest skeleton.
**Accept:** `pip install -e . && pytest` green; `kautilya --help` works.

### Phase 1 — Data Engineering (wk 1–2) ⚠️ highest-risk phase
Downloaders (respect robots.txt, rate-limit), PDF→text (pymupdf), parsers producing canonical
schema for all corpora, validation (pydantic), mapping tables built from MHA/PRS charts +
manual review pass, KautilyaBench v0 (~60 pairs).
**Accept:** ≥99% of target sections parsed; schema validator passes; mapping tables cover
100% of IPC parts I–XXIII headline offences; bench v0 committed.

### Phase 2 — Indexing + Baseline (wk 2–3)
Section-aware chunker, BM25 + Qdrant/LanceDB indexing with metadata filters, naive RAG
(single flat index, no rerank) as the **ablation baseline**, Streamlit chat v0.
**Accept:** baseline hit@5 recorded; end-to-end query < 8 s on API mode.

### Phase 3 — USP Features (wk 3–4)
QueryAnalyzer node (date/entity extraction incl. relative dates like "last Diwali"),
TemporalResolver + mapping surfacing, hybrid retriever + rerank, dual-register synthesis,
NLI verifier loop (max 2 regenerations → refuse-with-sources), IndicTrans2 translator,
language detection.
**Accept:** all three USPs demonstrable in UI; verifier catches seeded false-citation tests.

### Phase 4 — Evaluation (wk 4–5)
KautilyaBench v1 (150 pairs: 100 general, 30 temporal, 20 cross-domain), harness computing
Hit@k/MRR/citation-P&R/faithfulness/readability/temporal accuracy, ablation matrix
(chunking × retrieval × verifier), results tables auto-generated to `/reports`.
**Accept:** targets met — Hit@5 ≥ 0.85, citation precision ≥ 0.90, temporal acc ≥ 0.95;
ablation table generated.

### Phase 5 — Polish + Publication (wk 5–6)
UI polish (language selector, Legal/Simple toggle, date picker, source cards, disclaimers),
README + docs, demo script/video, IEEE-format paper draft, arXiv preprint, copyright filing.
**Accept:** paper draft complete; repo public-ready; 5-min demo recording.

## 8. Evaluation Protocol

| Metric | Tool | Target |
|---|---|---|
| Hit@5 / MRR (retrieval) | gold-section labels in bench | ≥0.85 / ≥0.70 |
| Citation precision/recall | regex-extract cites → check against retrieved spans | ≥0.90 P |
| Faithfulness | NLI entailment of each claim vs its cited span | ≥0.90 supported |
| Temporal routing accuracy | temporal subset gold labels | ≥0.95 |
| Readability (simple register) | textstat Flesch–Kincaid grade | ≤10 (from ~19) |
| Answer quality | LLM-as-judge 1–10 (correctness/completeness/relevance/reasoning) | report |
| Latency | p50/p95 per stage | p50 < 12 s |

Ablation matrix (each cell = full bench run):
1. chunking: naive-512 vs section-aware
2. retrieval: BM25-only / dense-only / hybrid / hybrid+rerank
3. regime filtering: on/off (shows USP-1 value directly)
4. verifier: on/off

## 9. Risks & Mitigations

| Risk | Mitigation |
|---|---|
| PDF parsing hell (scanned/odd layouts) | pymupdf + Vaquill/Zenodo pre-parsed fallbacks; manual fix queue |
| Mapping-table errors (legal accuracy!) | two-source verification + manual review; mark uncertain entries `equivalence:"uncertain"` |
| LLM hallucinating sections | verifier refuses ungrounded answers; system prompt hard-constrained; disclaimer everywhere |
| Scope creep into lakhs of judgments | hard cap: curated list frozen at Phase 1 |
| IndicTrans2 setup friction | fallback: direct LLM translation mode behind config flag (documented in paper as variant) |
| API cost blowup | Gemini Flash free tier for dev; batch eval caching; Ollama fallback |
| Timeline slip | Phases 1→2 are the critical path; USP-2/3 have documented fallback modes |

## 10. IP & Publication Strategy (realistic, student-level)

1. **Paper first (strongest asset):** IEEE-format conference paper — e.g., regional IEEE
   conferences / ICCCS / COMSNETS workshops, or arXiv preprint immediately for timestamp.
   Title sketch: *"Kautilya: Date-Aware, Citation-Verified RAG over India's Transitional
   Legal Codes with Plain-Language Multilingual Explanations."*
2. **Copyright registration** of code (₹500 govt fee, online, 2–4 months) — real protection.
3. **Provisional patent (optional):** file within 12 months of disclosure, framed as a
   *system claim* (temporal resolver + verifier + translator as technical components).
   Honest caveat: software per se is excluded under Patents Act §3(k); success odds are low,
   provisional filing is cheap and preserves priority if you pursue it. Do not delay the
   paper for it.
4. **Benchmark release** on Hugging Face (KautilyaBench, CC-BY-4.0) — citable artifact.

## 11. Repository Layout

```
Kautilya/
├── PROJECT_PLAN.md            ← this file
├── MASTER_PROMPT.md           ← prompt spec for AI coding agents
├── ARCHITECTURE.md            ← diagrams + component contracts
├── README.md
├── pyproject.toml
├── .env.example               ← API keys template (never commit real keys)
├── config/settings.yaml       ← models, k-values, thresholds, language list
├── data/
│   ├── raw/                   ← downloaded PDFs (gitignored)
│   ├── processed/             ← canonical JSON shards
│   ├── mappings/              ← ipc_to_bns.json etc.
│   └── bench/                 ← kautilyabench_v1.jsonl
├── src/kautilya/
│   ├── ingestion/             download.py parse_pdf normalize validate
│   ├── chunking/              legal_chunker.py
│   ├── indexing/              build_index.py search.py (bm25+dense+rrf+rerank)
│   ├── graph/                 state.py nodes/{analyzer,resolver,retriever,
│   │                          synthesizer,verifier,translator}.py pipeline.py
│   ├── llm/                   providers.py (gemini/openai/ollama factory)
│   ├── verify/                nli.py citation_check.py
│   ├── translate/             indictrans2.py detect.py
│   ├── ui/app.py              streamlit
│   └── eval/                  metrics.py run_bench.py judge.py
├── scripts/                   one-command entry points
├── tests/
└── reports/                   auto-generated eval tables (for the paper)
```

## 12. Non-Negotiable Guardrails

1. Every factual/legal claim carries a citation to a retrieved span — no exceptions.
2. Unverifiable answers are refused with pointers to relevant sources (never guessed).
3. Every response ends with: informational-not-legal-advice disclaimer.
4. No personal-data logging of queries by default.
5. Mapping tables ship with confidence labels; low-confidence mappings are surfaced as such.
