from __future__ import annotations

import argparse
import sys
from pathlib import Path

from kautilya import __version__
from kautilya.config import load_settings
from kautilya.log import setup_logging

_NOT_IMPLEMENTED = {
    "download-scj": "Phase 1b",
    "build-index": "Phase 2",
    "ask": "Phase 3",
    "eval": "Phase 4",
}


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

    p_pdf = sub.add_parser("ingest-pdf", help="parse a downloaded PDF (crpc|coi) to JSONL")
    p_pdf.add_argument("doc", choices=["crpc", "coi"])
    p_pdf.add_argument("--pdf", type=Path, required=True)
    p_pdf.add_argument("--out", type=Path, default=Path("data/processed/statutes"))
    p_pdf.set_defaults(func=_cmd_ingest_pdf)

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
    from kautilya.ingestion.pdf_parsers import parse_constitution, parse_crpc, write_shards

    parser_fn = {"crpc": parse_crpc, "coi": parse_constitution}[args.doc]
    provisions = parser_fn(args.pdf)
    shard = write_shards(provisions, args.out)
    print(f"{len(provisions)} provisions -> {shard}")
    return 0


def main(argv: list[str] | None = None) -> int:
    setup_logging()
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
