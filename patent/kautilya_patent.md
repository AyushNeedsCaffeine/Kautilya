# PATENT DRAFT — PROVISIONAL SPECIFICATION

## Title

**A SYSTEM AND METHOD FOR TIME-AWARE, VERIFIED, MULTILINGUAL LEGAL QUESTION-ANSWERING WITH DUAL-REGISTER ANSWERS**

## Field of the Invention

The present invention relates generally to computational question-answering and
information retrieval, and more particularly to a retrieval-augmented-generation
(RAG) system for legal text that (i) selects the legally applicable code based on
an incident date, (ii) produces dual-register answers in legal and plain language
from the same verified evidence, (iii) verifies each factual claim against
retrieved statutory text, and (iv) renders the verified plain-language answer in
multiple Indic languages. The invention has particular, but not exclusive,
application to Indian law following the 2024–2026 replacement of major national
codes (IPC → BNS, CrPC → BNSS, IEA → BSA, IT Act 1961 → IT Act 2025).

## Background of the Invention

Legal texts exist in versions that are active at different times. When national
codes are replaced (a "regime transition"), a legal question about an incident
that occurred before the transition date must be answered under the *old* code,
regardless of which code is current at the time the question is asked.

Constitutional constraints make this a hard requirement: Article 20(1) of the
Constitution of India prohibits prosecution/conviction under a law not in force
at the time of the act, and prohibits punishment greater than that prescribed at
the time of the act. A question-answering system that answers using whichever
code is indexed (invariably the newest snapshot) will mis-answer date-sensitive
questions.

Conventional legal RAG systems suffer from several defects:

- they index a single snapshot of the law and cannot route to the version in
  force on a given incident date;
- statutory language is inaccessible to lay users, yet no plain-language
  rendering is produced, or the plain-language rendering is generated without
  fidelity to the cited legal basis (introducing hallucinated claims);
- answers are confined to a single language, excluding the majority of Indian
  citizens who are more comfortable in an Indian language;
- generated citations are not verifiable against the retrieved sources, allowing
  fabricated citations to pass.

Accordingly, there is a need for a system that deterministically selects the
applicable legal regime from an incident date, produces legally precise and
plain-language answers that share the same citations, verifies every cited claim
before presenting it, and translates only the verified plain-language register
into Indian languages while preserving citations verbatim.

## Summary of the Invention

According to a first aspect, the invention provides a computer-implemented
method for time-aware, verified, multilingual legal question-answering,
comprising:

- receiving a natural-language legal query and an incident date associated with a
  legal question;
- detecting a legal domain of the query (e.g., criminal substantive, criminal
  procedure, evidence, labour, tax, constitutional) and extracting entities and
  language signals from the query;
- deterministically routing each detected domain to a legal regime — an old
  regime, a new regime, or a current regime — using a pre-computed temporal
  cutoff (a data structure mapping each domain to its transition date);
- restricting retrieval of evidence chunks to chunks whose metadata indicates the
  routed regime, whereby only chunks of the legally applicable code are candidates
  for answer generation;
- generating, in a single synthesis step, a dual-register answer comprising (a) a
  legal-register answer in precise statutory language with inline citation
  markers referencing retrieved chunk identifiers, and (b) a plain-language
  answer restating the same claims without citation markers, both registers
  deriving from the same retrieved evidence;
- verifying the legal-register answer by (i) confirming each citation marker
  corresponds to a retrieved chunk, and (ii) scoring each cited sentence against
  the cited chunk text with a natural-language-inference (NLI) entailment model;
- when verification fails, regenerating the answer with the verifier's feedback
  injected, and refusing to answer (rather than guessing) if regeneration is
  exhausted; and
- when verification passes and an Indic output language is selected, translating
  only the plain-language answer into the selected language using a machine
  translation model, while preserving all citation markers (which remain in the
  legal-register answer in English).

The method gives users, in order: the correct code for the incident date; a
precise legal statement with verified citations; an accessible plain-language
statement of the same claim; and, optionally, that plain-language statement in
the user's Indian language.

Further aspects and embodiments are set out in the claims and the detailed
description below.

## Detailed Description

### 0. Glossary

- **Regime**: the version of the law applicable to a query, selected from
  *old*, *new*, *current*, and *mixed*. "Old" generally denotes pre-transition
  codes (e.g., IPC/CrPC/IEA, repealed Labour statutes, IT Act 1961); "new"
  denotes post-transition codes (BNS/BNSS/BSA, the four Labour Codes, IT Act
  2025); "current" denotes provisions continuously in force (COI, landmark
  judgments).
- **Chunk**: a unit of indexed statutory text; preferably one section/article
  with its provisos and illustrations attached, carrying a header of metadata
  (act, chapter, section, regime, effective window).
