"""Recover technology and vintage lost by the archived weather-site selection.

Read-only with respect to source inventories, frozen requests and model results.
The replacement inventory is a candidate register, not a calibrated fleet.
Run with a Python environment containing openpyxl.
"""
from pathlib import Path
from collections import defaultdict
import csv, hashlib, json, math
import openpyxl

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT/'work/research/sources/zenodo_16810831/Global-integrated-Plant-Tracker-July-2025_china.xlsx'
SITES = ROOT/'work/research/prepared/openmeteo_sites_three_provinces.csv'
OUT = ROOT/'outputs/research/revision/weather_site_technology'
PC = 'Subnational unit (state, province)'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def year(value):
    try:
        x = float(value)
        return int(x) if math.isfinite(x) and x.is_integer() else None
    except (TypeError, ValueError):
        return None


def key(province, tech, name, mw, lat, lon):
    return (province, tech, name, round(float(mw), 6), round(float(lat), 6), round(float(lon), 6))


def write_csv(path, rows):
    with path.open('w') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator='\n'); w.writeheader(); w.writerows(rows)


def main():
    OUT.mkdir(exist_ok=True, parents=True)
    wb = openpyxl.load_workbook(SOURCE, read_only=True, data_only=True)
    it = wb['Power facilities'].values; header = next(it)
    lookup = defaultdict(list); candidates = []
    for excel_row, values in enumerate(it, 2):
        r = dict(zip(header, values))
        if r[PC] not in ['Jiangsu', 'Gansu', 'Guizhou'] or r['Type'] not in ['wind', 'solar'] or r['Status'] != 'operating':
            continue
        tech = str(r['Technology'] or 'unknown')
        separated = ('wind_offshore' if tech.lower().startswith('offshore') else
                     'wind_onshore' if tech.lower() == 'onshore' else 'wind_unknown') if r['Type'] == 'wind' else 'solar'
        sy = year(r['Start year'])
        record = dict(source_excel_row=excel_row, unit_id=r['GEM unit/phase ID'],
            province=r[PC], source_type=r['Type'], technology=tech, technology_group=separated,
            name=r['Plant / Project name'], phase=r['Unit / Phase name'], mw=r['Capacity (MW)'],
            lat=r['Latitude'], lon=r['Longitude'], start_year=sy,
            reported_start_year=r['Start year'], status_at_source_release=r['Status'],
            known_start_after_2020=sy is not None and sy > 2020,
            by2020_vintage_candidate=sy is not None and sy <= 2020,
            coordinate_available=r['Latitude'] is not None and r['Longitude'] is not None)
        candidates.append(record)
        if record['coordinate_available']:
            lookup[key(r[PC], r['Type'], record['name'], record['mw'], record['lat'], record['lon'])].append(record)
    wb.close()
    sites = list(csv.DictReader(SITES.open())); matched = []
    for i, s in enumerate(sites, 2):
        options = lookup[key(s['province'],s['tech'],s['name'],s['mw'],s['lat'],s['lon'])]
        if len(options) != 1:
            raise ValueError(f'Site CSV row {i} has {len(options)} source matches; no silent deduplication')
        matched.append(dict(site_csv_row=i, **options[0]))
    summaries = []
    for province, original_tech in sorted({(r['province'],r['source_type']) for r in matched}):
        group = [r for r in matched if r['province']==province and r['source_type']==original_tech]
        total = math.fsum(float(r['mw']) for r in group)
        categories = {}
        for t in sorted({r['technology_group'] for r in group}):
            sub = [r for r in group if r['technology_group']==t]
            categories[t] = dict(rows=len(sub), mw=math.fsum(float(r['mw']) for r in sub))
        late = [r for r in group if r['known_start_after_2020']]
        unknown = [r for r in group if r['start_year'] is None]
        summaries.append(dict(province=province, original_group=original_tech, rows=len(group), mw=total,
            technologies=categories, known_post2020_rows=len(late),
            known_post2020_capacity_fraction=math.fsum(float(r['mw']) for r in late)/total,
            unknown_start_rows=len(unknown)))
    write_csv(OUT/'archived_sites_with_technology_and_vintage.csv', matched)
    candidates.sort(key=lambda r:(r['province'],r['technology_group'],str(r['unit_id'])))
    candidate_path=ROOT/'work/research/prepared/technology_separated_operating_2025_candidate_inventory.csv'
    write_csv(candidate_path, candidates)
    js = next(x for x in summaries if x['province']=='Jiangsu' and x['original_group']=='wind')
    assert js['technologies']['wind_offshore']['rows'] == 20 and len(js['technologies']) == 1
    result = dict(source_workbook_sha256=sha(SOURCE), archived_sites_sha256=sha(SITES),
        code_sha256=sha(Path(__file__)), source_rows_matched=len(matched),
        unique_unit_ids=len({r['unit_id'] for r in matched}), summaries=summaries,
        candidate_rows=len(candidates), candidate_file=str(candidate_path.relative_to(ROOT)),
        candidate_sha256=sha(candidate_path),
        original_selection='largest 20 operating July-2025 units by province and Type; no technology or start-year filter',
        finding='All 20 Jiangsu wind rows are offshore; the old regional runner assigns this series to onwind_pu while keeping offshore on the archive profile.',
        existing_explicit_request_scope='Frozen source-repair plan also uses cell_selection=land at offshore locations. Request setting is not evidence of actual returned cell land/sea mask.',
        current_admission='NOT_ADMITTED_AS_PROVINCIAL_GENERATION_INPUT',
        candidate_limitations=['Operating-in-2025 inventory is not a full 2020 fleet: retired/surviving units and commissioning within 2020 need separate treatment.',
            'Fixed modern geography under historical weather is a scenario, not historical generation reconstruction.',
            'Start-year and technology unknowns retained; no imputation.',
            'Correct labels do not validate coordinates, turbine parameters, grid cells, observed generation or complete capacity coverage.'])
    (OUT/'audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__ == '__main__':
    main()
