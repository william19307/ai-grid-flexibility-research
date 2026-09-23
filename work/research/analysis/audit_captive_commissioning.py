"""Qualify historical operating evidence without promoting it to dispatch data."""
from pathlib import Path
from html.parser import HTMLParser
from decimal import Decimal
import ast
import csv
import hashlib
import html
import json
import re
import importlib.metadata
from pypdf import PdfReader
import pdfplumber

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / 'work/research/sources/nangang_permits_20260923'
OUT = ROOT / 'outputs/research/revision/captive_commissioning'
PREVIOUS = ROOT / 'outputs/research/revision/captive_boundary/unit_admission_ledger.csv'
PINS = {
    'nangang_annual_2022.pdf': '3a5446e09e95c32ec1d4f3d573dbc941eda2d11d6434b928c83ae419baad90c4',
    'nangang_green_assessment_20211216.pdf': 'e7dda041267d8ec0c0b754ae81df4408f76f5766fafd09ada5f2cfb5d021731e',
    'nangang_supplier_20220804.html': '86d6a0a56bb99fee5ec9a31e8ed87876748aa2ebca89380c18489673348854ca',
    'nangang_supplier_body.js': 'd602d47808a4aeeac0034487277f93c05d6a737487e999c5f1d41137efc55be4',
}


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def compact(s):
    return re.sub(r'\s+', '', s)


class Text(HTMLParser):
    def __init__(self):
        super().__init__(); self.parts = []

    def handle_data(self, data):
        self.parts.append(data)


