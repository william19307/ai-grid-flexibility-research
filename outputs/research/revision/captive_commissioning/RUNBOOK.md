# Stage 30: historical commissioning evidence

This stage strengthens the historical chronology of the two Nangang 120 MW units. It does not admit unit-level operating limits or change any dispatch model. The stage-29 ledger remains frozen. `unit_evidence_overlay.csv` retains its fields, prefixes the old source/identity/boundary descriptions with `stage29_`, and adds explicitly dated chronology evidence.

Recover the four raw files using `source_access_log.json` into the recorded paths under `work/research/sources/nangang_permits_20260923/`. Check the exact hashes in `evidence_manifest.json`. The supplier's HTML is a short shell that directly references a body script on its website provider's CDN; both files are required. The auditor decodes only the `document.write` string literal with `ast.literal_eval`, without executing downloaded JavaScript. A HTTP 200 shell is not by itself evidence of the article text. The current shell may contain a changing public request token; do not replace a mismatched hash silently. Record and review new bytes separately, or recover a matching public archived version.

The recorded 403 acceptance-report result is a failure, not an admitted fifth source. Do not fabricate the missing PDF or use search snippets as measured input. A separate local attempt to retrieve the government-hosted `https://njna.nanjing.gov.cn/njsjbxqglwyh/202504/P020250409638005367880.pdf` also returned HTTP 403; web extraction exceeded its size limit. It was not admitted or saved as a source. No access restriction was bypassed.

The annual report was reached through its issuer page: `https://www.600282.net/Home/SearchListDetails/61f29675-7126-40b0-8a65-fe48e9da4bb4`, which links the exact PDF URL in the access log. It contains two printed pages per PDF page and an appended sustainability section. Relevant PDF pages are 18 and 67; the target tables are on printed pages 24 and 122. Both text engines read the target rows, and full spreads were visually reviewed. The financial line is evidence of asset capitalization, not a turbine output measurement.

The green-bond assessment has no usable text layer on the reviewed pages. View PDF pages 6 and 7 (printed 4 and 5) and review `assessment_visual_transcription.json` before using its reported permit dates. The transcription is a documented visual reading, not a two-engine OCR result. Approximate efficiencies must not be applied as heat-rate curves. The original permit documents and project acceptance report remain unavailable in this stage.

```bash
python work/research/analysis/audit_captive_commissioning.py
```

Requires `pypdf` and `pdfplumber`; the actual versions are recorded in the manifest. Restore actual download receipts locally, including the new retrieval timestamp. Expected result is 30 checks, 12 preserved unit records, strengthened named Unit 6 chronology and a Unit 5 candidate chronology; zero new dispatch parameter sets. These checks verify reading, accounting arithmetic and preservation, not 30 empirical observations. No isolated-environment or second-machine execution was performed here.

Next acquisition targets: original approval identifiers and unit mapping, actual electricity interface/meter records, fuel calorific basis and part-load/start/ramp limits. The scan's reported permit dates provide specific retrieval keys. The 2022-08-04 supplier publication date is not an exact commissioning date or proof of historical decision-time availability. Chronology is retrospective evidence only.
