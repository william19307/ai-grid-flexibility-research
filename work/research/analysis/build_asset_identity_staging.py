"""Rebuild source identity evidence and an explicitly adjudicated asset view."""
import argparse
import csv
from decimal import Decimal
import hashlib
from html.parser import HTMLParser
import json
import math
from pathlib import Path
import re
import sys
from urllib.parse import urlparse
import openpyxl

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'work/research/inputs'))
from asset_identity import resolve_pinned_file

OUT = ROOT / 'outputs/research/revision/asset_identity'
WORKBOOK = ROOT / 'work/research/sources/zenodo_16810831/Global-integrated-Plant-Tracker-July-2025_china.xlsx'
WORKBOOK_SHA = '4ed14c94a305ec43af9ac33a49134fcee5c1271e2d93d248ab608c7781ea71d0'
STAGING = ROOT / 'outputs/research/revision/thermal_technology/fleet_staging.json'


class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.text, self.links, self.skip = [], [], 0

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'):
            self.skip += 1
        if tag == 'a':
            self.links.extend(v for k, v in attrs if k == 'href' and v)

    def handle_endtag(self, tag):
        if tag in ('script', 'style'):
            self.skip -= 1

    def handle_data(self, data):
        if not self.skip:
            self.text.append(data)


def government_reference(url):
    if url.startswith('https://web.archive.org/web/'):
        match = re.search(r'/web/\d+/(https?://.+)', url)
        if not match:
            return None
        url = match.group(1)
    parsed = urlparse(url)
    if parsed.hostname in ('www.funing.gov.cn', 'funing.yancheng.gov.cn'):
        return 'funing_government:' + parsed.path
    return None


