"""Read-only reconstruction of legacy 2030 input selection; no dispatch rerun.

Writes only revision/input_consistency. Source inventories are candidates, not
observed 2030 fleets. Independent OOXML parsing checks the selected gas records.
"""
from pathlib import Path
from decimal import Decimal, InvalidOperation
import hashlib
import json
import posixpath
import zipfile
import xml.etree.ElementTree as ET
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'outputs/research/revision/input_consistency'
RAW = ROOT / 'work/research/sources/zenodo_16810831/Global-integrated-Plant-Tracker-July-2025_china.xlsx'
PREP = ROOT / 'work/research/prepared/plant_tracker_2025_unit_inventory.csv'
SRC = ROOT / 'work/research/sources/zenodo_13987282/selected/data'
FROZEN = ROOT / 'outputs/research/tables/gem_fleet_three_provinces_2020_2030.csv'
PROVS = ['Gansu', 'Jiangsu', 'Guizhou']
TYPES = ['coal', 'oil/gas', 'nuclear', 'hydropower', 'wind', 'solar']
ID = 'GEM unit/phase ID'
NS = {'s': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def xml_records(path, wanted_ids):
    """Resolve the named worksheet; no pandas/openpyxl values reused."""
    with zipfile.ZipFile(path) as z:
        strings = []
        if 'xl/sharedStrings.xml' in z.namelist():
            strings = [''.join(n.itertext()) for n in ET.fromstring(z.read('xl/sharedStrings.xml'))]
        workbook = ET.fromstring(z.read('xl/workbook.xml'))
        sheet = next(s for s in workbook.find('s:sheets', NS) if s.attrib['name'] == 'Power facilities')
        rel_id = sheet.attrib['{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id']
        rel = next(r for r in ET.fromstring(z.read('xl/_rels/workbook.xml.rels')) if r.attrib['Id'] == rel_id)
        target = rel.attrib['Target']
        target = target.lstrip('/') if target.startswith('/') else posixpath.normpath('xl/' + target)
        headers, records = {}, {}
        with z.open(target) as stream:
            for _, elem in ET.iterparse(stream, events=['end']):
                if elem.tag != '{' + NS['s'] + '}row':
                    continue
                cells = {}
                for cell in elem:
                    col = ''.join(c for c in cell.attrib['r'] if c.isalpha())
                    typ = cell.attrib.get('t')
                    value = cell.find('s:v', NS)
                    text = '' if value is None else (value.text or '')
                    if typ == 's':
                        text = strings[int(text)]
                    elif typ == 'inlineStr':
                        text = ''.join(n.text or '' for n in cell.findall('.//s:t', NS))
                    cells[col] = text
                if ID in cells.values():
                    headers = cells
                elif headers:
                    row = {name: cells.get(col, '') for col, name in headers.items()}
                    if row.get(ID) in wanted_ids:
                        assert row[ID] not in records
                        records[row[ID]] = row
                elem.clear()
    assert set(records) == set(wanted_ids)
    return records


def clean(value):
    return '' if pd.isna(value) else str(value)


def same(a, b):
    a, b = clean(a), clean(b)
    if a == b:
        return True
    try:
        return Decimal(a) == Decimal(b)
    except InvalidOperation:
        return False


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    raw = pd.read_excel(RAW, sheet_name='Power facilities')
    empty = raw.isna().all(axis=1)
    raw = raw.loc[~empty].copy()
    assert raw[ID].notna().all() and raw[ID].is_unique
    d = pd.read_csv(PREP, low_memory=False)
    assert d[ID].is_unique
    d = d[d.province_source_label.isin(PROVS)].copy()
    fields = ['Technology', 'Fuel', 'CHP', 'Captive Industry Type', 'Captive Industry Use', 'Captive Non Industry Use']
    d = d.merge(raw[[ID] + fields], on=ID, how='left', validate='one_to_one', indicator=True)
    assert d['_merge'].eq('both').all()
    d.drop(columns='_merge', inplace=True)
    # Exactly reproduce historical membership, including its unresolved assumptions.
    d['selected_legacy_2030'] = (d.Status.isin(['operating', 'construction']) &
        d.start_year_numeric.le(2030) & (d.retired_year_numeric.isna() | d.retired_year_numeric.gt(2030)))
    frozen = pd.read_csv(FROZEN).set_index(['province', 'type'])
    rows = []
    for p in PROVS:
        for typ in TYPES:
            x = d[(d.province_source_label == p) & (d.Type == typ)]
            selected = x[x.selected_legacy_2030]
            assert abs(selected.capacity_numeric_MW.sum() - frozen.loc[(p, typ), 'mw_2030_operating_plus_construction']) < 1e-6
            assert len(selected) == frozen.loc[(p, typ), 'units_2030']
            active = x[x.Status.isin(['operating', 'construction'])]
            unknown = active[active.start_year_numeric.isna()]
            excluded = active[~active.selected_legacy_2030 & active.start_year_numeric.notna()]
            assert len(active) == len(selected) + len(unknown) + len(excluded)
            assert abs(active.capacity_numeric_MW.sum() - sum(t.capacity_numeric_MW.sum() for t in [selected, unknown, excluded])) < 1e-6
            rows.append(dict(province=p, type=typ, selected_units=len(selected), selected_MW=selected.capacity_numeric_MW.sum(),
                selected_operating_MW=selected.loc[selected.Status.eq('operating'), 'capacity_numeric_MW'].sum(),
                selected_construction_MW=selected.loc[selected.Status.eq('construction'), 'capacity_numeric_MW'].sum(),
                selected_unknown_retirement_units=int(selected.retired_year_numeric.isna().sum()),
                selected_unknown_retirement_MW=selected.loc[selected.retired_year_numeric.isna(), 'capacity_numeric_MW'].sum(),
                excluded_operating_unknown_start_MW=unknown.loc[unknown.Status.eq('operating'), 'capacity_numeric_MW'].sum(),
                excluded_construction_unknown_start_MW=unknown.loc[unknown.Status.eq('construction'), 'capacity_numeric_MW'].sum(),
                other_excluded_active_MW=excluded.capacity_numeric_MW.sum(),
                admission='NOT_ADMITTED_AS_REALIZED_2030'))
    pd.DataFrame(rows).to_csv(OUT / 'fleet_vintage_ledger.csv', index=False, lineterminator='\n')

    gas = d[d.Type.eq('oil/gas') & d.selected_legacy_2030].copy()
    cross = xml_records(RAW, set(gas[ID]))
    source_cols = [ID, 'Type', 'Status', 'Capacity (MW)', 'Start year', 'Retired year', 'Technology', 'Fuel', 'CHP',
                   'Captive Industry Type', 'Captive Industry Use', 'Captive Non Industry Use', 'Subnational unit (state, province)']
    raw_index = raw.set_index(ID, drop=False)
    checked = 0
    for uid, xml in cross.items():
        for col in source_cols:
            assert same(xml[col], raw_index.loc[uid, col]), (uid, col)
            checked += 1
        prepared = gas[gas[ID].eq(uid)].iloc[0]
        for left, right in [('Capacity (MW)', 'capacity_numeric_MW'), ('Start year', 'Start year'), ('Retired year', 'Retired year')]:
            assert same(xml[left], prepared[right]), (uid, left, 'prepared')
        assert xml['Subnational unit (state, province)'] == prepared.province_source_label
    def candidate(row):
        if row.Technology == 'combined cycle' and row.Fuel in ['fossil gas: natural gas', 'fossil gas: LNG']:
            return 'CCGT_FOSSIL_GAS_REQUIRES_HEAT_AND_OPERATION_DATA'
        if 'industrial by-product:' in clean(row.Fuel):
            return 'INDUSTRIAL_BYPRODUCT_REQUIRES_PROCESS_AND_EXPORT_BOUNDARY'
        return 'UNCLASSIFIED_REQUIRES_REVIEW'
    gas['candidate_category'] = gas.apply(candidate, axis=1)
    gas['legacy_mapping'] = 'OCGT_natural_gas_parameters'
    gas['admission'] = 'CANDIDATE_ONLY_NOT_OPERATIONALLY_VALIDATED'
    keep = [ID, 'province_source_label', 'Plant / Project name', 'Unit / Phase name', 'capacity_numeric_MW', 'Status',
            'Start year', 'Retired year'] + fields + ['candidate_category', 'legacy_mapping', 'admission']
    gas[keep].to_csv(OUT / 'selected_oil_gas_unit_audit.csv', index=False, lineterminator='\n')
    gas.groupby(['province_source_label', 'Technology', 'Fuel'], dropna=False).agg(
        units=(ID, 'count'), capacity_MW=('capacity_numeric_MW', 'sum')).reset_index().to_csv(
        OUT / 'oil_gas_technology_summary.csv', index=False, lineterminator='\n')

    costs = pd.read_csv(SRC / 'costs/costs_2030.csv')
    def cost(t, p):
        x = costs[(costs.technology == t) & (costs.parameter == p)]
        assert len(x) == 1
        return Decimal(str(x.iloc[0].value))
    rates = []
    for typ in ['OCGT', 'CCGT']:
        efficiency = cost(typ, 'efficiency')
        mc = cost('gas', 'fuel') / efficiency + cost(typ, 'VOM')
        emission = cost('gas', 'CO2 intensity') / efficiency
        rates.append(dict(technology=typ, efficiency=float(efficiency), marginal_cost_EUR_per_MWh=float(mc),
                          emissions_t_per_MWh=float(emission), scope='ARCHIVE_PARAMETERS_NOT_MEASURED_OPERATION'))
    pd.DataFrame(rates).to_csv(OUT / 'conditional_technology_rates.csv', index=False, lineterminator='\n')

    archive = pd.read_csv(SRC / 'existing_infrastructure/China_current_capacity.csv')
    archive['Province'] = archive.Province.str.replace(' ', '')
    load = pd.read_csv(SRC / 'load/Province_Load_2020_2060.csv', index_col=0)
    load_rows = []
    for p in PROVS:
        ratio = float(load.loc[p, '2030'] / load.loc[p, '2020'])
        load_rows.append(dict(province=p, archive_2020_value=float(load.loc[p, '2020']), archive_2030_value=float(load.loc[p, '2030']),
            growth_ratio=ratio, normalized_hourly_shape_change=0,
            forecast_excludes_treated_AI_cohort='NOT_ESTABLISHED', dispatch_vs_all_society_scope='UNRECONCILED',
            status='SCENARIO_MULTIPLIER_NOT_VALIDATED_2030_FORECAST'))
    pd.DataFrame(load_rows).to_csv(OUT / 'load_scope_ledger.csv', index=False, lineterminator='\n')
    cap_rows = []
    for p in PROVS:
        x = archive[archive.Province.eq(p)]
        for category, archive_types, gem_type in [('wind', ['onshore wind', 'offshore wind'], 'wind'), ('solar', ['solar PV'], 'solar')]:
            cap_rows.append(dict(province=p, type=category,
                legacy_existing_MW=x.loc[x.Type.isin(archive_types), 'Value'].sum(),
                GEM_selected_2030_MW=float(frozen.loc[(p, gem_type), 'mw_2030_operating_plus_construction']),
                comparison='DIFFERENT_COVERAGE_AND_VINTAGE_NOT_A_CAPACITY_CORRECTION'))
    pd.DataFrame(cap_rows).to_csv(OUT / 'renewable_vintage_comparison.csv', index=False, lineterminator='\n')
    selected = d[d.selected_legacy_2030 & d.Type.isin(TYPES)]
    summary = dict(date='2026-09-23', status='SOURCE_AUDIT_ONLY_NO_PROVINCIAL_REESTIMATE',
        selected_oil_gas_units=len(gas), selected_oil_gas_MW=float(gas.capacity_numeric_MW.sum()),
        ccgt_units=int(gas.Technology.eq('combined cycle').sum()), ccgt_MW=float(gas.loc[gas.Technology.eq('combined cycle'), 'capacity_numeric_MW'].sum()),
        byproduct_units=int(gas.candidate_category.str.startswith('INDUSTRIAL').sum()), byproduct_MW=float(gas.loc[gas.candidate_category.str.startswith('INDUSTRIAL'), 'capacity_numeric_MW'].sum()),
        selected_gas_turbine_label_units=int(gas.Technology.eq('gas turbine').sum()),
        gas_CHP_yes_units=int(gas.CHP.eq('yes').sum()), gas_CHP_yes_MW=float(gas.loc[gas.CHP.eq('yes'), 'capacity_numeric_MW'].sum()),
        selected_all_technology_units=len(selected), unknown_retirement_selected_units=int(selected.retired_year_numeric.isna().sum()),
        independent_xml_fields_checked=checked, frozen_fleet_groups_reconciled=len(rows),
        marginal_cost_OCGT_over_CCGT_percent=(rates[0]['marginal_cost_EUR_per_MWh']/rates[1]['marginal_cost_EUR_per_MWh']-1)*100,
        emissions_OCGT_over_CCGT_percent=(rates[0]['emissions_t_per_MWh']/rates[1]['emissions_t_per_MWh']-1)*100,
        limitations=['No actual 2030 fleet observation', 'Missing retirement year is not proof of operation in 2030',
                    'CHP and captive use may overlap; no inferred export or heat capability',
                    'Archive CCGT rates are a conditional parameter comparison, not new measured costs',
                    'No source supports removing all AI from the demand forecast',
                    'Renewable inventory comparisons have different coverage; no subtraction interpreted as missing capacity'])
    (OUT / 'audit_summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n')
    source_paths = [RAW, PREP, FROZEN, SRC / 'costs/costs_2030.csv', SRC / 'existing_infrastructure/China_current_capacity.csv',
                    SRC / 'load/Province_Load_2020_2060.csv', ROOT / 'work/research/analysis/run_regional_2030_s0_s3.py',
                    ROOT / 'work/research/analysis/run_regional_smoke_s0_s1_s2.py']
    (OUT / 'source_hashes.json').write_text(json.dumps({str(p.relative_to(ROOT)): sha(p) for p in source_paths}, indent=2) + '\n')
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
