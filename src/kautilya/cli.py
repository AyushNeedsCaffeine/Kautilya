from __future__ import annotations

import argparse
import sys
from pathlib import Path

from kautilya import __version__
from kautilya.config import Settings, load_settings
from kautilya.log import setup_logging

_NOT_IMPLEMENTED = {
    "download": "Phase 1",
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

    for name, phase in _NOT_IMPLEMENTED.items():
        p_stub = sub.add_parser(name, help=f"(arrives in {phase})")
        p_stub.add_argument("query", nargs="*", help="free-form arguments for the command")
        p_stub.set_defaults(func=lambda args, s=None, ph=phase: _stub(ph))

    return parser


def _stub(phase: str) -> int:
    print(f"not implemented yet — scheduled for {phase}", file=sys.stderr)
    return 2


def main(argv: list[str] | None = None) -> int:
    setup_logging()
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
