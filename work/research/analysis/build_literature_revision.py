#!/usr/bin/env python3
"""Build and verify the 2026-09-27 literature delta used by manuscript v1.6.

The script preserves the original screening registry, appends newly identified
primary studies, resolves DOI metadata through Crossref and arXiv metadata
through the arXiv API, and writes a compact novelty/claim ledger.  It does not
infer the absence of a method from an abstract.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
import unicodedata
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "outputs/research/tables/literature_screening.json"
OUT = ROOT / "outputs/research/revision/literature_20260927"
ACCESS_DATE = "2026-09-27"
USER_AGENT = "ai-grid-flexibility-research/1.0 (mailto:qkfp0742@leeds.ac.uk)"


NEW_RECORDS = [
    {
        "id": "L17",
        "title": "Data center workload flexibility for power system demand response: Evidence from Alibaba traces",
        "publication_status": "International Journal of Electrical Power & Energy Systems 178 (2026), 111940",
        "canonical_url": "https://doi.org/10.1016/j.ijepes.2026.111940",
        "inspection_level": "Open-access version-of-record PDF obtained from the university repository; methods, assumptions, results and limitations inspected visually and by two text engines",
        "known_overlap": "Real workload traces, latency-derived deferrability, a service-aware deferral rule and modeled short-notice demand response are already published",
        "next_comparison": "Do not claim first trace-based flexibility quantification; distinguish observed queue latency from a completion contract and compare mode choice with start-time choice on the same fixed cohort while retaining completion and rebound accounting",
        "primary_evidence_url": "https://www.sciencedirect.com/science/article/pii/S0142061526003820",
    },
    {
        "id": "L18",
        "title": "Power-Flexible AI Data Centers: A New Paradigm for Grid-Responsive Compute",
        "publication_status": "arXiv preprint 2606.25098 (2026)",
        "canonical_url": "https://arxiv.org/abs/2606.25098",
        "inspection_level": "Current arXiv metadata and abstract inspected",
        "known_overlap": "A 130 kW deployment reports rapid reduction, sustained curtailment, carbon-aware operation and spatial shifting while preserving priority-job service levels",
        "next_comparison": "Do not claim first multi-form or deployed AI power flexibility; retain a narrower contribution about controlled attribution and grid-translation boundaries",
        "primary_evidence_url": "https://arxiv.org/abs/2606.25098",
    },
    {
        "id": "L19",
        "title": "Spatial LLM Workload Shifting Needs Foresight: Model Commitment for AI Data Center Operation under Power Grid Constraints",
        "publication_status": "arXiv preprint 2609.09787 (2026)",
        "canonical_url": "https://arxiv.org/abs/2609.09787",
        "inspection_level": "Current arXiv metadata and abstract inspected",
        "known_overlap": "Model deployment state, latency and foresight constraints in spatial LLM shifting are explicitly modeled",
        "next_comparison": "Treat topology and model placement as open empirical constraints; aggregate GPU feasibility does not establish deployable migration",
        "primary_evidence_url": "https://arxiv.org/abs/2609.09787",
    },
    {
        "id": "L20",
        "title": "Flexible Training Workloads in Large-Scale AI Data Centers for Transient-Stability Support in Transmission-Constrained Power Systems",
        "publication_status": "arXiv preprint 2608.30901 (2026)",
        "canonical_url": "https://arxiv.org/abs/2608.30901",
        "inspection_level": "Current arXiv metadata and abstract inspected",
        "known_overlap": "Upward AI training response for transient-stability support is already proposed and simulated",
        "next_comparison": "Keep the present paper's hourly energy/capacity claims separate from sub-second or transient-stability services",
        "primary_evidence_url": "https://arxiv.org/abs/2608.30901",
    },
    {
        "id": "L21",
        "title": "Coordinating GPU Data Centers and Power Grid Regulation Service for Exogenous Carbon Benefits",
        "publication_status": "arXiv preprint 2601.22487 (2026)",
        "canonical_url": "https://arxiv.org/abs/2601.22487",
        "inspection_level": "Current arXiv metadata and abstract inspected",
        "known_overlap": "GPU data-center participation in frequency regulation and grid-side carbon accounting are already proposed",
        "next_comparison": "Do not generalize an hourly scheduling result to frequency regulation without response-rate, telemetry and rebound measurements",
        "primary_evidence_url": "https://arxiv.org/abs/2601.22487",
    },
]


NOVELTY_ROWS = [
    {
        "theme": "Field capability",
        "prior_evidence": "L01 and L18 demonstrate software-controlled AI-cluster flexibility with service constraints",
        "remaining_contribution": "No first-demonstration claim remains",
        "manuscript_action": "Frame field capability as established and use it to motivate boundary identification",
        "status": "overlap_closes_broad_novelty",
    },
    {
        "theme": "Trace-based deferral",
        "prior_evidence": "L17 derives deferrability and demand-response estimates from more than one million Alibaba trace tasks",
        "remaining_contribution": "Same-cohort factorial separation of operating mode and start time under an explicit completion benchmark",
        "manuscript_action": "Cite L17 and state that queue latency is not an observed deadline; retain complete-cohort completion and rebound accounting as the narrower difference",
        "status": "narrow_contribution_survives",
    },
    {
        "theme": "Power-system planning",
        "prior_evidence": "L03, L09 and L10 study cost, emissions, interconnection or adequacy effects",
        "remaining_contribution": "Translation tests showing that cohort accounting and nonlinear commitment can reverse or escape simple proxies",
        "manuscript_action": "Present counterexamples as limits on inference, not empirical provincial effects",
        "status": "methodological_contribution_only_until_recompute",
    },
    {
        "theme": "Markets and coordination",
        "prior_evidence": "L02, L08, L13 and L14 already study remuneration, public signals, obligations and endogenous prices",
        "remaining_contribution": "Common-information fixed-response comparison with an explicit counterexample to linear endpoint screening",
        "manuscript_action": "Remove first-mechanism language and require historical forecast vintages for empirical claims",
        "status": "conditional_contribution",
    },
    {
        "theme": "Spatial and fast services",
        "prior_evidence": "L19-L21 model topology/model commitment, transient stability and frequency regulation",
        "remaining_contribution": "None within those timescales in the current evidence",
        "manuscript_action": "Explicitly limit the scope to retrospective hourly scheduling and avoid ancillary-service claims",
        "status": "out_of_scope_requires_measurement",
    },
    {
        "theme": "Empirical grid value",
        "prior_evidence": "Existing studies provide field response or modeled system outcomes, but not this paper's full boundary chain",
        "remaining_contribution": "Potentially a measured-service-to-fixed-investment validation chain on common hardware and aligned provincial inputs",
        "manuscript_action": "Keep Nature Energy system-benefit claim open until hardware, boundary and held-out annual gates pass",
        "status": "not_yet_demonstrated",
    },
]


CLAIM_ROWS = [
    {
        "manuscript_claim": "AI clusters can respond to grid signals while preserving stated service constraints",
        "support": "L01;L18",
        "use": "motivation",
        "limit": "Different hardware and service definitions; not calibration of this study",
    },
    {
        "manuscript_claim": "Trace-based workload deferral has already been quantified",
        "support": "L17",
        "use": "novelty boundary",
        "limit": "Observed queue latency is used as a proxy rather than a contractual deadline",
    },
    {
        "manuscript_claim": "Temporal flexibility can change cost, investment and emissions",
        "support": "L03;L09;L10",
        "use": "literature context",
        "limit": "Model structures and accreditation differ; not evidence for this paper's provinces",
    },
    {
        "manuscript_claim": "Spatiotemporal remuneration and coordination have prior art",
        "support": "L02;L06;L07;L08;L14",
        "use": "literature context",
        "limit": "No claim that every prior paper contains the present completion and accounting tests",
    },
    {
        "manuscript_claim": "Interconnection obligations and verified services have been proposed",
        "support": "L13",
        "use": "policy context",
        "limit": "Commentary proposal rather than validation of this paper's mechanism",
    },
    {
        "manuscript_claim": "Aggregate GPU feasibility does not establish deployable spatial or fast response",
        "support": "L19;L20;L21",
        "use": "scope boundary",
        "limit": "Recent preprints; cited as adjacent work, not settled empirical evidence",
    },
]


def norm(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def get_json(url: str) -> dict:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=45) as response:
        return json.load(response)


def crossref_record(doi: str) -> dict:
    url = "https://api.crossref.org/works/" + urllib.parse.quote(doi, safe="")
    message = get_json(url)["message"]
    date_parts = (message.get("published-print") or message.get("published-online") or message.get("published") or {}).get("date-parts", [[]])[0]
    authors = []
    for author in message.get("author", []):
        name = " ".join(part for part in [author.get("given", ""), author.get("family", "")] if part)
        if name:
            authors.append(name)
    return {
        "doi": message.get("DOI", doi).lower(),
        "title": (message.get("title") or [""])[0],
        "container_title": (message.get("container-title") or [""])[0],
        "published_date_parts": date_parts,
        "authors": authors,
        "type": message.get("type"),
        "publisher": message.get("publisher"),
        "url": message.get("URL"),
    }


def arxiv_records(ids: list[str]) -> dict[str, dict]:
    url = "https://export.arxiv.org/api/query?id_list=" + ",".join(ids)
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=45) as response:
        root = ET.fromstring(response.read())
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    found = {}
    for entry in root.findall("atom:entry", ns):
        identifier = (entry.findtext("atom:id", default="", namespaces=ns).rstrip("/").split("/")[-1]).split("v")[0]
        found[identifier] = {
            "arxiv_id": identifier,
            "title": " ".join(entry.findtext("atom:title", default="", namespaces=ns).split()),
            "published": entry.findtext("atom:published", default="", namespaces=ns),
            "updated": entry.findtext("atom:updated", default="", namespaces=ns),
            "authors": [a.findtext("atom:name", default="", namespaces=ns) for a in entry.findall("atom:author", ns)],
            "summary": " ".join(entry.findtext("atom:summary", default="", namespaces=ns).split()),
        }
    return found


def write_csv(path: Path, rows: list[dict]) -> None:
    fieldnames = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    base_records = json.loads(BASE.read_text(encoding="utf-8"))
    if [record["id"] for record in base_records] != [f"L{i:02d}" for i in range(1, 17)]:
        raise ValueError("Unexpected base literature registry IDs")
    records = base_records + NEW_RECORDS
    if [record["id"] for record in records] != [f"L{i:02d}" for i in range(1, 22)]:
        raise ValueError("Literature IDs must be contiguous and unique")

    doi_pattern = re.compile(r"https://doi\.org/(10\..+)$")
    doi_meta = {}
    doi_checks = []
    for record in records:
        match = doi_pattern.match(record["canonical_url"])
        if not match:
            continue
        doi = match.group(1)
        metadata = crossref_record(doi)
        doi_meta[record["id"]] = metadata
        expected = set(norm(record["title"]).split())
        actual = set(norm(metadata["title"]).split())
        overlap = len(expected & actual) / max(1, len(expected | actual))
        doi_checks.append({
            "id": record["id"],
            "doi": doi,
            "title_token_jaccard": round(overlap, 6),
            "pass": overlap >= 0.55,
        })

    arxiv_ids = []
    arxiv_by_record = {}
    for record in records:
        match = re.match(r"https://arxiv\.org/abs/([0-9.]+)$", record["canonical_url"])
        if match:
            arxiv_ids.append(match.group(1))
            arxiv_by_record[record["id"]] = match.group(1)
    arxiv_meta = arxiv_records(arxiv_ids)
    arxiv_checks = []
    for record in records:
        arxiv_id = arxiv_by_record.get(record["id"])
        if not arxiv_id:
            continue
        metadata = arxiv_meta.get(arxiv_id)
        if metadata is None:
            raise ValueError(f"Missing arXiv metadata for {record['id']}")
        expected = set(norm(record["title"]).split())
        actual = set(norm(metadata["title"]).split())
        overlap = len(expected & actual) / max(1, len(expected | actual))
        arxiv_checks.append({
            "id": record["id"],
            "arxiv_id": arxiv_id,
            "title_token_jaccard": round(overlap, 6),
            "pass": overlap >= 0.55,
        })

    if not all(row["pass"] for row in doi_checks + arxiv_checks):
        raise ValueError("A literature metadata title check failed")

    registry_payload = {
        "access_date": ACCESS_DATE,
        "scope": "Direct work on data-centre or AI-compute flexibility, grid interaction, service constraints or mechanisms; not a systematic review.",
        "interpretation_rule": "Abstract inspection can establish reported content but cannot establish that an unmentioned method is absent.",
        "base_registry_sha256": hashlib.sha256(BASE.read_bytes()).hexdigest(),
        "records": records,
    }
    (OUT / "literature_registry.json").write_text(json.dumps(registry_payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (OUT / "crossref_metadata.json").write_text(json.dumps(doi_meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (OUT / "arxiv_metadata.json").write_text(json.dumps(arxiv_meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    write_csv(OUT / "metadata_checks.csv", doi_checks + arxiv_checks)
    write_csv(OUT / "novelty_matrix.csv", NOVELTY_ROWS)
    write_csv(OUT / "claim_citation_ledger.csv", CLAIM_ROWS)

    validation = {
        "access_date": ACCESS_DATE,
        "base_records": len(base_records),
        "new_records": len(NEW_RECORDS),
        "total_records": len(records),
        "crossref_records": len(doi_meta),
        "arxiv_records": len(arxiv_meta),
        "metadata_checks": len(doi_checks) + len(arxiv_checks),
        "all_metadata_checks_pass": all(row["pass"] for row in doi_checks + arxiv_checks),
        "novelty_rows": len(NOVELTY_ROWS),
        "claim_rows": len(CLAIM_ROWS),
        "broad_first_claims_remaining": 0,
        "supported_current_contribution": "same-cohort factorial attribution under explicit completion benchmarks plus translation-boundary counterexamples",
        "nature_energy_system_claim_ready": False,
        "remaining_gate": "common-hardware service measurements and aligned fixed-investment held-out system validation",
    }
    (OUT / "validation.json").write_text(json.dumps(validation, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(validation, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
