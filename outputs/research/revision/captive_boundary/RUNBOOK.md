# Stage 29 source audit and reconstruction

The tracked source access log lists three public institutional URLs, local relative paths, retrieval times, byte counts and SHA256 values. Raw PDF/HTML files are excluded from Git. Download each URL into its recorded path and compare bytes/hash to `evidence_manifest.json`; do not overwrite an existing source or copy an old retrieval time into a new receipt. If a dynamic page differs, preserve the new version separately and audit the difference before modifying admission. The frozen auditor intentionally rejects unmatched versions.

The download receipts required by the auditor are `download_log.json` (the PDF record) and `supplementary_download_log.json` (the two HTML records), under `work/research/sources/captive_boundary_20260923/`. A reconstruction must write receipts for the actual new requests with URL, path, bytes, sha256 and retrieved_utc. Current HTTP failures and changed versions should be retained, not silently bypassed. Requests to the company page via web extraction timed out in this run; a direct standard-library HTTPS fetch succeeded and is the source of the saved bytes. A preliminary downloader import failed because `requests` was absent; standard-library urllib was used instead.

Install/locate `pypdf` and `pdfplumber` in the chosen environment; the versions used are recorded in the evidence manifest. Then, from the repository root:

```bash
python work/research/analysis/audit_captive_generation_boundary.py
```

The script reads only the three pinned sources and the tracked stage-23 oil/gas inventory, and writes this stage's derived audit files. It does not run or import a dispatch solver. Successful recovery can change source-access timestamps and their derived hashes; numeric values and admission states should remain the same. This run used the Codex bundled Python environment, not the stage-27 isolated environment; no claim of second-machine reconstruction is made.

For visual source review, render PDF one-based pages 15, 16, 17 and 157 (printed 14, 15, 16 and 156). Inspect full pages, headers and notes. The first numeric extraction correctly failed because whole-page text interleaved table columns. The final script reads the bordered table and checks its header before comparing its values with pypdf. Both engines agree, and all four pages were visually reviewed.

Expected current result: 48 checks; 12 records and 1,125 MW; two candidate project matches totalling 255 MW; zero records admitted as unconstrained grid supply. Zero admission is an evidence state, not a claim of zero actual generation or flexibility. Empty export/firm-capacity fields are intentional missing values. Candidate identity is not verified unique project identity. The audit ledger is not an enforced solver gate.

The public Changzhou planning PDF URL `https://fgw.changzhou.gov.cn/uploadfile/fgw/2017/0630/20170630163513_19407.pdf` redirected during source screening; cached search content was not admitted. Unrelated Jiugang/Angang and Nantong project search results were not used to change any selected unit.

Next: obtain unique permit/commissioning matches and site/grid boundary, shared-gas and operating evidence, then implement the corresponding constraints in a new experiment. Never run the old provincial batch scripts to populate this audit: they may overwrite frozen results and still use the rejected uniform gas mapping.
