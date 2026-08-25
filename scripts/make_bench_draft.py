"""Draft KautilyaBench v1 candidates from committed artifacts (no LLM).

Outputs data/bench/draft.jsonl (~120 records) for human review.
Every record carries: query, lang, domain, incident_date, expected_route,
expected_regimes, gold/related chunk ids, must_refuse, category.

Usage: Kautilya-venv/bin/python scripts/make_bench_draft.py [--out PATH]
"""

from __future__ import annotations

import argparse
import json
import random
import re
import sys
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

CHUNKS_DIR = REPO / "data/processed/chunks"
MAPPINGS = REPO / "data/mappings"
CUTOFF_CRIM = date(2024, 7, 1)
CUTOFF_TAX = date(2026, 4, 1)

random.seed(42)


def load_chunks() -> dict[str, dict]:
    out = {}
    for f in CHUNKS_DIR.glob("*.jsonl"):
        for line in f.open():
            c = json.loads(line)
            out[c["chunk_id"]] = c
    return out


def load_twins() -> dict[str, list[str]]:
    """old_section -> new ids and vice versa, across the three tables."""
    tables = [("ipc_to_bns.json", "IPC", "BNS"),
              ("crpc_to_bnss.json", "CRPC", "BNSS"),
              ("iea_to_bsa.json", "IEA", "BSA")]
    fwd: dict[str, list[str]] = {}
    rev: dict[str, list[str]] = {}
    for fname, old_act, new_act in tables:
        m = json.loads((MAPPINGS / fname).read_text())
        pairs = m["pairs"] if isinstance(m, dict) else m
        for p in pairs:
            news = p["new"] if isinstance(p["new"], list) else [p["new"]]
            olds = p["old"]
            for o in olds:
                fwd.setdefault(f"{old_act}_s{o}", []).extend(
                    f"{new_act}_s{n}" for n in news)
            for n in news:
                rev.setdefault(f"{new_act}_s{n}", []).extend(
                    f"{old_act}_s{o}" for o in olds)
    return {"fwd": fwd, "rev": rev}


def clean_title(t: str) -> bool:
    """Titles suitable for templated queries (no amendment noise)."""
    if not (12 <= len(t.strip()) <= 95):
        return False
    bad = ("subs.", "omitted", "inserted", "substituted", "repealed",
           "amendment", "w.e.f", "[...]", "act 26")
    return not any(b in t.lower() for b in bad)


