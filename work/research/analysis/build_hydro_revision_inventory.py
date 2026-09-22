"""Recover hydro technologies discarded by the original unit inventory.

Preserves original 2030 vintage selection to isolate the technology correction.
This does not resolve unknown commissioning years or forecast completion dates.
"""
from pathlib import Path
import hashlib
import json
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'outputs/research/revision/hydro'
SOURCE = ROOT / 'work/research/sources/zenodo_16810831/Global-integrated-Plant-Tracker-July-2025_china.xlsx'


def build():
    raw = pd.read_excel(SOURCE, sheet_name='Power facilities')
    d = raw.loc[raw.Type.eq('hydropower')].copy()
    d['start'] = pd.to_numeric(d['Start year'], errors='coerce')
    d['retired'] = pd.to_numeric(d['Retired year'], errors='coerce')
    d['capacity_mw'] = pd.to_numeric(d['Capacity (MW)'], errors='raise')
    d['province'] = d['Subnational unit (state, province)'].astype(str).str.replace(' ', '')
    d['technology'] = d.Technology.fillna('unclassified').str.strip().str.lower()
    assert not d['GEM unit/phase ID'].duplicated().any()
    assert d.capacity_mw.ge(0).all()
    d['included_2030'] = (d.Status.isin(['operating', 'construction']) &
                          d.start.le(2030) & (d.retired.isna() | d.retired.gt(2030)))
    d['selection_reason'] = 'excluded_status_or_vintage'
    d.loc[d.start.isna(), 'selection_reason'] = 'unknown_start_year_not_imputed'
    d.loc[d.included_2030, 'selection_reason'] = 'operating_or_construction_start_by_2030'
    columns = ['GEM unit/phase ID', 'Plant / Project name', 'province', 'technology',
               'capacity_mw', 'Status', 'start', 'retired', 'included_2030', 'selection_reason']
    OUT.mkdir(parents=True, exist_ok=True)
    d[columns].to_csv(OUT / 'hydro_units_classified.csv', index=False)
    summary = d[d.included_2030].groupby(['province', 'technology']).agg(
        capacity_mw=('capacity_mw', 'sum'), records=('capacity_mw', 'size')).reset_index()
    summary.to_csv(OUT / 'hydro_2030_by_technology.csv', index=False)
    audit = dict(source=str(SOURCE.relative_to(ROOT)), sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
                 source_doi='10.5281/zenodo.16810831', licence='CC-BY-4.0',
                 technology_field='Technology (source workbook, not inferred from plant name)',
                 included_records=int(d.included_2030.sum()),
                 unknown_start_records=int(d.start.isna().sum()),
                 limitations=['Original vintage selection retained; missing start years remain excluded.',
                              'Storage duration and efficiency are not supplied by this workbook.',
                              'Conventional reservoir and mixed hydro require separate hydrology calibration.'])
    (OUT / 'inventory_manifest.json').write_text(json.dumps(audit, indent=2) + '\n')
    print(summary[summary.province.isin(['Gansu', 'Jiangsu', 'Guizhou'])].to_string(index=False))


if __name__ == '__main__':
    build()
