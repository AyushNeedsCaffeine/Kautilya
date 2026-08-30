"""TemporalResolver node (ARCHITECTURE.md §4).

Pure logic, no network: routes each analysed domain to the legal regime in
force on the incident date (USP #1) and surfaces old<->new section
equivalences from data/mappings/*.json (NCRB corresponding-section tables).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date
from functools import cache
from pathlib import Path

from kautilya.log import get_logger
from kautilya.schemas import Equivalence

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_MAPPINGS_DIR = REPO_ROOT / "data" / "mappings"

log = get_logger(__name__)

# domain -> mapping file stem (None = route by cutoff only, no tables yet)
_DOMAIN_PAIR = {
    "criminal_substantive": ("ipc", "bns"),
    "criminal_procedure": ("crpc", "bnss"),
    "evidence": ("iea", "bsa"),
}

_FALLBACK_CUTOFFS = {  # mirrors config/settings.yaml temporal.cutoffs
    "criminal_substantive": "2024-07-01",
    "criminal_procedure": "2024-07-01",
    "evidence": "2024-07-01",
    "labour": "2025-11-21",
    "tax": "2026-04-01",
}


@dataclass(frozen=True)
class MappingTable:
    old_act: str
    new_act: str
    cutoff: str                                   # ISO yyyy-mm-dd
    forward: dict[str, dict]                      # new_sec -> pair
    reverse: dict[str, list[dict]]                # old_sec -> [pairs]

    def pair_for_new(self, sec: str) -> dict | None:
        return self.forward.get(sec.upper())

    def pairs_for_old(self, sec: str) -> list[dict]:
        return self.reverse.get(sec.upper(), [])


def load_mapping_table(path: Path) -> MappingTable:
    m = json.loads(Path(path).read_text(encoding="utf-8"))
    fwd: dict[str, dict] = {}
    rev: dict[str, list[dict]] = {}
    for p in m["pairs"]:
        fwd[p["new"].upper()] = p
        for o in p["old"]:
            rev.setdefault(o.upper(), []).append(p)
    meta = m["meta"]
    return MappingTable(old_act=meta["old_act"], new_act=meta["new_act"],
                        cutoff=str(meta["cutoff"]), forward=fwd, reverse=rev)


@cache
def load_mappings(dir_path: str = str(DEFAULT_MAPPINGS_DIR)) -> dict[tuple[str, str], MappingTable]:
    out: dict[tuple[str, str], MappingTable] = {}
    d = Path(dir_path)
    if d.is_dir():
        for f in sorted(d.glob("*_to_*.json")):
            t = load_mapping_table(f)
            out[(t.old_act.lower(), t.new_act.lower())] = t
    log.info("resolver: loaded %d mapping tables from %s", len(out), d)
    return out


# --------------------------------------------------------------- routing
def route_regime(domain: str,
                 incident_date: str | None,
                 cutoffs: dict[str, str] | None = None) -> str:
    """'old' if incident predates the domain cutoff, else 'new'.

    Missing date -> 'current' (latest law, resolver adds a note upstream);
    constitutional / general matters are regime-independent -> 'current'.
    """
    if domain in ("constitutional", "general"):
        return "current"
    if not incident_date:
        return "current"
    iso = (cutoffs or _FALLBACK_CUTOFFS).get(domain)
    if iso is None:
        return "current"
    return "old" if date.fromisoformat(incident_date) < date.fromisoformat(iso) else "new"


# ---------------------------------------------------- equivalence lookup
_SECTION_RE = re.compile(
    r"\b(?:section|sec|s)\.?\s*(\d{1,3}[A-Za-z]?)\b", re.IGNORECASE)


def mentioned_sections(query: str) -> list[str]:
    seen: list[str] = []
    for m in _SECTION_RE.finditer(query):
        s = m.group(1).upper()
        if s not in seen:
            seen.append(s)
    return seen[:6]


def find_equivalences(query: str,
                      domains: list[str],
                      regimes: dict[str, str],
                      tables: dict[tuple[str, str], MappingTable] | None = None,
                      max_notes: int = 8) -> list[Equivalence]:
    """Surface old<->new correspondences for sections cited in the query."""
    tabs = tables if tables is not None else load_mappings()
    secs = mentioned_sections(query)
    if not secs:
        return []

    relevant: list[MappingTable] = []
    for dom in domains:
        key = _DOMAIN_PAIR.get(dom)
        if key and key in tabs:
            t = tabs[key]
            if t not in relevant:
                relevant.append(t)

    out: list[Equivalence] = []
    for s in secs:
        for t in relevant:
            regime = regimes.get(
                next((d for d, k in _DOMAIN_PAIR.items()
                      if k == (t.old_act.lower(), t.new_act.lower())), ""),
                "new")
            if regime == "old":
                for p in t.pairs_for_old(s):
                    kind = "partial" if p.get("partial") else "corresponding"
                    out.append(Equivalence(
                        old_id=f"{t.old_act}_s{s}", equivalence=kind,
                        note=f"{t.old_act} s.{s} ≈ {t.new_act} s.{p['new']}"))
            else:
                p = t.pair_for_new(s)
                if p:
                    olds = ", ".join(f"s.{o}" for o in p["old"][:3])
                    more = "" if len(p["old"]) <= 3 else f" (+{len(p['old']) - 3} more)"
                    out.append(Equivalence(
                        old_id=f"{t.old_act}_{p['old'][0]}" if p["old"] else "",
                        equivalence="partial" if p.get("partial") else "corresponding",
                        note=f"{t.new_act} s.{s} ← {t.old_act} {olds}{more}"))
            if len(out) >= max_notes:
                return out[:max_notes]
    return out


# ------------------------------------------------------------------ node
def resolve_temporal(state: dict,
                     cutoffs: dict[str, str] | None = None,
                     tables: dict[tuple[str, str], MappingTable] | None = None) -> dict:
    """LangGraph node: `(state) -> partial state`."""
    needs_date = state.get("needs_date", False)
    incident = state.get("incident_date")
    if needs_date and not incident:
        log.info("resolver: past-tense query without date -> ask_date")
        return {"route": "ask_date", "regimes": {}, "equivalences": []}

    domains = state.get("domains") or ["general"]
    cuts = cutoffs  # None -> route_regime falls back to module defaults
    regimes = {d: route_regime(d, incident, cuts) for d in domains}
    equivs = find_equivalences(state.get("query_raw", ""), domains, regimes,
                               tables=tables)
    log.info("resolver: regimes=%s equivalences=%d", regimes, len(equivs))
    return {"regimes": regimes, "equivalences": equivs,
            "route": None, "incident_date": incident}