def rec(idx: int, **kw) -> dict:
    return {
        "id": f"kb{idx:03d}",
        "query": kw["query"],
        "lang": kw.get("lang", "en"),
        "domain": kw["domain"],
        "incident_date": kw.get("incident_date"),
        "expected_route": kw.get("expected_route", "answer"),
        "expected_regimes": kw.get("expected_regimes"),
        "gold_chunk_ids": kw["gold"],
        "related_chunk_ids": kw.get("related", []),
        "must_refuse": kw.get("must_refuse", False),
        "category": kw["category"],
        "notes": kw.get("notes", ""),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path,
                    default=REPO / "data/bench/draft.jsonl")
    args = ap.parse_args()

    chunks = load_chunks()
    twins = load_twins()

    def expand(cid: str) -> list[str]:
        """'CRPC_s125' or 'CRPC_s125_p1' -> every part of that section."""
        base = cid.split("_p")[0]
        pat = re.compile(rf"^{re.escape(base)}(_p\d+)?$")
        return sorted(i for i in chunks if pat.match(i))

    def valid(ids: list[str]) -> list[str]:
        out: list[str] = []
        for i in dict.fromkeys(ids):
            out.extend(expand(i))
        return out

    def twin_of(cid: str) -> list[str]:
        base = cid.split("_p")[0]
        return sorted(set(
            twins["fwd"].get(base, []) or twins["rev"].get(base, [])))

    rows: list[dict] = []
    idx = 1

    def add(**kw):
        nonlocal idx
        gold = valid(kw.pop("gold"))
        rel = valid(kw.pop("related", []))
        if not gold:
            print(f"  !! skipped (no gold): {kw['query'][:50]}",
                  file=sys.stderr)
            return
        rows.append(rec(idx, gold=gold, related=rel, **kw))
        idx += 1

    # ---------------------------------------------------------- seeds
    D_PRE = "2024-03-15"
    D_POST = "2024-09-15"

    crim_old_new = [
        ("punishment for murder", ["IPC_s302"], "criminal_substantive"),
        ("attempt to murder punishment", ["IPC_s307"], "criminal_substantive"),
        ("cheating and dishonestly inducing delivery of property",
         ["IPC_s420"], "criminal_substantive"),
        ("dowry death punishment", ["IPC_s304B"], "criminal_substantive"),
        ("husband subjecting wife to cruelty", ["IPC_s498A"],
         "criminal_substantive"),
        ("culpable homicide not amounting to murder", ["IPC_s304"],
         "criminal_substantive"),
        ("punishment for theft", ["IPC_s379"], "criminal_substantive"),
        ("robbery and dacoity punishment", ["IPC_s392"], "criminal_substantive"),
        ("criminal conspiracy", ["IPC_s120B"], "criminal_substantive"),
        ("public servant taking bribe", ["IPC_s161"], "criminal_substantive"),
        ("outraging modesty of a woman", ["IPC_s354"], "criminal_substantive"),
        ("kidnapping for ransom", ["IPC_s364A"], "criminal_substantive"),
    ]
    for q, gold, dom in crim_old_new:
        tw = twin_of(gold[0])
        if not tw:
            print(f"  !! no twins for {gold[0]} - skipping new-regime pair",
                  file=sys.stderr)
        else:
            add(query=f"{q}", domain=dom, incident_date=D_PRE,
                expected_regimes={dom.split("_")[0]: "old"}, gold=gold,
                related=twin_of(gold[0]), category="regime_old")
            add(query=f"{q} (incident happened in September 2024)",
                domain=dom, incident_date=D_POST,
                expected_regimes={dom.split("_")[0]: "new"}, gold=tw,
                related=gold, category="regime_new")

    proc_old_new = [
        ("registration of FIR information in cognizable offences",
         ["CRPC_s154"]),
        ("regular bail in non-bailable offence", ["CRPC_s437"]),
        ("anticipatory bail", ["CRPC_s438"]),
        ("police to produce arrested person before magistrate within 24 hours",
         ["CRPC_s57"]),
        ("right of accused against self incrimination free legal aid",
         ["CRPC_s304"]),
        ("charge sheet completion timeline investigation custody",
         ["CRPC_s167"]),
        ("maintenance of wife children and parents", ["CRPC_s125"]),
    ]
    for q, gold in proc_old_new:
        tw = twin_of(gold[0])
        if not tw:
            print(f"  !! no twins for {gold[0]} - skipping pair",
                  file=sys.stderr)
            continue
        add(query=q, domain="criminal_procedure", incident_date=D_PRE,
            expected_regimes={"criminal_procedure": "old"}, gold=gold,
            related=twin_of(gold[0]), category="regime_old")
        add(query=f"{q} (offence dated June 2025)", domain="criminal_procedure",
            incident_date="2025-06-01",
            expected_regimes={"criminal_procedure": "new"},
            gold=tw, related=gold, category="regime_new")

    ev_old_new = [
        ("admissibility of electronic records certificate",
         ["IEA_s65B"], "evidence"),
        ("opinions of experts admissibility", ["IEA_s45"], "evidence"),
        ("statement of relevant fact by person who is dead or cannot attend",
         ["IEA_s32"], "evidence"),
    ]
    for q, gold, dom in ev_old_new:
        tw = twin_of(gold[0])
        if not tw:
            print(f"  !! no twins for {gold[0]} - skipping pair",
                  file=sys.stderr)
            continue
        add(query=q, domain=dom, incident_date=D_PRE,
            expected_regimes={"evidence": "old"}, gold=gold,
            related=twin_of(gold[0]), category="regime_old")
        add(query=f"{q} (trial for a 2025 offence)", domain=dom,
            incident_date="2025-02-10",
            expected_regimes={"evidence": "new"},
            gold=tw, related=gold, category="regime_new")

    # constitutional / landmarks
    landmark_rows = [
        ("basic structure doctrine Kesavananda Bharati",
         "Kesavananda Bharati v State of Kerala", "constitutional"),
        ("right to privacy fundamental right Puttaswamy",
         "Justice K.S. Puttaswamy v Union of India (Privacy)", "constitutional"),
        ("President's rule state emergency Bommai safeguards",
         "S.R. Bommai v Union of India", "constitutional"),
        ("death penalty rarest of rare Bachan Singh",
         "Bachan Singh v State of Punjab", "criminal_substantive"),
        ("rarest of rare case guidelines Machhi Singh",
         "Machhi Singh v State of Punjab", "criminal_substantive"),
        ("section 303 mandatory death sentence unconstitutional Mithu",
         "Mithu v State of Punjab", "criminal_substantive"),
        ("certificate under section 65B mandatory Anvar Basheer",
         "Anvar P.V. v P.K. Basheer", "evidence"),
        ("65B certificate overruled Arjun Panditrao Khotkar position",
         "Arjun Panditrao Khotkar v Kailash Kushanrao Gorantyal", "evidence"),
        ("zero FIR mandatory registration Lalita Kumari",
         "Lalita Kumari v Govt of UP", "criminal_procedure"),
        ("arrest guidelines Arnesh Kumar 41A notice", 
         "Arnesh Kumar v State of Bihar", "criminal_procedure"),
        ("arrest safeguards D.K. Basu memo grounds", 
         "D.K. Basu v State of West Bengal", "criminal_procedure"),
        ("reading down section 377 decriminalisation Navtej Johar",
         "Navtej Singh Johar v Union of India", "criminal_substantive"),
        ("online speech 66A struck down Shreya Singhal",
         "Shreya Singhal v Union of India", "constitutional"),
        ("narco analysis test self incrimination Selvi", 
         "Selvi v State of Karnataka", "criminal_procedure"),
        ("living will euthanasia Common Cause", 
         "Common Cause v Union of India (Euthanasia)", "constitutional"),
        ("doctrine of harmonious construction Golak Nath",
         "Golak Nath v State of Punjab", "constitutional"),
        ("pavement dwellers right to livelihood Olga Tellis",
         "Olga Tellis v Bombay Municipal Corporation", "constitutional"),
        ("visceral hatred speech incitement Tehseen Poonawalla lynching",
         "Tehseen S. Poonawalla v Union of India", "criminal_substantive"),
    ]
    lm_gold_cache: dict[str, list[str]] = {}
    for c in chunks.values():
        if c.get("landmark"):
            lm_gold_cache.setdefault(c["landmark"], []).append(c["chunk_id"])
    for q, lm, dom in landmark_rows:
        # any part of the judgment counts as a hit - keep 10 parts
        golds = sorted(lm_gold_cache.get(lm, []),
                       key=lambda i: int(i.rsplit("_p", 1)[1])
                       if "_p" in i else -1)[:10]
        add(query=q, domain=dom, gold=golds, category="landmark")

    # labour & tax (both-current domains; split tax acts by date)
    labour_rows = [
        ("gratuity eligibility payment and amount determination",
         ["SSCODE"], "gratuity"),
        ("maternity benefit leave duration", ["SSCODE"], "maternity"),
        ("retrenchment compensation and notice period for workmen",
         ["OSHCODE", "IRCODE"], "retrenchment"),
        ("provident fund contribution employer employee", ["IRCODE"],
         "provident fund"),
        ("equal remuneration for men and women workers", ["WAGECODE"],
         "remuneration"),
        ("factory safety committee duties occupier", ["OSHCODE"],
         "factory safety"),
    ]
    for q, act_hints, cat in labour_rows:
        hits = [cid for cid, c in chunks.items()
                if c["act_short"] in act_hints
                and any(w in (c.get("title") or "").lower()
                        for w in cat.split())][:2]
        if hits:
            add(query=q, domain="labour",
                expected_regimes={"labour": "current"}, gold=hits,
                category="labour")

    tax_rows = [
        ("deduction for life insurance premium under 80C", ["80C"],
         "2025-11-30", "ITA1961"),
        ("long term capital gains transfer of shares", ["capital gains",
         "112"], "2025-08-01", "ITA1961"),
        ("income tax refund procedure delay", ["refund"], "2026-05-20",
         "ITA2025"),
        ("assessment of escaped income best judgement assessment", ["147",
         "escaped"], "2025-12-01", "ITA1961"),
        ("annual value of house property let out", ["house property", "22"],
         "2026-06-15", "ITA2025"),
    ]
    for q, keys, dt, want_act in tax_rows:
        hits = [cid for cid, c in chunks.items()
                if c["act_short"] == want_act
                and any(k in (c.get("title") or "").lower()
                        or k in c.get("section_no", "").lower()
                        for k in keys)][:2]
        if hits:
            regime = "old" if want_act == "ITA1961" else "new"
            add(query=f"{q} (for FY {dt[:4]})", domain="tax",
                incident_date=dt, expected_regimes={"tax": regime},
                gold=hits, category="tax")

    # ask_date routes (past tense, no date)
    for q in [
        "what was the law on cheating when my uncle was duped back then?",
        "which section applied to dowry cases earlier?",
        "bail provisions that used to apply at that time",
        "what did the evidence act say about electronic records before?",
    ]:
        add(query=q, domain="criminal_substantive", expected_route="ask_date",
            gold=["IPC_s420"], category="ask_date")

    # romanised Hindi
    hindi_rows = [
        ("hatya ki saza kya hai March 2023 mein hua tha",
         ["IPC_s302"], "2023-03-01", {"criminal_substantive": "old"},
         ["IPC_s302"]),
        ("March 2024 mein mere saath dhokha hua tha kaunsa section lagega",
         ["IPC_s415", "IPC_s420"], "2024-03-01",
         {"criminal_substantive": "old"}, ["IPC_s420"]),
        ("june 2025 mein cheating hui thi kaunsa kanoon lagega",
         ["BNS_s318"], "2025-06-01", {"criminal_substantive": "new"},
         ["BNS_s318"]),
        ("electronic evidence ka certificate zaroori hai kya",
         ["IEA_s65B"], None, None, []),
        ("gratuity kitne saal baad milta hai", ["SSCODE_s53"], None, None, []),
        ("fir darj karne ka niyam kya tha pehle", ["CRPC_s154"], None,
         None, []),
        ("girftari ke baad kitne ghante mein court jana chahiye",
         ["CRPC_s57"], None, None, []),
        ("anticipatory bail kya hai aur kab milti hai", ["CRPC_s438"],
         None, None, []),
    ]
    for q, gold, dt, reg, rel in hindi_rows:
        add(query=q, lang="hi", domain="criminal_substantive",
            incident_date=dt, expected_regimes=reg, gold=gold, related=rel,
            category="hindi")

    # must-refuse gaps (outside corpus scope)
    for q, note in [
        ("how do I register a private limited company?",
         "company law not ingested"),
        ("compensation claim under the Motor Vehicles Act for accidents",
         "MVA not ingested"),
        ("US visa application process for Indian citizens", "out of scope"),
        ("divorce procedure under Hindu Marriage Act", "HMA not ingested"),
    ]:
        add(query=q, domain="general", must_refuse=True,
            gold=["IPC_s420"], category="gap")

    # ---------------------------------------------------------- autos
    # clean-title section lookups across acts
    per_act_quota = {
        "IPC": 4, "BNS": 4, "CRPC": 3, "BNSS": 3, "IEA": 2, "BSA": 2,
        "ITA1961": 3, "ITA2025": 3, "COI": 2, "IRCODE": 1, "OSHCODE": 1,
        "SSCODE": 1, "WAGECODE": 1,
    }
    seen_titles = set()
    for act, quota in per_act_quota.items():
        pool = [c for c in chunks.values() if c["act_short"] == act
                and clean_title(c.get("title") or "")
                and c["section_no"] not in ("Preamble",)]
        random.shuffle(pool)
        got = 0
        for c in pool:
            key = re.sub(r"\W+", "", (c["title"] or "").lower())[:60]
            if key in seen_titles:
                continue
            seen_titles.add(key)
            sec = c["section_no"]
            q = f"what does section {sec} of {c['act'].split(',')[0]} cover?"
            add(query=q, domain=c["domain"], gold=[c["chunk_id"]],
                related=twin_of(c["chunk_id"]), category="auto_lookup")
            got += 1
            if got >= quota:
                break

    args.out.parent.mkdir(parents=True, exist_ok=True)

    # consistency audit: regime labels must match gold acts
    # (tax splits ITA1961->old / ITA2025->new at the 2026-04-01 cutoff)
    OLD_ACTS = {"IPC", "CRPC", "IEA", "ITA1961"}
    NEW_ACTS = {"BNS", "BNSS", "BSA", "ITA2025"}
    bad = 0
    for r in rows:
        reg = r.get("expected_regimes") or {}
        want = next(iter(reg.values()), None)
        gact = {chunks[i]["act_short"] for i in r["gold_chunk_ids"]}
        if want == "old" and (gact & NEW_ACTS or not gact & OLD_ACTS):
            bad += 1
        if want == "new" and (gact & OLD_ACTS or not gact & NEW_ACTS):
            bad += 1
    if bad:
        raise SystemExit(f"AUDIT FAILED: {bad} rows with mismatched "
                         f"regime/act labels - fix before shipping")

    with args.out.open("w") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    cats: dict[str, int] = {}
    for r in rows:
        cats[r["category"]] = cats.get(r["category"], 0) + 1
    print(f"wrote {len(rows)} -> {args.out}")
    for k, v in sorted(cats.items()):
        print(f"  {v:3d}  {k}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
