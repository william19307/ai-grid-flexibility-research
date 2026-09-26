#!/usr/bin/env python3
"""Download and audit the pinned open-access Caprara et al. 2026 PDF."""

from __future__ import annotations

import hashlib
import json
import tempfile
import urllib.request
from pathlib import Path

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "outputs/research/revision/literature_20260927/caprara_fulltext_audit.json"
ITEM_UUID = "c15cab92-e0eb-4124-852d-e02e1dde9bdc"
BITSTREAM_UUID = "e87ee20a-d65c-451d-8023-ef0bc3ec3325"
ITEM_API = f"https://upcommons.upc.edu/server/api/core/items/{ITEM_UUID}"
CONTENT_URL = f"https://upcommons.upc.edu/server/api/core/bitstreams/{BITSTREAM_UUID}/content"
EXPECTED_SIZE = 9_261_880
EXPECTED_MD5 = "c4691772b88d0da335d034fde0dbbe35"
EXPECTED_SHA256 = "9afe7c3efe6fb986de0c95cf524c3309255447306258c7e2a378a53d35da78a6"
USER_AGENT = "ai-grid-flexibility-research/1.0 (mailto:qkfp0742@leeds.ac.uk)"


def fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=90) as response:
        return response.read()


def compact(text: str) -> str:
    return " ".join(text.split()).lower()


item = json.loads(fetch(ITEM_API))
assert item["uuid"] == ITEM_UUID
assert item["handle"] == "2117/472510"

pdf_bytes = fetch(CONTENT_URL)
assert len(pdf_bytes) == EXPECTED_SIZE
assert hashlib.md5(pdf_bytes).hexdigest() == EXPECTED_MD5
assert hashlib.sha256(pdf_bytes).hexdigest() == EXPECTED_SHA256

with tempfile.TemporaryDirectory() as folder:
    path = Path(folder) / "paper.pdf"
    path.write_bytes(pdf_bytes)
    reader = PdfReader(path)
    assert len(reader.pages) == 27
    pages = [compact(page.extract_text() or "") for page in reader.pages]

full_text = " ".join(pages)
anchors = {
    "gpu_side_boundary": "quantifies the flexibility of the modeled it-side power only",
    "non_it_not_modeled": "non-it subsystems such as cooling, ups, and auxiliary infrastructure are discussed for context but are not explicitly modeled",
    "latency_proxy": "observed variance in task latency values suggests that a substantial share of the workload can be used for deferral-based flexibility provision",
    "no_measured_power": "the alibaba trace does not provide measured per-device power telemetry",
    "first_order_power": "first-order approximation of gpu-side it power",
    "rebound_missing": "rescheduling rebound — is not modeled in the present framework",
    "dependencies_missing": "does not model inter-task dependencies within multi-task jobs",
    "delay_cost_assumption": "incurs no additional costs based on historical observations of similar task waiting times",
}
checks = {name: phrase in full_text for name, phrase in anchors.items()}
assert all(checks.values()), checks

audit = {
    "access_date": "2026-09-27",
    "citation": "Caprara et al., International Journal of Electrical Power & Energy Systems 178, 111940 (2026)",
    "doi": "10.1016/j.ijepes.2026.111940",
    "repository_item_api": ITEM_API,
    "repository_handle": "https://hdl.handle.net/2117/472510",
    "bitstream_content_url": CONTENT_URL,
    "bitstream_uuid": BITSTREAM_UUID,
    "filename": "1-s2.0-S0142061526003820-main.pdf",
    "license": "CC BY 4.0 as reported by the repository/publisher record",
    "bytes": len(pdf_bytes),
    "md5": EXPECTED_MD5,
    "sha256": EXPECTED_SHA256,
    "pages": len(pages),
    "text_anchor_checks": checks,
    "checks_passed": sum(checks.values()) + 5,
    "interpretation": {
        "overlap": "production trace, latency-proxy classification, task-duration uncertainty and modeled response-window deferral are prior art",
        "limits": "GPU-side linear power estimate; no measured facility boundary, rescheduling rebound or task dependencies; historical waiting supports an assumed no-extra-cost deferral rule rather than an observed contract deadline",
        "remaining_manuscript_contribution": "same fixed cohort factorial attribution under explicit completion benchmarks plus translation-boundary tests",
    },
}
OUT.write_text(json.dumps(audit, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print(json.dumps({"checks_passed": audit["checks_passed"], "pages": audit["pages"], "pass": True}))
