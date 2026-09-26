#!/usr/bin/env python3
"""Independent structural verification for the 2026-09-27 literature audit."""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "outputs/research/revision/literature_20260927"


def csv_rows(name: str) -> list[dict]:
    with (OUT / name).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


registry = json.loads((OUT / "literature_registry.json").read_text(encoding="utf-8"))
records = registry["records"]
assert len(records) == 21
assert [record["id"] for record in records] == [f"L{i:02d}" for i in range(1, 22)]
assert len({record["canonical_url"] for record in records}) == 21
assert registry["access_date"] == "2026-09-27"

crossref = json.loads((OUT / "crossref_metadata.json").read_text(encoding="utf-8"))
arxiv = json.loads((OUT / "arxiv_metadata.json").read_text(encoding="utf-8"))
checks = csv_rows("metadata_checks.csv")
assert len(checks) == len(crossref) + len(arxiv)
assert all(row["pass"] == "True" for row in checks)
assert all(float(row["title_token_jaccard"]) >= 0.55 for row in checks)

known_ids = {record["id"] for record in records}
claims = csv_rows("claim_citation_ledger.csv")
for row in claims:
    cited = set(row["support"].split(";"))
    assert cited and cited <= known_ids

novelty = csv_rows("novelty_matrix.csv")
assert len(novelty) == 6
assert any(row["status"] == "not_yet_demonstrated" for row in novelty)
assert any(row["status"] == "overlap_closes_broad_novelty" for row in novelty)

validation = json.loads((OUT / "validation.json").read_text(encoding="utf-8"))
assert validation["total_records"] == 21
assert validation["new_records"] == 5
assert validation["all_metadata_checks_pass"] is True
assert validation["broad_first_claims_remaining"] == 0
assert validation["nature_energy_system_claim_ready"] is False
assert re.search(r"hardware.*held-out", validation["remaining_gate"])

print(json.dumps({
    "checks": 14 + len(checks) + len(claims),
    "records": len(records),
    "metadata_records": len(checks),
    "claim_rows": len(claims),
    "novelty_rows": len(novelty),
    "pass": True,
}))
