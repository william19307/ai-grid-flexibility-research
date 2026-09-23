"""Audit dated project evidence without overwriting the frozen inventory.

HTML is parsed as data, never executed. Web-extracted Nantong observations are
explicitly separate from the three byte-pinned local primary documents.
"""
import argparse
import csv
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from decimal import Decimal

ROOT = Path(__file__).resolve().parents[3]
EVIDENCE = ROOT / 'outputs/research/revision/ccgt_primary'
INVENTORY = ROOT / 'outputs/research/revision/input_consistency/selected_oil_gas_unit_audit.csv'
INVENTORY_SHA = '21eae3d38864226d5f23b6a3caecafd77f27c515e80dda4f22d6d53412486d07'


class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.text = []
        self.rows = []
        self.row = None
        self.cell = None
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'):
            self.skip += 1
        if tag == 'tr':
            if self.row is not None:
                raise ValueError('Nested table requires separate review')
            self.row = []
        if tag in ('td', 'th') and self.row is not None:
            self.cell = []

    def handle_data(self, data):
        if not self.skip:
            self.text.append(data)
            if self.cell is not None:
                self.cell.append(data)

    def handle_endtag(self, tag):
        if tag in ('script', 'style'):
            self.skip -= 1
        if tag in ('td', 'th') and self.cell is not None:
            self.row.append(''.join(''.join(self.cell).split()))
            self.cell = None
        if tag == 'tr' and self.row is not None:
            self.rows.append(self.row)
            self.row = None


def dump(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--output-dir', type=Path, default=EVIDENCE)
    args = ap.parse_args()
    checks = []

    def check(name, condition):
        if not condition:
            raise ValueError(name)
        checks.append(name)

    sources = json.loads((EVIDENCE / 'source_access_log.json').read_text())
    review = json.loads((EVIDENCE / 'reviewed_events.json').read_text())
    pages = {}
    for source in sources:
        if source['evidence_access'] != 'raw_html':
            continue
        raw = (ROOT / source['path']).read_bytes()
        check(source['source_id'] + '_source_bytes', hashlib.sha256(raw).hexdigest() == source['sha256'])
        charset = re.search(br'charset=["\s]*([\w-]+)', raw[:3000], re.I)
        if charset is None:
            raise ValueError('Undeclared encoding requires review')
        page = Page()
        page.feed(raw.decode(charset.group(1).decode()))
        pages[source['source_id']] = page

    owner = ''.join(''.join(pages['qishuyan_owner'].text).split())
    check('qishuyan_capacity_and_heat_group', all(s in owner for s in (
        '2170MW', 'F级2×390MW', 'E级2×220MW燃机热电联产机组', 'F级2×475MW')))
    check('qishuyan_historical_dates', all(s in owner for s in ('2017年07月27日', '2005年', '2011年、2015年')))
    plan = pages['wuxi_plan'].rows
    indices = [i for i, row in enumerate(plan) if len(row) > 1 and row[1] == '东亚电力（无锡）有限公司']
    check('wuxi_expansion_unique_row', len(indices) == 1)
    i = indices[0]
    check('wuxi_reserve_section_and_expansion', plan[i][2] == '扩建2套400MW级燃气蒸汽联合循环热电联产机组'
          and plan[i-2][1] == '储备项目' and plan[i][3] == '2016~2020')
    mee = pages['wuxi_mee'].rows
    indices = [i for i, row in enumerate(mee) if len(row) > 1 and row[1] == '东亚电力（无锡）燃气电厂2×400MW级项目']
    check('mee_unique_project_row', len(indices) == 1)
    i = indices[0]
    check('mee_project_and_neighbor_boundary', mee[i][0] == '4' and mee[i][2] == '江苏省无锡市'
          and '2×400兆瓦级（F级）燃气－蒸汽联合循环' in mee[i][4]
          and mee[i+1][0] == '5' and '山东国电泰安' in mee[i+1][1])
    check('mee_notice_date_not_url_date', '2012-10-26' in ''.join(pages['wuxi_mee'].text))

    check('frozen_inventory_bytes', hashlib.sha256(INVENTORY.read_bytes()).hexdigest() == INVENTORY_SHA)
    with INVENTORY.open(newline='') as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames
        rows = list(reader)
    check('inventory_identity_and_total', len(rows) == len({r['GEM unit/phase ID'] for r in rows}) == 109
          and sum(Decimal(r['capacity_numeric_MW']) for r in rows) == Decimal(24959))
    events = {e['event_id']: e for e in review['events']}
    check('event_source_references', len(events) == 5 and all(
        set(e['sources']) <= {s['source_id'] for s in sources} for e in events.values()))
    check('no_false_unit_or_parameter_admission', events['nantong_unit2_trial']['assigned_GEM_unit_ID'] is None
          and events['nantong_planned_sequence']['physical_unit_numbers'] is None
          and review['operational_parameter_sets_admitted'] == 0)
    links = {
        'East Asia Power Wuxi Gas power station': ['wuxi_original_proposal', 'wuxi_reserve_expansion'],
        'Huadian Qishuyan Gas power station': ['qishuyan_historical_groups'],
        'Huaneng Nantong power station': ['nantong_planned_sequence', 'nantong_unit2_trial'],
    }
    overlay = []
    for row in rows:
        refs = links.get(row['Plant / Project name'], [])
        overlay.append(dict(row, stage34_event_refs=';'.join(refs),
                            stage34_correspondence='plant_or_capacity_group_candidate_only' if refs else 'not_reviewed_this_stage',
                            stage34_original_fields_changed='false', stage34_dispatch_admitted='false'))
    touched = [r for r in overlay if r['stage34_event_refs']]
    check('reviewed_cohort_scope', len(touched) == 10 and sum(Decimal(r['capacity_numeric_MW']) for r in touched) == 4460)
    check('all_original_values_preserved', all({k: r[k] for k in fields} == old for r, old in zip(overlay, rows)))
    unknown = [r for r in rows if r['Technology'] == 'combined cycle' and r['CHP'] == 'not found']
    check('heat_unknown_not_converted_to_no', len(unknown) == 15 and sum(Decimal(r['capacity_numeric_MW']) for r in unknown) == 5981)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    with (args.output_dir / 'unit_evidence_overlay.csv').open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(overlay[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(overlay)
    dump(args.output_dir / 'validation.json', {
        'schema': 'ccgt_primary_audit_v1', 'passed': len(checks), 'checks': checks,
        'inventory_rows': len(rows), 'inventory_MW': 24959, 'source_pinned_html_count': len(pages),
        'linked_candidate_rows': len(touched), 'linked_candidate_MW': 4460,
        'heat_unknown_rows_remaining': len(unknown), 'heat_unknown_MW_remaining': 5981,
        'operational_parameter_sets_admitted': 0,
        'limit': 'Source bytes, selected boundaries and accounting checks; manual interpretations are not independently proven by these checks. Nantong web observations lack original-byte snapshots.',
        'reviewed_events_sha256': hashlib.sha256((EVIDENCE / 'reviewed_events.json').read_bytes()).hexdigest(),
        'source_log_sha256': hashlib.sha256((EVIDENCE / 'source_access_log.json').read_bytes()).hexdigest(),
    })
    print(json.dumps({'passed': len(checks), 'candidate_rows': len(touched), 'admitted_parameters': 0}))


if __name__ == '__main__':
    main()
