#!/usr/bin/env python3
"""Independent citation, evidence-boundary and DOCX checks for manuscript v1.7."""

from __future__ import annotations

import csv
import json
import re
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
FOLDER = ROOT / "outputs/research/revision/manuscript_v1.7"
MARKDOWN = FOLDER / "core_paper_en_v1.7_review.md"
DOCX = FOLDER / "core_paper_en_v1.7_review.docx"
POWER = ROOT / "outputs/research/revision/mlperf_power_admission"


def expand(text: str) -> list[int]:
    out: list[int] = []
    for match in re.finditer(r"\[([0-9,–-]+)\]", text):
        for token in match.group(1).split(","):
            if "–" in token or "-" in token:
                sep = "–" if "–" in token else "-"
                left, right = map(int, token.split(sep))
                out.extend(range(left, right + 1))
            else:
                out.append(int(token))
    return out


text = MARKDOWN.read_text(encoding="utf-8")
body, tail = text.split("## References\n", 1)
refs, evidence = tail.split("## Evidence register\n", 1)
reference_numbers = [int(x) for x in re.findall(r"(?m)^(\d+)\. ", refs)]
assert reference_numbers == list(range(1, 27))
cited = expand(body)
assert set(cited) == set(reference_numbers)
first: list[int] = []
for value in cited:
    if value not in first:
        first.append(value)
assert first == reference_numbers
assert "10.1038/s41597-026-07496-6" in refs
assert "343c3d2cb03f2ae02b1023a44e4a45ba4b8422ef" in refs
assert "power_measurement.adoc" in refs
assert "b6da0c7" in body
assert len(re.findall(r"(?m)^E\d+\.", evidence)) == 8
assert "65.13–82.03%" in body and "3.777–5.377 kW" in body
assert "cannot identify the change in whole-node power" in body
for disallowed in ("13.6–28.5%", "9.5 GW", "deliver most of the grid value"):
    assert disallowed not in body

power_summary = json.loads((POWER / "audit_summary.json").read_text())
power_rows = list(csv.DictReader((POWER / "matched_results.csv").open()))
assert len(power_rows) == 24
assert power_summary["whole_node_energy_saving_computable"] is False
assert power_summary["standard_system_power_rows"] == 0

assert DOCX.is_file() and DOCX.stat().st_size > 50_000
with zipfile.ZipFile(DOCX) as archive:
    document = archive.read("word/document.xml").decode("utf-8")
    core = archive.read("docProps/core.xml").decode("utf-8")
    assert "Revision v1.7 power-boundary review edition" in core
    assert document.count("<w:tbl>") == 2
    assert len([n for n in archive.namelist() if n.startswith("word/media/")]) == 1

result = {
    "references": len(reference_numbers),
    "cited_references": len(set(cited)),
    "evidence_entries": 8,
    "mlperf_rows": len(power_rows),
    "tables": 2,
    "media": 1,
    "whole_node_savings_claim": False,
    "pass": True,
}
print(json.dumps(result))
