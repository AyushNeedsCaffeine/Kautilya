from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class ActSource:
    act_id: str
    short: str
    full_name: str
    domain: str
    regime: str
    effective_from: date
    effective_to: date | None = None
    repeals: str | None = None
    expected_sections: int | None = None


ACT_REGISTRY: dict[str, ActSource] = {
    src.act_id: src
    for src in [
        ActSource("IND_central_20062", "BNS", "Bharatiya Nyaya Sanhita, 2023",
                  "criminal_substantive", "new", date(2024, 7, 1), None,
                  "IPC 1860", 358),
        ActSource("IND_REP_659_1860", "IPC", "Indian Penal Code, 1860",
                  "criminal_substantive", "old", date(1862, 1, 1), date(2024, 6, 30),
                  None, 511),
        ActSource("IND_central_20099", "BNSS", "Bharatiya Nagarik Suraksha Sanhita, 2023",
                  "criminal_procedure", "new", date(2024, 7, 1), None,
                  "CrPC 1974", 531),
        ActSource("IND_central_20063", "BSA", "Bharatiya Sakshya Adhiniyam, 2023",
                  "evidence", "new", date(2024, 7, 1), None,
                  "Evidence Act 1872", 170),
        ActSource("IND_REP_971_1872", "IEA", "Indian Evidence Act, 1872",
                  "evidence", "old", date(1872, 9, 1), date(2024, 6, 30),
                  None, 167),
        ActSource("IND_central_15793", "WAGECODE", "Code on Wages, 2019",
                  "labour", "current", date(2019, 8, 8), None, None, 69),
        ActSource("IND_central_22040", "IRCODE", "Industrial Relations Code, 2020",
                  "labour", "current", date(2025, 11, 21), None, None, 106),
        ActSource("IND_central_16823", "SSCODE", "Code on Social Security, 2020",
                  "labour", "current", date(2025, 11, 21), None, None, 164),
        ActSource("IND_central_22041", "OSHCODE",
                  "Occupational Safety, Health and Working Conditions Code, 2020",
                  "labour", "current", date(2025, 11, 21), None, None, 143),
        ActSource("IND_central_2435", "ITA1961", "Income-tax Act, 1961",
                  "tax", "current", date(1962, 4, 1), None, None, 298),
    ]
}

DOMAINS = sorted({s.domain for s in ACT_REGISTRY.values()})