- **Dual-register answer**: a pair (legal register, simple register) generated
  from a single synthesis step over shared retrieved evidence.
- **Citation marker**: an inline reference of the form `[CHUNK_ID]` mapping to a
  retrieved chunk.
- **Regeneration loop**: a bounded retry in which verifier feedback is supplied
  to the generator.

### 1. Preferred Embodiment — System Overview

The invention is preferably realised as a state-machine (LangGraph-style)
pipeline of six functional nodes executed by a computing device, each node
consuming a shared typed state and returning partial updates. The nodes are:

1. **QueryAnalyzer** — receives the raw query; jointly performs language
   detection (Unicode script ranges, romanised-script cues), domain
   classification (keyword lexicons per domain), entity extraction (section
   numbers, act names), and incident-date extraction (ISO, day/month/year,
   month+year, year-only). When an LLM is available, the analysis is produced as
   a structured (JSON) output whose domain set is union-merged with keyword
   signals so a confident-but-wrong label cannot starve the retriever.
2. **TemporalResolver** — holds a table mapping (domain → transition date).
   Given the incident date and domain(s), returns the regime for each domain and
   a flag `ask_date` when the query is past-tense but no date is present.
   When an old↔new section equivalence table is available, the resolver loads a
   human-readable equivalence note (e.g., "IPC s.420 ≈ BNS s.318(4)") for
   surfacing.
