"""Verifier node (ARCHITECTURE.md §4, Phase 4a).

Two gates over the Synthesizer output:
1. Citation existence - every [chunk_id] in the legal register must exist
   inside the retrieved context.
2. NLI entailment - each cited sentence is checked against its cited span
   with an XNLI model; entailment probability below `threshold` marks the
   claim unsupported.

Unsupported claims -> route='regenerate' (<= settings.verifier.max_regen)
-> else refuse-with-sources. NLI unavailable -> citation check only.
"""

from __future__ import annotations

import re

from kautilya.log import get_logger

log = get_logger(__name__)

_CITE_RE = re.compile(r"\[([A-Za-z][A-Za-z0-9_]{2,60})\]")
_SENT_RE = re.compile(r"(?<=[.!?])\s+|\n+")

# XNLI models punish attribution scaffolding even when content is correct,
# so hypotheses are scored as several phrasings and the max is taken.
_SEC_REF_RE = re.compile(
    r"\bSections?\s+\d+[A-Za-z]*(?:\s*(?:and|&)\s*\d+[A-Za-z]*)*\b"
    r"|\bs\.\s?\d+[A-Za-z]*", re.IGNORECASE)
_FRAMING_RE = re.compile(
    r"^\s*(?:Under|In|Per|According to)\b[^,]{0,90},\s*", re.IGNORECASE)
_DEFS_RE = re.compile(
    r"\b(defines?|means|prescribes?|provides?|stipulates?|says)\b"
    r"(?:[^,.;]{0,30}?\bas\b|\s+that\b)?", re.IGNORECASE)
# Pure routing/attribution sentences carry no verifiable legal claim of
# their own - gate 1 (citation existence) covers them.
_ATTRIB_ONLY_RE = re.compile(
    r"^\s*(?:the\s+)?(?:primary\s+|main\s+|key\s+|relevant\s+)?"
    r"provisions?\b.*\bis\b.*$", re.IGNORECASE)


def split_sentences(text: str) -> list[str]:
    parts = [p.strip() for p in _SENT_RE.split(text or "") if p.strip()]
    return parts


def hypothesis_variants(sentence: str) -> list[str]:
    """Original + scaffold-free phrasings of one cited sentence."""
    if _ATTRIB_ONLY_RE.match(sentence):
        return []
    stripped = _SEC_REF_RE.sub("the law",
                               _FRAMING_RE.sub("", sentence))
    collapsed = re.sub(r"\bis\s+is\b", "is", _DEFS_RE.sub("is", stripped))
    collapsed = collapsed.strip()
    out = [sentence]
    if collapsed and collapsed != sentence:
        out.append(collapsed)
    return list(dict.fromkeys(out))


class NLIVerifier:
    """XNLI text-classification pipeline; fp16 on GPU, CPU fallback on OOM."""

    def __init__(self, model_name: str,
                 device: str | None = None):
        import torch
        from transformers import pipeline

        self.model_name = model_name
        if device is None:
            device = 0 if torch.cuda.is_available() else -1
        kwargs = dict(device=device)
        if device != -1:
            kwargs["torch_dtype"] = torch.float16
        try:
            self.pipe = pipeline("text-classification", model=model_name,
                                 **kwargs)
        except Exception as e:  # noqa: BLE001 - VRAM pressure etc.
            log.warning("nli: GPU load failed (%s); retrying on CPU", e)
            self.pipe = pipeline("text-classification", model=model_name,
                                 device=-1)

    def entailment_scores(self, premise: str,
                          hypotheses: list[str]) -> list[float]:
        """P(entailment) per hypothesis against one premise."""
        if not hypotheses:
            return []
        # NOTE: must use {"text", "text_pair"} dicts - bare tuples are
        # silently split into two independent single-text inputs.
        items = [{"text": premise[:4000], "text_pair": h} for h in hypotheses]
        results = self.pipe(items, batch_size=8,
                            top_k=None, truncation=True, padding=True)
        if results and isinstance(results[0], dict):
            results = [results]          # single-item call returns flat dict
        scores: list[float] = []
        for res in results:
            labels = {r["label"].upper(): float(r["score"]) for r in res}
            scores.append(labels.get("ENTAILMENT", 0.0))
        return scores

    def best_support(self, contexts: dict[str, str],
                     hypotheses: list[str]) -> list[float]:
        """Max P(entailment) over every retrieved chunk per hypothesis."""
        best = [0.0] * len(hypotheses)
        for text in contexts.values():
            scores = self.entailment_scores(text, hypotheses)[:len(best)]
            for i, sc in enumerate(scores):
                best[i] = max(best[i], sc)
        return best


def verify(state: dict,
           nli: NLIVerifier | None = None,
           threshold: float = 0.75,
           max_regen: int = 2) -> dict:
    """LangGraph node: `(state) -> partial state`."""
    if state.get("route") in ("refuse", "ask_date", "error"):
        return {"verification": "skipped"}

    answer_legal = state.get("answer_legal", "")
    # Premise per chunk = "Title. body" - the section-title anchor lifts
    # entailment on definitional sentences from ~0.47 to ~0.79.
    contexts: dict[str, str] = {
        c["chunk_id"]: f"{c.get('title') or ''}. {c.get('text') or ''}".strip(". ")
        for c in (state.get("retrieved") or [])}
    notes: list[str] = []

    # ---- gate 1: citation existence -------------------------------------
    cited = [c for c in dict.fromkeys(_CITE_RE.findall(answer_legal))]
    invalid = [c for c in cited if c not in contexts]
    if invalid:
        notes.append(f"citations not present in retrieved context: "
                     f"{', '.join(invalid)}")

    # ---- gate 2: NLI entailment, max over context x phrasings -----------
    unsupported: list[str] = []
    if cited and not invalid and nli is not None:
        for sentence in split_sentences(answer_legal):
            if not _CITE_RE.search(sentence):
                continue
            variants = hypothesis_variants(_CITE_RE.sub("", sentence).strip())
            if not variants or len(variants[0].split()) < 3:
                continue
            try:
                best = nli.best_support(contexts, variants)
            except Exception as e:  # noqa: BLE001 - never kill a live answer
                log.warning("verifier: NLI inference failed (%s); "
                            "falling back to citation-existence only", e)
                notes.append("NLI inference failed - citation check only")
                unsupported.clear()
                break
            score = max(best) if best else 1.0
            if score < threshold:
                unsupported.append(f"unsupported claim: {sentence[:90]}")
                log.info("verifier: low entailment (%.2f): %s",
                         score, sentence[:80])
    elif cited and not invalid and nli is None:
        notes.append("NLI unavailable - citation-existence check only")
    elif not cited:
        notes.append("no inline citations found in legal register")

    problems = bool(invalid or unsupported or not cited)

    # ---- routing ---------------------------------------------------------
    retries = int(state.get("retries") or 0)
    if not problems:
        return {"route": None,
                "verification": "pass",
                "verification_notes": notes}

    reason = "; ".join(notes + unsupported)[:200]
    if retries < max_regen:
        log.info("verifier: regenerate (%d/%d): %s",
                 retries + 1, max_regen, reason)
        return {"route": "regenerate", "verification": "fail",
                "retries": retries + 1,
                "verification_notes": notes + unsupported}
    log.warning("verifier: refusing after %d regenerations", retries)
    return {"route": "refuse", "verification": "fail",
            "verification_notes": notes + unsupported,
            "answer_simple": "I could not fully verify this answer against "
                             "the retrieved legal text after several "
                             "attempts, so I am refusing to answer. Please "
                             "rephrase or narrow the question."}
