from __future__ import annotations

import json
from pathlib import Path

import polars as pl

from kautilya.ingestion.normalize import normalize_act
from kautilya.ingestion.sources import ACT_REGISTRY
from kautilya.log import get_logger

logger = get_logger(__name__)


def ingest_legislation(parquet_path: Path, out_dir: Path) -> dict[str, dict]:
    out_dir.mkdir(parents=True, exist_ok=True)
    df = pl.read_parquet(parquet_path)
    report: dict[str, dict] = {}

    for act_id, source in ACT_REGISTRY.items():
        sub = df.filter(pl.col("act_id") == act_id)
        if sub.is_empty():
            logger.warning("act_id %s (%s) not found in parquet", act_id, source.short)
            report[source.short] = {"status": "missing", "sections": 0}
            continue
        provisions = normalize_act(sub, source)
        shard = out_dir / f"{source.short}.jsonl"
        with open(shard, "w", encoding="utf-8") as fh:
            for p in provisions:
                fh.write(p.model_dump_json() + "\n")
        expected = source.expected_sections or 0
        found = len(provisions)
        report[source.short] = {
            "status": "ok",
            "sections": found,
            "expected": expected,
            "coverage": round(found / expected, 3) if expected else None,
        }
        logger.info("%s: %d provisions -> %s", source.short, found, shard)
    return report


def write_report(report: dict[str, dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2)
