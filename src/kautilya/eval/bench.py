"""KautilyaBench evaluation harness (ARCHITECTURE.md §6, phase 4b).

Loads gold QA pairs (data/bench/*.jsonl), runs them through retrieval
(stage=retrieval, no LLM) or the full pipeline (stage=full), and scores:

- Hit@5 / Hit@8      : any gold chunk in top-k retrieved
- MRR@8              : reciprocal rank of first gold hit
- citation precision : cited ids that are gold-or-related / total cited
- temporal accuracy  : routed regimes match expected_regimes
- refusal correctness: must_refuse rows actually refused
- FK<=10 rate        : simple register readability target

Models load once per process; per-record results stream to a JSONL trace
and aggregate into reports/bench_report.json.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path

from kautilya.log import get_logger

log = get_logger(__name__)

OLD_ACTS = {"IPC", "CRPC", "IEA"}
NEW_ACTS = {"BNS", "BNSS", "BSA"}


@dataclass
class Record:
    id: str
    query: str
    lang: str = "en"
    domain: str = "general"
    incident_date: str | None = None
    expected_route: str = "answer"
    expected_regimes: dict | None = None
    gold_chunk_ids: list[str] = field(default_factory=list)
    related_chunk_ids: list[str] = field(default_factory=list)
    must_refuse: bool = False
    category: str = ""
    notes: str = ""


def load_bench(path: Path) -> list[Record]:
    recs = []
    for i, line in enumerate(path.open()):
        d = json.loads(line)
        d.setdefault("id", f"kb{i:03d}")
        recs.append(Record(**{k: v for k, v in d.items()
                              if k in Record.__dataclass_fields__}))
    return recs


# ------------------------------------------------------------------ metrics
def hit_at_k(retrieved: list[str], gold: list[str], k: int) -> bool:
    g = set(gold)
    return any(r in g for r in retrieved[:k])


def mrr_at_k(retrieved: list[str], gold: list[str], k: int) -> float:
    g = set(gold)
    for rank, r in enumerate(retrieved[:k], start=1):
        if r in g:
            return 1.0 / rank
    return 0.0


def citation_precision(cited: list[str], record: Record) -> tuple[float, int]:
    """Fraction of citations that are gold-or-related; (prec, n_cited)."""
    ok = set(record.gold_chunk_ids) | set(record.related_chunk_ids)
    base = lambda cid: cid.split("_p")[0]  # noqa: E731 - parts count as same
    ok_bases = {base(i) for i in ok}
    good = sum(1 for c in cited if base(c) in ok_bases)
    return (good / len(cited)) if cited else 1.0, len(cited)


def temporal_correct(record: Record, regimes: dict | None) -> bool:
    if not record.expected_regimes:
        return True
    if not regimes:
        return False
    want_prefix = {dom.split("_")[0]: r for dom, r in
                   record.expected_regimes.items()}
    got_prefix = {dom.split("_")[0]: r for dom, r in regimes.items()}
    return all(got_prefix.get(d) == r for d, r in want_prefix.items())


def fk_grade(text: str) -> float | None:
    try:
        import textstat
    except ImportError:  # pragma: no cover
        return None
    if not text or not text.strip():
        return None
    try:
        return float(textstat.flesch_kincaid_grade(text))
    except Exception:  # noqa: BLE001
        return None


def route_matches(record: Record, out: dict) -> bool:
    got_route = "ask_date" if out.get("route") == "ask_date" else "answer"
    return got_route == record.expected_route


def refusal_correct(record: Record, out: dict) -> bool:
    refused = (out.get("route") == "refuse" or out.get("refused") is True)
    return refused == record.must_refuse


# ------------------------------------------------------------------ runner
def _trace_done_ids(trace_path: Path) -> set[str]:
    """Ids already in the trace (successful rows) — skip on resume."""
    if not trace_path.exists():
        return set()
    done: set[str] = set()
    for line in trace_path.open():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not row.get("id") or row.get("error"):
            continue
        answers = str(row.get("answer_simple") or "") + \
            str(row.get("answer_legal") or "")
        if "Answer generation failed" in answers:
            continue
        done.add(row["id"])
    return done


def evaluate(records: list[Record],
             retriever=None,
             pipeline_fn=None,
             final_k: int = 8,
             limit: int | None = None,
             trace_path: Path | None = None,
             progress_every: int = 10,
             delay: float = 0.0,
             resume: bool = False) -> dict:
    """Run records through one stage; returns aggregate report dict.

    With resume=True and an existing trace, previously completed record ids
    are skipped and new rows append to the trace (rate-limit friendly:
    nightly batches without re-burning quota on re-runs).
    """
    if resume and trace_path:
        done = _trace_done_ids(trace_path)
        todo = [r for r in records if r.id not in done]
        log.info("resume: skipped %d already-trace records, %d remain",
                 len(records) - len(todo), len(todo))
        records = todo
    if limit:
        records = records[:limit]

    rows: list[dict] = []
    t_start = time.time()
    trace_file = None
    if trace_path:
        trace_path.parent.mkdir(parents=True, exist_ok=True)
        trace_file = trace_path.open("a" if (resume and trace_path.exists())
                                    else "w")

    try:
      for n, rec in enumerate(records, start=1):
        t0 = time.time()
        row: dict = {"id": rec.id, "category": rec.category,
                     "query": rec.query}
        try:
            if pipeline_fn is not None:            # full stage
                out = pipeline_fn(rec.query,
                                  incident_date=rec.incident_date)
                retrieved = [c["chunk_id"] for c in out.get("retrieved", [])]
                cited = list(out.get("citations") or [])
                row.update(
                    route=out.get("route"),
                    regimes=dict(out.get("regimes") or {}),
                    verification=out.get("verification"),
                    answer_simple=(out.get("answer_simple") or "")[:400],
                    answer_legal=(out.get("answer_legal") or "")[:600])
                row["fk"] = fk_grade(out.get("answer_simple"))
            else:                                   # retrieval stage
                from kautilya.graph.analyzer import analyze_query
                from kautilya.graph.resolver import resolve_temporal
                st: dict = {"query_raw": rec.query}
                if rec.incident_date:
                    st["incident_date"] = rec.incident_date
                st.update(analyze_query(st))       # offline fallback path
                if rec.incident_date:              # gold date wins over any
                    st["incident_date"] = rec.incident_date  # text parse
                st.update(resolve_temporal(st))
                res = retriever.retrieve(st) if st.get("route") != \
                    "ask_date" else []
                retrieved = [c["chunk_id"] for c in res]
                cited = []
                row.update(route=st.get("route") or "answer",
                           regimes=dict(st.get("regimes") or {}),
                           verification="n/a")
        except Exception as e:                      # noqa: BLE001
            log.warning("bench %s failed: %s", rec.id, e)
            row["error"] = str(e)[:200]
            retrieved, cited = [], []

        # a synthesis failure is NOT a valid refuse: mark it so resume retries
        if not row.get("error") and pipeline_fn is not None:
            failed_answers = [
                a for a in ((row.get("answer_simple") or ""),
                            (row.get("answer_legal") or ""))
                if "Answer generation failed" in a]
            if failed_answers:
                row["error"] = "synthesis failed (generation error)"
                if "citations" in row:
                    row["citations"] = []
                row["answers_invalid"] = True
                retrieved, cited = row.get("retrieved_top", []), []

        dt = time.time() - t0
        prec, ncited = citation_precision(cited, rec)
        row.update(
            latency_s=round(dt, 2),
            retrieved_top=retrieved[:final_k],
            cited=cited,
            hit5=hit_at_k(retrieved, rec.gold_chunk_ids, 5),
            hit8=hit_at_k(retrieved, rec.gold_chunk_ids, final_k),
            mrr8=mrr_at_k(retrieved, rec.gold_chunk_ids, final_k),
            cit_prec=prec, n_cited=ncited,
            temporal_ok=temporal_correct(rec, row.get("regimes")),
            route_ok=route_matches(rec, row),
            refusal_ok=refusal_correct(rec, row),
            gold=rec.gold_chunk_ids[:3],
        )
        rows.append(row)
        if trace_file:
            trace_file.write(json.dumps(row, ensure_ascii=False) + "\n")
            trace_file.flush()
        if delay:
            time.sleep(delay)
        if n % progress_every == 0 or n == len(records):
            log.info("bench: %d/%d (%.1fs avg)", n, len(rows),
                     (time.time() - t_start) / n)
    finally:
        if trace_file:
            trace_file.close()

    if resume and trace_path and rows:
        # reload the full trace → cumulative report over all completed rows
        all_rows: list[dict] = []
        _score_keys = ("category", "hit5", "hit8", "mrr8", "cit_prec",
                       "n_cited", "temporal_ok", "route_ok", "refusal_ok")
        for line in trace_path.open():
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            answers = str(row.get("answer_simple") or "") + \
                str(row.get("answer_legal") or "")
            if row.get("error") or "Answer generation failed" in answers:
                continue        # stale/failed rows are retried on next resume
            if not all(k in row for k in _score_keys):
                continue        # malformed rows are not completed records
            all_rows.append(row)
        rows = all_rows

    scored = [r for r in rows if not r.get("error")]
    n = max(len(scored), 1)
    # retrieval-quality subset: rows whose golds are real retrieval targets
    core = [r for r in scored
            if r["category"] not in ("ask_date", "gap")]
    nc = max(len(core), 1)

    def frac(rows_, key: str) -> float:
        return sum(1 for r in rows_ if r[key]) / max(len(rows_), 1)

    prec_vals = [r["cit_prec"] for r in scored if r["n_cited"]]
    fks = [r["fk"] for r in scored if isinstance(r.get("fk"), float)]
    by_cat: dict[str, dict] = {}
    for cat in sorted({r["category"] for r in scored}):
        sub = [r for r in scored if r["category"] == cat]
        m = max(len(sub), 1)
        by_cat[cat] = {
            "n": len(sub),
            "hit5": round(sum(r["hit5"] for r in sub) / m, 3),
            "temporal_ok": round(sum(r["temporal_ok"] for r in sub) / m, 3),
        }

    return {
        "stage": "full" if pipeline_fn else "retrieval",
        "n_records": len(rows), "n_errors": len(rows) - len(scored),
        "hit5": round(frac(scored, "hit5"), 3),
        "hit8": round(frac(scored, "hit8"), 3),
        "hit5_core": round(frac(core, "hit5"), 3),
        "mrr8": round(sum(r["mrr8"] for r in scored) / n, 3),
        "mrr8_core": round(sum(r["mrr8"] for r in core) / nc, 3),
        "citation_precision": round(sum(prec_vals) / max(len(prec_vals), 1),
                                    3),
        "n_cited_total": sum(r["n_cited"] for r in scored),
        "temporal_accuracy": round(frac(scored, "temporal_ok"), 3),
        "route_accuracy": round(frac(scored, "route_ok"), 3),
        "refusal_correctness": round(frac(scored, "refusal_ok"), 3),
        "fk_le_10_rate": round(sum(1 for v in fks if v <= 10)
                               / max(len(fks), 1), 3),
        "fk_median": round(sorted(fks)[len(fks) // 2], 2) if fks else None,
        "avg_latency_s": round((time.time() - t_start) / n, 2),
        "wall_min": round((time.time() - t_start) / 60, 1),
        "by_category": by_cat,
    }
