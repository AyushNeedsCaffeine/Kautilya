from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from kautilya import __version__
from kautilya.config import load_settings
from kautilya.log import setup_logging

_NOT_IMPLEMENTED = {
    "download-scj": "Phase 1b",
}


def _cmd_eval(args: argparse.Namespace) -> int:
    from kautilya.eval.bench import evaluate, load_bench
    from kautilya.indexing.build_index import IndexConfig
    from kautilya.indexing.search import HybridRetriever

    settings = load_settings(args.config or Path("config/settings.yaml"))
    records = load_bench(args.bench)
    print(f"bench: {len(records)} records from {args.bench}")

    retriever = pipeline_fn = None
    if args.stage == "retrieval":
        idx = IndexConfig.from_settings(args.config or
                                        Path("config/settings.yaml"))
        ret = settings.retrieval
        retriever = HybridRetriever(persist=idx.persist,
                                    dense_k=ret.dense_k,
                                    sparse_k=ret.sparse_k, rrf_k=ret.rrf_k,
                                    final_k=ret.final_k)
    else:
        from kautilya.graph.pipeline import run_query
        from kautilya.graph.verifier import NLIVerifier
        from kautilya.llm import create_llm

        llm = create_llm(provider=args.llm, config_path=args.config)
        nli = None if args.no_verify else NLIVerifier(settings.verifier.nli_model)
        idx = IndexConfig.from_settings(args.config or
                                        Path("config/settings.yaml"))
        ret = settings.retrieval
        retr = HybridRetriever(persist=idx.persist, dense_k=ret.dense_k,
                               sparse_k=ret.sparse_k, rrf_k=ret.rrf_k,
                               final_k=ret.final_k)

        def pipeline_fn(query, incident_date=None):  # noqa: E306
            return run_query(query, llm=llm, retriever=retr, nli=nli,
                             incident_date=incident_date)

    report = evaluate(records, retriever=retriever,
                      pipeline_fn=pipeline_fn,
                      final_k=settings.retrieval.final_k,
                      limit=args.limit,
                      trace_path=args.trace,
                      delay=args.delay)
    report["bench"] = str(args.bench)
    args.out.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: v for k, v in report.items()
                      if k != "by_category"}, indent=2))
    print("\nby category:")
    for cat, s in report["by_category"].items():
        print(f"  {cat:<18} n={s['n']:<3} hit5={s['hit5']:<6}"
              f" temporal={s['temporal_ok']}")
    print(f"\nreport -> {args.out}")
    if args.trace:
        print(f"trace  -> {args.trace}")
    return 0