def distance_km(a, b):
    la, lo, lb, lob = map(math.radians, [a['Latitude'], a['Longitude'], b['Latitude'], b['Longitude']])
    q = math.sin((lb-la)/2)**2 + math.cos(la)*math.cos(lb)*math.sin((lob-lo)/2)**2
    return 2*6371*math.asin(math.sqrt(min(1, max(0, q))))


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output-dir', type=Path, default=OUT)
    args = parser.parse_args()
    checks = []

    def check(label, condition):
        if not condition:
            raise ValueError(label)
        checks.append(label)

    log = json.loads((OUT / 'source_access_log.json').read_text())
    decision = json.loads((OUT / 'adjudication.json').read_text())
    pages, source_hashes = {}, {}
    for source in log:
        if source['admission'] != 'raw_snapshot':
            continue
        path = ROOT / source['path']
        raw = path.read_bytes()
        check('raw_source:' + source['source_id'], hashlib.sha256(raw).hexdigest() == source['sha256'])
        source_hashes[source['source_id']] = source['sha256']
        page = Page()
        page.feed(raw.decode('utf-8'))
        pages[source['source_id']] = page
    owner = ''.join(''.join(pages['cnooc_operation'].text).split())
    check('owner_project_configuration_and_chronology', all(s in owner for s in (
        '2022-05-23', '两套10万千瓦级燃气－蒸汽联合循环热电联产机组',
        '2022年1月和5月相继投产', '第二套机组圆满完成96小时满负荷试运行')))
    target = 'funing_government:/art/2020/8/19/art_24074_3414768.html'
    lineage = {}
    for sid in ('gem_thermal_current', 'gem_jiangsu_current'):
        lineage[sid] = [u for u in pages[sid].links if government_reference(u) == target]
        check('shared_project_reference:' + sid, bool(lineage[sid]))
        revision = next(s['page_revision_id'] for s in log if s['source_id'] == sid)
        check('captured_database_revision:' + sid, any('oldid=' + revision in u for u in pages[sid].links))
    manifest = resolve_pinned_file(STAGING, decision)
    source = json.loads(STAGING.read_text())
    by_id = {r['unit_id']: r for r in source['stock']}
    check('workbook_source', hashlib.sha256(WORKBOOK.read_bytes()).hexdigest() == WORKBOOK_SHA)
    workbook = openpyxl.load_workbook(WORKBOOK, read_only=True, data_only=True)
    iterator = workbook['Power facilities'].iter_rows(values_only=True)
    headers = next(iterator)
    id_col = headers.index('GEM unit/phase ID')
    fields = ['Plant / Project name', 'Plant / Project name (local)', 'Plant / Project name (other)',
              'GEM location ID', 'GEM unit/phase ID', 'Latitude', 'Longitude', 'Location accuracy',
              'Owner', 'Parent', 'Hydrogen capable', 'GEM.Wiki URL', 'Capacity (MW)', 'Start year',
              'Technology', 'Fuel', 'CHP', 'Subnational unit (state, province)']
    identities = []
    for row_number, row in enumerate(iterator, 2):
        if row[id_col] in by_id:
            data = dict(zip(headers, row))
            identities.append(dict(workbook_row=row_number, **{k: data[k] for k in fields}))
    workbook.close()
    check('all_selected_source_identities', len(identities) == len(by_id) == len({r['GEM unit/phase ID'] for r in identities}) == 109)
    check('identity_fields_match_staging', all(
        Decimal(str(r['Capacity (MW)'])) == Decimal(by_id[r['GEM unit/phase ID']]['capacity_mw'])
        and r['Plant / Project name'] == by_id[r['GEM unit/phase ID']]['source_record']['Plant / Project name']
        and r['CHP'] == by_id[r['GEM unit/phase ID']]['source_record']['CHP']
        for r in identities))
    # Diagnostic only: this screen cannot resolve aliases or certify completeness.
    screened = {}
    for i, a in enumerate(identities):
        for b in identities[i+1:]:
            if a['GEM location ID'] == b['GEM location ID']:
                continue
            if any(a[k] != b[k] for k in ('Capacity (MW)', 'Start year', 'Technology', 'Subnational unit (state, province)')):
                continue
            if not all(isinstance(v, (int, float)) for v in (a['Latitude'], a['Longitude'], b['Latitude'], b['Longitude'])):
                continue
            distance = distance_km(a, b)
            if distance <= 5:
                key = (a['GEM location ID'], b['GEM location ID'])
                item = screened.setdefault(key, dict(projects=[a['Plant / Project name'], b['Plant / Project name']],
                    location_ids=list(key), distance_km=distance, coordinate_accuracy=[a['Location accuracy'], b['Location accuracy']],
                    source_unit_pairs=[]))
                item['source_unit_pairs'].append([a['GEM unit/phase ID'], b['GEM unit/phase ID']])
    args.output_dir.mkdir(parents=True, exist_ok=True)
    manifest['source_staging_path'] = str(STAGING.relative_to(ROOT))
    manifest['adjudication_sha256'] = hashlib.sha256((OUT / 'adjudication.json').read_bytes()).hexdigest()
    manifest['identity_review_source_hashes'] = source_hashes
    dump(args.output_dir / 'asset_candidates.json', manifest)
    dump(args.output_dir / 'selected_identity_fields.json', dict(workbook_sha256=WORKBOOK_SHA, records=identities))
    dump(args.output_dir / 'citation_lineage.json', dict(shared_project_article=target, links=lineage,
        scope='Shared citation supports an alias inference; it is not independent corroboration.', source_hashes=source_hashes))
    dump(args.output_dir / 'identity_screen.json', dict(criteria='Different location IDs; equal province, technology, capacity and start year; distance <= 5 km.',
        use='Candidate screening only; neither a deduplication rule nor a completeness audit.', candidates=list(screened.values())))
    with (args.output_dir / 'capacity_accounting.csv').open('w', newline='') as f:
        writer = csv.writer(f, lineterminator='\n')
        writer.writerow(['view', 'records_or_assets', 'capacity_mw', 'scope'])
        writer.writerow(['frozen_inventory', len(source['stock']), manifest['source_capacity_mw'], 'source rows, not independently verified distinct assets'])
        writer.writerow(['reviewed_alias_asset_view', len(manifest['asset_candidates']), manifest['resolved_candidate_capacity_mw'], 'research identity inference; no operating admission'])
        writer.writerow(['difference', len(source['stock'])-len(manifest['asset_candidates']), manifest['alias_counting_difference_mw'], 'only Funing duplicate-counting correction'])
    dump(args.output_dir / 'source_validation.json', dict(passed=len(checks), checks=checks,
        source_sha256=source_hashes, workbook_sha256=WORKBOOK_SHA,
        scope='Source bytes, reference lineage and preserved metadata; semantic identity remains an explicit research adjudication.'))
    print(json.dumps(dict(checks=len(checks), source_rows=len(source['stock']), candidate_assets=len(manifest['asset_candidates']),
        candidate_capacity_mw=manifest['resolved_candidate_capacity_mw'], duplicate_counting_mw=manifest['alias_counting_difference_mw'])))


if __name__ == '__main__':
    main()
