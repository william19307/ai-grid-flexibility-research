#!/usr/bin/env python3
"""Verify the current paper package and write its non-self-referential manifest."""

from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
PACKAGE = ROOT / "outputs/research/current_paper_20260927"

SOURCE_MATCHES = {
    "02_original_submission_v1.4/core_paper_en_v1.4.md": "outputs/research/manuscript/core_paper_en_v1.4.md",
    "02_original_submission_v1.4/core_paper_en_v1.4.docx": "outputs/research/manuscript/docx/core_paper_en_v1.4.docx",
    "02_original_submission_v1.4/supplementary_information_v1.4.md": "outputs/research/manuscript/supplementary_information_v1.4.md",
    "02_original_submission_v1.4/supplementary_information_v1.4.docx": "outputs/research/manuscript/docx/supplementary_information_v1.4.docx",
    "02_original_submission_v1.4/supplementary_information_v1.4.pdf": "outputs/research/manuscript/docx/supplementary_information_v1.4.pdf",
    "02_original_submission_v1.4/cover_letter_nature_energy.md": "outputs/research/manuscript/cover_letter_nature_energy.md",
    "02_original_submission_v1.4/cover_letter_nature_energy.docx": "outputs/research/manuscript/docx/cover_letter_nature_energy.docx",
    "02_original_submission_v1.4/supplementary_data_1.xlsx": "outputs/research/manuscript/supplementary_data_1.xlsx",
    "01_current_revision/figures/fig1_policy_attribution.png": "outputs/research/revision/policy/figures/policy_attribution_bounds.png",
    "01_current_revision/figures/figS1_quarterly_diagnostic.png": "outputs/research/revision/rudong_h2_quarterly/quarterly_diagnostic.png",
}

for source in sorted((ROOT / "outputs/research/figures/submission").glob("*")):
    if source.is_file() and source.suffix.lower() != ".svg":
        SOURCE_MATCHES[f"02_original_submission_v1.4/figures/{source.name}"] = source.relative_to(ROOT).as_posix()

for source in sorted((ROOT / "outputs/research/revision").glob("*methods_draft.md")):
    SOURCE_MATCHES[f"03_research_records/methods/{source.name}"] = source.relative_to(ROOT).as_posix()

for source in sorted((ROOT / "outputs/research/revision").glob("阶段*.md")):
    SOURCE_MATCHES[f"03_research_records/stages/{source.name}"] = source.relative_to(ROOT).as_posix()

SOURCE_MATCHES.update({
    "03_research_records/CURRENT_CLAIM_STATUS.md": "outputs/research/revision/CURRENT_CLAIM_STATUS.md",
    "03_research_records/REVISION_STATUS.md": "outputs/research/revision/REVISION_STATUS.md",
    "03_research_records/HANDOFF.md": "HANDOFF.md",
    "03_research_records/RESEARCH_LOG.md": "RESEARCH_LOG.md",
    "03_research_records/REPRODUCE.md": "REPRODUCE.md",
    "03_research_records/SYNC_MANIFEST.md": "SYNC_MANIFEST.md",
})


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def category(relative: str) -> str:
    if relative == "00_阅读说明.md":
        return "package_guide"
    if relative.startswith("01_current_revision/"):
        return "current_review_manuscript"
    if relative.startswith("02_original_submission_v1.4/"):
        return "historical_submission_archive"
    if relative.startswith("03_research_records/"):
        return "research_record_snapshot"
    return "other"


def verify_docx(relative: str, expected_equations: int, expected_tables: int, required_phrases):
    path = PACKAGE / relative
    with zipfile.ZipFile(path) as archive:
        document_xml = archive.read("word/document.xml").decode("utf-8")
        media = [name for name in archive.namelist() if name.startswith("word/media/")]
    equation_count = document_xml.count("<m:oMath>")
    table_count = document_xml.count("<w:tbl>")
    forbidden = ("[[EQ_", "\\frac", "$$")
    if equation_count != expected_equations:
        raise SystemExit(f"{relative}: expected {expected_equations} equations, found {equation_count}")
    if table_count != expected_tables:
        raise SystemExit(f"{relative}: expected {expected_tables} tables, found {table_count}")
    if any(token in document_xml for token in forbidden):
        raise SystemExit(f"{relative}: raw equation source remains in document XML")
    for phrase in required_phrases:
        if phrase not in document_xml:
            raise SystemExit(f"{relative}: missing required phrase {phrase!r}")
    return {"equations": equation_count, "tables": table_count, "embedded_media": len(media)}


def main() -> int:
    failures = []
    for relative, source_relative in SOURCE_MATCHES.items():
        packaged = PACKAGE / relative
        source = ROOT / source_relative
        if not packaged.is_file() or not source.is_file():
            failures.append(f"missing source pair: {relative} <- {source_relative}")
            continue
        if digest(packaged) != digest(source):
            failures.append(f"byte mismatch: {relative} <- {source_relative}")
    if failures:
        raise SystemExit("\n".join(failures))

    main_docx = verify_docx(
        "01_current_revision/core_paper_en_v1.5_review.docx",
        expected_equations=0,
        expected_tables=2,
        required_phrases=("Service constraints", "Manuscript status.", "Data and code availability", "Figure 1."),
    )
    si_docx = verify_docx(
        "01_current_revision/supplementary_information_v1.5_review.docx",
        expected_equations=5,
        expected_tables=1,
        required_phrases=("Supplementary methods", "S9 Validation", "Figure S1."),
    )

    files = []
    for path in sorted(PACKAGE.rglob("*")):
        if not path.is_file() or path.name == "MANIFEST.json":
            continue
        relative = path.relative_to(PACKAGE).as_posix()
        item = {
            "path": relative,
            "bytes": path.stat().st_size,
            "sha256": digest(path),
            "category": category(relative),
        }
        if relative in SOURCE_MATCHES:
            item["byte_identical_to"] = SOURCE_MATCHES[relative]
        files.append(item)

    payload = {
        "schema_version": 1,
        "package": "current_paper_20260927",
        "prepared_date": "2026-09-27",
        "evidence_through_revision_stage": 35,
        "evidence_date": "2026-09-23",
        "evidence_base_commit": "f4bd66b564e50d0a7e30d5f4cca6ebe522b5df33",
        "branch": "codex/research-evidence-revision",
        "manifest_scope": "All package files except MANIFEST.json itself; the adjacent ZIP is also excluded.",
        "file_count": len(files),
        "files": files,
    }
    target = PACKAGE / "MANIFEST.json"
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {target} with {len(files)} entries")
    print(f"main DOCX: {main_docx}")
    print(f"supplement DOCX: {si_docx}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