def validate_config(config: Path | None) -> int:
    settings = load_settings(config)
    print("config OK")
    print(f"  llm        : {settings.llm.provider}/{settings.llm.model}")
    print(f"  embeddings : {settings.embeddings.model}")
    print(f"  languages  : {', '.join(settings.languages)}")
    for domain, cutoff in settings.temporal.cutoffs.items():
        print(f"  cutoff     : {domain:<22} {cutoff.isoformat()}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="kautilya",
        description="Time-aware, citation-verified legal RAG over Indian law.",
    )
    parser.add_argument("--version", action="version", version=f"kautilya {__version__}")
    parser.add_argument("--config", type=Path, default=None, help="path to settings.yaml")
    sub = parser.add_subparsers(dest="command", required=True)

    p_validate = sub.add_parser("validate-config", help="validate settings.yaml and exit")
    p_validate.set_defaults(func=lambda args, s=None: validate_config(args.config))

    p_ingest = sub.add_parser("ingest", help="normalize central-legislation parquet to JSONL")
    p_ingest.add_argument("--parquet", type=Path,
                          default=Path("data/raw/in_central_legislation.parquet"))
    p_ingest.add_argument("--out", type=Path, default=Path("data/processed/statutes"))
    p_ingest.set_defaults(func=_cmd_ingest)

    p_pdf = sub.add_parser("ingest-pdf", help="parse a downloaded PDF (crpc|coi|ita2025) to JSONL")
    p_pdf.add_argument("doc", choices=["crpc", "coi", "ita2025"])
    p_pdf.add_argument("--pdf", type=Path, required=True)
    p_pdf.add_argument("--out", type=Path, default=Path("data/processed/statutes"))
    p_pdf.set_defaults(func=_cmd_ingest_pdf)

    p_chunks = sub.add_parser("build-chunks", help="section-aware chunks from statute shards")
    p_chunks.add_argument("--shards", type=Path, default=Path("data/processed/statutes"))
    p_chunks.add_argument("--out", type=Path, default=Path("data/processed/chunks"))
    p_chunks.set_defaults(func=_cmd_build_chunks)

    p_index = sub.add_parser("build-index", help="embed chunks -> LanceDB + BM25 index")
    p_index.add_argument("--chunks", type=Path, default=Path("data/processed/chunks"))
    p_index.add_argument("--persist", type=Path, default=None)
    p_index.set_defaults(func=_cmd_build_index)

    p_ask = sub.add_parser("ask", help="ask a legal question (time-aware, dual-register)")
    p_ask.add_argument("question", nargs="+")
    p_ask.add_argument("--date", default=None, help="incident date (YYYY-MM-DD)")
    p_ask.add_argument("--lang", default=None, help="answer language code (en/hi/...)")
    p_ask.add_argument("--legal-only", action="store_true")
    p_ask.add_argument("--simple-only", action="store_true")
    p_ask.add_argument("--json", action="store_true", dest="as_json")
    p_ask.add_argument("--no-verify", action="store_true",
                       help="skip NLI verification (faster, unverified)")
    p_ask.add_argument("--llm", choices=["gemini", "ollama"], default=None,
                       help="LLM backend (default: settings.yaml provider)")
    p_ask.set_defaults(func=_cmd_ask)

    p_eval = sub.add_parser("eval",
                            help="run KautilyaBench (retrieval or full stage)")
    p_eval.add_argument("--bench", type=Path,
                        default=Path("data/bench/bench_v1.jsonl"))
    p_eval.add_argument("--stage", choices=["retrieval", "full"],
                        default="retrieval")
    p_eval.add_argument("--limit", type=int, default=None,
                        help="evaluate only the first N records")
    p_eval.add_argument("--out", type=Path,
                        default=Path("reports/bench_report.json"))
    p_eval.add_argument("--trace", type=Path,
                        default=Path("reports/bench_trace.jsonl"))
    p_eval.add_argument("--llm", choices=["gemini", "ollama"], default=None,
                        help="LLM backend (default: settings.yaml provider)")
    p_eval.add_argument("--no-verify", action="store_true",
                        help="skip NLI verification (faster, unverified)")
    p_eval.add_argument("--delay", type=float, default=0.0,
                        help="sleep N seconds between records (rate-limit relief)")
    p_eval.set_defaults(func=_cmd_eval)

    for name, phase in _NOT_IMPLEMENTED.items():
        p_stub = sub.add_parser(name, help=f"(arrives in {phase})")
        p_stub.add_argument("query", nargs="*", help="free-form arguments for the command")
        p_stub.set_defaults(func=lambda args, s=None, ph=phase: _stub(ph))

    return parser


def _stub(phase: str) -> int:
    print(f"not implemented yet — scheduled for {phase}", file=sys.stderr)
    return 2


def _cmd_ingest(args: argparse.Namespace) -> int:
    from kautilya.ingestion.ingest import ingest_legislation, write_report

    report = ingest_legislation(args.parquet, args.out)
    report_path = Path("reports") / "ingestion_coverage.json"
    write_report(report, report_path)
    for short, info in sorted(report.items()):
        cov = f"{info['coverage']:.1%}" if info.get("coverage") else "-"
        print(f"  {short:10s} sections={info['sections']:4d} expected="
              f"{info.get('expected', '-'):>4} coverage={cov}")
    print(f"coverage report -> {report_path}")
    return 0


def _cmd_ingest_pdf(args: argparse.Namespace) -> int:
    from kautilya.ingestion.pdf_parsers import (
        parse_constitution,
        parse_crpc,
        parse_ita2025,
        write_shards,
    )

    parser_fn = {
        "crpc": parse_crpc,
        "coi": parse_constitution,
        "ita2025": parse_ita2025,
    }[args.doc]
    provisions = parser_fn(args.pdf)
    shard = write_shards(provisions, args.out)
    print(f"{len(provisions)} provisions -> {shard}")
    return 0