3. **HybridRetriever** — a fusion of dense (BGE-M3) and sparse (BM25) retrieval
   with metadata prefiltering restricted to the routed regime's act allowlist,
   plus an optional section-hint boost that promotes chunks matching an exact
   act+section mention in the query. The corpus is stored in a single table with
   regime metadata columns enabling regime-filtered prefiltering (a "regime-gated
   retriever").
4. **Synthesizer** — generates, in one call, the JSON triple: legal-register
   answer with inline `[CHUNK_ID]` markers; plain-language answer with the same
   claims and FK-grade target; and the citation list. The synthesis prompt
   instructs the model to refuse (`"refused": true`) when sources are
   insufficient. Citations are validated against retrieved chunk IDs; only valid
   citations are retained.
5. **Verifier** — Gate 1 (citation existence): every citation marker must appear
   among retrieved chunks. Gate 2 (NLI entailment): each cited sentence is
   decomposed into hypothesis variants (original + scaffold-free rephrasings)
   and scored against the cited chunk text with an NLI entailment model taking
   the maximum probability across variants and paraphrases; claims below a
   threshold are flagged unsupported. On failure, the synthesizer regenerates
   with feedback, up to a retry bound; on exhaustion the system refuses with
   source pointers.
6. **Translator** — when a non-English output language is selected, translates
   only the verified plain-language register using IndicTrans2 (neural);
   citations remain in English and are preserved verbatim. Translation runs
   strictly *after* verification passes, so untranslated, unverified content is
   never surfaced. Indic↔Indic pivots through English.

### 2. Terminology of the routing map

Transition cutoffs (illustrative; stored as configuration):

- Criminal (substantive) / procedure / evidence: **1 July 2024** (IPC→BNS,
  CrPC→BNSS, IEA→BSA).
- Labour: **21 November 2025** (repealed statutes → Labour Codes).
- Tax: **1 April 2026** (IT Act 1961 → IT Act 2025).
- Constitutional / case law: always current.

Deterministic routing yields auditability: given the same inputs, the same
regime is always chosen; no model weight decides legal applicability.

### 3. Working Example

Query: *"What is the punishment for murder?"* with incident date **2024-03-15**.

1. **Analyze**: domain = criminal_substantive; date = 2024-03-15; language = en.
2. **Resolve**: since 2024-03-15 is before the 2024-07-01 cutoff, regime =
   **old**; act allowlist = {IPC, CrPC, IEA, SCJ, COI}. Equivalence note loaded:
   IPC s.300/302 ↔ BNS s.101/103.
3. **Retrieve**: regime-filtered search returns IPC s.302 (gold) and related
   sections; BNS s.103 (new regime) is excluded by the filter.
4. **Synthesize**: legal register: *"Whoever commits murder shall be punished
   with death or imprisonment for life and fine, and shall also be liable to
   fine [IPC_s302]."* Simple register: *"Murder can mean a sentence of death or
   jail for life, plus a fine."* Citations: [IPC_s302].
5. **Verify**: IPC_s302 present in retrieved set (gate 1 ✓); XNLI entails the
   sentence against s.302 text above threshold (gate 2 ✓).
6. **Translate** (requested language: Hindi): simple register rendered in
   Devanagari; legal register and `[IPC_s302]` remain in English.

Had the incident date been **2025-08-01** (after the cutoff), the same query
would be routed to the **new** regime, retrieve BNS s.103, and answer under
BNS with the equivalence note flipped ("BNS s.103 ≈ IPC s.302").

### 4. Advantages over the Prior Art

- Date-driven, deterministic regime selection (no hallucinated code choice,
  satisfies Article 20(1) concerns).
- Regime-gated retrieval bounds answer generation to legally admissible sources.
- Dual-register output shares one verified citation set — plain-language
  simplification cannot fabricate claims not already in the legal register.
- Verification is a hard gate: invented citations and unsupported claims trigger
  regeneration or refusal.
- Continuous, verbatim-citation multilingual output without translating the
  authoritative legal register.
- Small-footprint operation (4 GB GPU) via lazy loading and VRAM eviction of the
  translation and embedding models.

### 5. Variants and Extensions

- The NLI verifier may be replaced by a premise-selection reranker or an
  instruction-tuned verifier LLM.
- The translation model may be any neural MT supporting the target languages
  (e.g., mBART, IndicTrans/NMT).
- The regime-gating metadata may be generalised to jurisdiction/geo-gating for
  multi-jurisdiction corpora.
- The determinism of routing may be relaxed toward probabilistic regime
  selection where transition dates are uncertain, with human-in-the-loop
  confirmation.

## Claims

**Claim 1.** A computer-implemented method for time-aware legal
question-answering, the method comprising:

(a) receiving a natural-language legal query and an incident date associated
    with a question about an act or omission;
(b) analyzing the query to determine at least one legal domain, at least one
    entity, and a language;
(c) determining, from the incident date and a pre-computed temporal-cutoff map
    associating each legal domain with a regime-transition date, a legal regime
    applicable to each determined domain, selected from an old regime, a new
    regime, and a current regime;
(d) retrieving candidate evidence chunks from a corpus in which each chunk is
    tagged with a regime metadata value, wherein retrieval is restricted, by the
    regime metadata, to chunks whose tag matches the applicable legal regime;
(e) generating, from the retrieved chunks, a dual-register answer comprising a
    legal-register portion in statutory language with inline citation markers
    that reference retrieved chunk identifiers, and a plain-language portion
    restating the legal-register claim in simplified language without citation
    markers;
(f) verifying the dual-register answer by confirming that each inline citation
    marker corresponds to a retrieved chunk identifier and that each cited
    statement is entailed by the text of the corresponding retrieved chunk
    according to a natural-language-inference model; and
(g) outputting the dual-register answer only when verification passes, and
    otherwise regenerating the answer with verifier feedback or refusing to
    answer.

**Claim 2.** The method of claim 1, wherein determining the applicable legal
regime further comprises: when no incident date is derivable from the query but
the query refers to a past incident, returning a request-for-date signal, and
deferring retrieval until an incident date is supplied.

**Claim 3.** The method of claim 1, further comprising, for each determined
domain, loading an equivalence note that maps a section of the old regime to a
corresponding section of the new regime, and rendering said equivalence note as
part of the output answer.

**Claim 4.** The method of claim 1, wherein step (d) uses a reciprocal-rank
fusion of a dense vector retrieval ranked list and a sparse lexical retrieval
ranked list, the dense retrieval being performed with bilingual-embeddings dense
retrieval restricted by the regime metadata, and the sparse retrieval being
performed with BM25.

**Claim 5.** The method of claim 1, further comprising a readability-moderation
step in which a Flesch-Kincaid grade level of the plain-language portion is
computed, and when the grade level exceeds a threshold, the plain-language
portion is regenerated under an instruction to use shorter sentences and more
common vocabulary, while reusing the same verified citation set.

**Claim 6.** The method of claim 1, further comprising, when a target Indic
language differing from the language of the query is selected: translating only
the plain-language portion into the target Indic language with a neural machine
translation model, wherein the legal-register portion and the inline citation
markers remain untranslated, and appending the translated plain-language portion
to the output.

## Abstract (for the specification)

A system and method for time-aware, verified, multilingual legal
question-answering. A query and an incident date are analyzed to determine legal
domains and a language; a temporal-cutoff map deterministically routes each
domain to a legal regime (old/new/current) applicable on the incident date.
Evidence retrieval is gated by regime metadata so only chunks of the legally
applicable code are candidates. A dual-register answer is generated in one step:
a legal-register statement with inline citation markers plus a plain-language
statement restating the same claim. The answer is verified by confirming citation
existence and by scoring each cited sentence against the cited chunk text with an
NLI entailment model; unsupported answers trigger regeneration with verifier
feedback or are refused. On verification success, and only then, the
plain-language portion may be translated to an Indic language while citations
remain verbatim in English.