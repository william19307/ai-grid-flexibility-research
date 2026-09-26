#!/usr/bin/env python3
"""Independent citation, claim-boundary and DOCX checks for manuscript v1.6."""

from __future__ import annotations

import json
import re
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
FOLDER = ROOT / "outputs/research/revision/manuscript_v1.6"
MARKDOWN = FOLDER / "core_paper_en_v1.6_review.md"
DOCX = FOLDER / "core_paper_en_v1.6_review.docx"
REGISTRY = ROOT / "outputs/research/revision/literature_20260927/literature_registry.json"


def expand_citations(text: str) -> list[int]:
    values = []
    for match in re.finditer(r"\[([0-9,–-]+)\]", text):
        for token in match.group(1).split(","):
            if "–" in token or "-" in token:
                separator = "–" if "–" in token else "-"
                left, right = map(int, token.split(separator))
                values.extend(range(left, right + 1))
            else:
                values.append(int(token))
    return values


text = MARKDOWN.read_text(encoding="utf-8")
body, reference_tail = text.split("## References\n", 1)
reference_text, evidence_tail = reference_tail.split("## Evidence register\n", 1)
references = {
    int(number): value.strip()
    for number, value in re.findall(r"(?ms)^(\d+)\. (.*?)(?=^\d+\. |\Z)", reference_text)
}
assert list(references) == list(range(1, 24))

cited = expand_citations(body)
assert set(cited) == set(references)
first_order = []
for number in cited:
    if number not in first_order:
        first_order.append(number)
assert first_order == list(references)

registry = json.loads(REGISTRY.read_text(encoding="utf-8"))["records"]
canonical = {record["id"]: record["canonical_url"] for record in registry}
expected_links = {
    1: canonical["L01"],
    2: canonical["L18"],
    3: canonical["L17"],
    5: canonical["L09"],
    7: canonical["L06"],
    8: canonical["L07"],
    9: canonical["L12"],
    10: canonical["L13"],
    11: canonical["L02"],
    12: canonical["L08"],
    17: canonical["L19"],
    18: canonical["L16"],
}
for number, link in expected_links.items():
    assert link in references[number], (number, link)

for number, doi in {
    4: "10.1016/j.isci.2026.116497",
    6: "10.21203/rs.3.rs-9829457/v1",
    19: "10.1002/qj.3803",
    20: "10.5281/zenodo.7970649",
    21: "10.5281/zenodo.8322210",
    22: "10.5281/zenodo.13987282",
    23: "10.5281/zenodo.16810831",
}.items():
    assert doi.lower() in references[number].lower(), (number, doi)

assert "510780e9ead27698e33cedf24df5a5a171a8f11b" in body
assert len(re.findall(r"(?m)^E\d+\.", evidence_tail)) == 7
assert "nature_energy_system_claim_ready" not in text
for disallowed in (
    "13.6–28.5%",
    "9.5 GW",
    "within 2.6%",
    "deliver most of the grid value",
):
    assert disallowed not in body

novelty_first_sentences = [
    sentence for sentence in re.split(r"(?<=[.!?])\s+", body)
    if re.search(r"\bclaim of first\b", sentence, flags=re.IGNORECASE)
]
assert len(novelty_first_sentences) == 1
assert "make no claim of first" in novelty_first_sentences[0].lower()

assert DOCX.is_file() and DOCX.stat().st_size > 50_000
with zipfile.ZipFile(DOCX) as archive:
    names = set(archive.namelist())
    document_xml = archive.read("word/document.xml").decode("utf-8")
    core_xml = archive.read("docProps/core.xml").decode("utf-8")
    assert "Revision v1.6 literature-integrated review edition" in core_xml
    assert document_xml.count("<w:tbl>") == 2
    media = [name for name in names if name.startswith("word/media/")]
    assert len(media) == 1
    assert "References" in document_xml and "Evidence register" in document_xml

result = {
    "references": len(references),
    "cited_references": len(set(cited)),
    "registry_links_checked": len(expected_links),
    "additional_dois_checked": 7,
    "evidence_entries": 7,
    "tables": 2,
    "media": 1,
    "positive_broad_first_claims": 0,
    "pass": True,
}
print(json.dumps(result))