def _cmd_build_chunks(args: argparse.Namespace) -> int:
    import json

    from kautilya.chunking.legal_chunker import ChunkConfig, build_chunks

    cfg = ChunkConfig.from_settings(args.config or Path("config/settings.yaml"))
    stats = build_chunks(args.shards, args.out, cfg)
    total = sum(v["chunks"] for v in stats.values())
    for short, info in sorted(stats.items()):
        print(f"  {short:9s} sections={info['sections']:4d} chunks={info['chunks']:4d} "
              f"oversized={info['oversized_sections']}")
    print(f"total: {total} chunks -> {args.out}")
    report = Path("reports") / "chunking_stats.json"
    report.parent.mkdir(exist_ok=True)
    report.write_text(json.dumps(
        {"config": {"max_tokens": cfg.max_tokens,
                    "chars_per_token": cfg.chars_per_token},
         "stats": stats}, indent=2) + "\n")
    print(f"chunking report -> {report}")
    return 0


def _cmd_build_index(args: argparse.Namespace) -> int:
    import json

    from kautilya.indexing.build_index import IndexConfig, build_index, load_chunks

    cfg = IndexConfig.from_settings(args.config or Path("config/settings.yaml"))
    if args.persist:
        cfg = IndexConfig(model=cfg.model, persist=args.persist,
                          batch_size=cfg.batch_size, device=cfg.device,
                          dtype=cfg.dtype)
    chunks = load_chunks(args.chunks)
    print(f"loaded {len(chunks)} chunks; embedding with {cfg.model} ...")
    stats = build_index(chunks, cfg)
    print(f"lancedb rows={stats['table_rows']} dim={stats['dim']} "
          f"in {stats['seconds']}s -> {cfg.persist}")
    report = Path("reports") / "index_stats.json"
    report.write_text(json.dumps(stats, indent=2) + "\n")
    print(f"index report -> {report}")
    return 0


def _cmd_ask(args: argparse.Namespace) -> int:
    import json as _json

    from kautilya.graph.pipeline import run_query
    from kautilya.graph.verifier import NLIVerifier
    from kautilya.indexing.build_index import IndexConfig
    from kautilya.indexing.search import HybridRetriever
    from kautilya.llm import create_llm

    settings = load_settings(args.config or Path("config/settings.yaml"))
    llm = create_llm(provider=args.llm, config_path=args.config)
    idx = IndexConfig.from_settings(args.config or Path("config/settings.yaml"))
    ret = settings.retrieval
    retriever = HybridRetriever(persist=idx.persist, dense_k=ret.dense_k,
                                sparse_k=ret.sparse_k, rrf_k=ret.rrf_k,
                                final_k=ret.final_k)
    nli = None
    if not args.no_verify:
        vcfg = settings.verifier
        nli = NLIVerifier(vcfg.nli_model)
    question = " ".join(args.question)
    print(f"asking: {question!r} ...", flush=True)

    out = run_query(question, llm=llm, retriever=retriever, nli=nli,
                    incident_date=args.date, final_lang=args.lang)

    if args.as_json:
        keep = {k: out.get(k) for k in
                ("query_raw", "input_lang", "domains", "incident_date",
                 "regimes", "route", "answer_legal", "answer_simple",
                 "answer_translated", "citations",
                 "verification", "verification_notes")}
        print(_json.dumps(keep, indent=2, default=str))
        return 0

    if out.get("route") == "ask_date":
        print("\nThis looks like a past-incident question but no date was found.")
        print("Re-run with:  --date YYYY-MM-DD")
        return 0

    if out.get("route") == "refuse":
        print("\n== Refused ==")
        print(out.get("answer_simple") or "Could not verify an answer.")
        notes = out.get("verification_notes") or []
        if notes:
            print("Verifier notes:", "; ".join(n[:100] for n in notes[:3]))
        print("\n--- Informational purposes only; not legal advice. ---")
        return 0

    sources = ", ".join(out.get("citations", [])) or "-"
    print()
    if not args.simple_only:
        print("== Legal register ==")
        print(out.get("answer_legal") or "(refused)")
    if not args.legal_only:
        translated = out.get("answer_translated")
        if translated and args.lang and args.lang != "en":
            print(f"\n== Simple register ({args.lang}) ==")
            print(translated)
        else:
            print("\n== Simple register ==")
            print(out.get("answer_simple") or "(refused)")
    print(f"\nSources: {sources}")
    if out.get("verification") == "pass" and nli is not None:
        print("Verified: every cited claim checked for entailment (NLI).")
    elif out.get("verification") == "pass":
        print("Verified: citations exist in retrieved context "
              "(NLI skipped).")
    if out.get("equivalences"):
        for e in out["equivalences"]:
            print(f"Note: {e.note}")
    print("\n--- Informational purposes only; not legal advice. ---")
    return 0


def main(argv: list[str] | None = None) -> int:
    setup_logging()
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