def main():
    checks = []

    def check(name, condition):
        if not condition:
            raise ValueError(name)
        checks.append(name)

    for name, expected in PINS.items():
        check('source_hash:' + name, sha(SRC / name) == expected)
    receipts = json.loads((SRC / 'download_log.json').read_text())
    by_name = {Path(r['path']).name: r for r in receipts if 'path' in r}
    check('receipts_match', {n: r['sha256'] for n, r in by_name.items()} == PINS)
    raw = (SRC / 'nangang_supplier_20220804.html').read_text()
    body_receipt = by_name['nangang_supplier_body.js']
    check('supplier_page_links_body_resource', body_receipt['url'] in raw)
    script = (SRC / 'nangang_supplier_body.js').read_text()
    # Treat the downloaded JS as a string literal. Never execute remote code.
    check('literal_document_write_wrapper', script.startswith("document.write('") and script.rstrip().endswith("');"))
    decoded = ast.literal_eval(script[len('document.write('):script.rfind(');')])
    parser = Text(); parser.feed(decoded)
    representations = [compact(''.join(parser.parts)), compact(html.unescape(re.sub(r'<[^>]*>', '', decoded)))]
    for token in ['2022-08-04', '15:59', '120MW', '第二台同型号机组', '2020年1月11日', '正式投入商业运行', 'N120-16.7/566/566', 'N120-16.67/566/566']:
        check('supplier_dual_text:' + token, all(token in s for s in representations))

    reader = PdfReader(SRC / 'nangang_annual_2022.pdf')
    check('annual_page_count', len(reader.pages) == 118)
    expected_rows = {
        17: ['6#120MW高效发电机组项目', '444,070,000.00', '已转固', '225,974,864.71', '400,000,000.00', '/', '自筹'],
        66: ['6#120MW高效发电机组项目', '444,070,000.00', '174,025,135.29', '225,974,864.71', '-', '400,000,000.00', '-', '-', '90.08', '已经转固', '-', '-', '', '自筹'],
    }
    with pdfplumber.open(SRC / 'nangang_annual_2022.pdf') as other:
        for page, expected in expected_rows.items():
            rows = [row for table in other.pages[page].extract_tables() for row in table
                    if any('6#120' in (cell or '') for cell in row)]
            check(f'annual_unique_row:{page}', len(rows) == 1)
            check(f'annual_exact_table_row:{page}', [compact(c or '') for c in rows[0]] == expected)
            # pypdf reads columns in a different order but the target row is contiguous.
            text = compact(reader.pages[page].extract_text())
            check(f'annual_independent_text_row:{page}', ''.join(expected) in text)
    # This verifies accounting movements only, not the amount of electrical output.
    check('construction_account_rollforward', Decimal('174025135.29') + Decimal('225974864.71') == Decimal('400000000.00'))
    check('reported_budget_fraction_rounding', (Decimal('400000000') / Decimal('444070000') * 100).quantize(Decimal('.01')) == Decimal('90.08'))
    scanned = PdfReader(SRC / 'nangang_green_assessment_20211216.pdf')
    check('assessment_scanned_not_machine_text', len(scanned.pages) == 18 and not scanned.pages[6].extract_text().strip())

    # These fields were transcribed from full-page renderings; do not describe
    # them as independently verified by two text engines or original permits.
    manual = json.loads((OUT / 'assessment_visual_transcription.json').read_text())
    check('manual_transcription_source_hash', manual['source_sha256'] == PINS['nangang_green_assessment_20211216.pdf'])
    check('manual_transcription_pages', manual['pdf_one_based_pages'] == [6, 7])
    check('manual_transcription_not_operational_parameters', manual['admitted_as_measured_dispatch_parameters'] is False)

    with PREVIOUS.open() as f:
        previous = list(csv.DictReader(f))
    historical_fields = {'primary_candidate_sources', 'identity_status', 'boundary_status'}
    def column(key):
        return 'stage29_' + key if key in historical_fields else key
    rows = []
    for row in previous:
        r = {column(k): v for k, v in row.items()}
        r['chronology_sources'] = ''
        r['historical_operation_evidence'] = 'No additional evidence in stage 30'
        r['exact_commissioning_date_admitted'] = ''
        if r['unit_id'] == 'G100000412573':
            r['chronology_sources'] = 'nangang_annual_2022.pdf;nangang_supplier_body.js;stage29_company_operations'
            r['historical_operation_evidence'] = '2022 Unit 6 operation is corroborated by named company reporting and asset transfer; supplier reports a second 120 MW unit by its declared 2022-08-04 publication date. Exact date and permit-to-unit mapping not established.'
        elif r['unit_id'] == 'G100000412574':
            r['chronology_sources'] = 'nangang_supplier_body.js'
            r['historical_operation_evidence'] = 'Supplier reports first same-model unit commercial operation on 2020-01-11, consistent with inventory 2020 start; supplier does not name Unit 5. Candidate match only.'
        rows.append(r)
    check('ledger_preserves_all_prior_fields', all(all(r[column(k)] == p[k] for k in p) for r, p in zip(rows, previous)) and len(rows) == len(previous) == 12)
    check('no_invented_export_or_ramp_parameters', all(r['export_limit_MW'] == r['firm_flexible_capacity_MW'] == r['exact_commissioning_date_admitted'] == '' for r in rows))
    with (OUT / 'unit_evidence_overlay.csv').open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator='\n'); w.writeheader(); w.writerows(rows)
    results = {
        'checks_passed': len(checks), 'checks': checks,
        'source_interpretation': 'Historical operating existence and chronology, not meter-level flexibility validation',
        'corroborated_named_2022_unit': 'G100000412573',
        'additional_first_unit_candidate': 'G100000412574',
        'new_qualified_dispatch_parameter_sets': 0, 'new_dispatch_runs': 0,
        'unit6_reported_2022_budget_CNY': '444070000.00',
        'unit6_reported_2022_transfer_to_fixed_assets_CNY': '400000000.00',
        'budget_scope_warning': 'Do not resolve earlier CNY 471m vs CNY 430m by assuming tax or scope equivalence. Annual report notes investments exclude tax; exact bridge remains unavailable.',
        'manual_review_warning': 'The scanned assessment is visually transcribed, not independently OCR-verified. Its reported permit metadata are not downloaded permit originals.',
    }
    (OUT / 'audit_results.json').write_text(json.dumps(results, ensure_ascii=False, indent=2) + '\n')
    (OUT / 'source_access_log.json').write_text(json.dumps(receipts, ensure_ascii=False, indent=2) + '\n')
    outputs = ['assessment_visual_transcription.json', 'unit_evidence_overlay.csv', 'audit_results.json', 'source_access_log.json']
    manifest = {
        'inputs': {str(p.relative_to(ROOT)): sha(p) for p in [PREVIOUS, *(SRC / n for n in PINS)]},
        'code': {str(Path(__file__).relative_to(ROOT)): sha(Path(__file__))},
        'outputs': {n: sha(OUT / n) for n in outputs},
        'dependencies': {n: importlib.metadata.version(n) for n in ['pypdf', 'pdfplumber']},
        'visual_review': {'annual_pdf_pages': [18, 67], 'annual_printed_pages': [24, 122], 'assessment_pdf_pages': [6, 7], 'assessment_printed_pages': [4, 5]},
    }
    (OUT / 'evidence_manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'checks_passed': len(checks), 'new_dispatch_parameter_sets': 0}))


if __name__ == '__main__':
    main()
