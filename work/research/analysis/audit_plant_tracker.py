"""Unit inventory audit; does not reconstruct historical capacity automatically."""
from pathlib import Path
import pandas as pd,numpy as np,json,hashlib
ROOT=Path(__file__).resolve().parents[3]
SRC=ROOT/'work/research/sources/zenodo_16810831'
OUT=ROOT/'outputs/research/tables'
file=SRC/'Global-integrated-Plant-Tracker-July-2025_china.xlsx'
raw=pd.read_excel(file,sheet_name='Power facilities')
blank=raw.isna().all(axis=1)
d=raw.loc[~blank].copy()
assert len(d)==35171 and d['GEM unit/phase ID'].notna().all() and not d['GEM unit/phase ID'].duplicated().any()
assert d['Country/area'].eq('China').all()
d['capacity_numeric_MW']=pd.to_numeric(d['Capacity (MW)'],errors='coerce')
d['start_year_numeric']=pd.to_numeric(d['Start year'],errors='coerce')
d['retired_year_numeric']=pd.to_numeric(d['Retired year'],errors='coerce')
d['province_source_label']=d['Subnational unit (state, province)'].astype('string')
# Keep explicit date/coverage flags rather than assigning unknown years to 2020.
d['start_year_unknown']=d.start_year_numeric.isna()
d['current_operating_known_start_by_2020']=d.Status.eq('operating')&d.start_year_numeric.le(2020)
d['current_operating_unknown_start']=d.Status.eq('operating')&d.start_year_unknown
d['retired_after_2020_known_start_by_2020']=d.Status.eq('retired')&d.start_year_numeric.le(2020)&d.retired_year_numeric.gt(2020)
rows=[]
for tech,g in d.groupby('Type'):
    op=g[g.Status.eq('operating')]
    rows.append(dict(technology=tech,all_records=len(g),current_operating_records=len(op),
        current_operating_capacity_MW=op.capacity_numeric_MW.sum(min_count=1),
        current_operating_unknown_start_records=int(op.start_year_unknown.sum()),
        current_operating_unknown_start_capacity_MW=op.loc[op.start_year_unknown,'capacity_numeric_MW'].sum(),
        surviving_operating_start_by_2020_capacity_MW=g.loc[g.current_operating_known_start_by_2020,'capacity_numeric_MW'].sum(),
        retired_after_2020_known_start_by_2020_capacity_MW=g.loc[g.retired_after_2020_known_start_by_2020,'capacity_numeric_MW'].sum(),
        limitation='partial reconstruction candidates; exclusions, conversions and missing dates unresolved'))
pd.DataFrame(rows).to_csv(OUT/'plant_tracker_vintage_completeness.csv',index=False)
keep=['GEM unit/phase ID','Type','Status','Plant / Project name','Unit / Phase name',
      'province_source_label','capacity_numeric_MW','Start year','Retired year','start_year_numeric',
      'retired_year_numeric','start_year_unknown','current_operating_known_start_by_2020',
      'current_operating_unknown_start','retired_after_2020_known_start_by_2020','Conversion/replacement',
      'Unit conversion year','Conversion from/replacement of (GEM unit ID)','Conversion to (GEM unit ID)']
d[keep].to_csv(ROOT/'work/research/prepared/plant_tracker_2025_unit_inventory.csv',index=False)
summary={'status':'unit_inventory_audited_historical_reconstruction_pending','source':'Global Energy Monitor, Global Integrated Power Tracker, July 2025 release',
    'mirror':'https://doi.org/10.5281/zenodo.16810831','license':'CC-BY-4.0, confirmed About sheet',
    'raw_excel_rows':len(raw),'fully_empty_rows_removed':int(blank.sum()),'valid_unit_phase_records':len(d),
    'duplicate_unit_phase_ids':int(d['GEM unit/phase ID'].duplicated().sum()),
    'missing_or_nonnumeric_capacity':int(d.capacity_numeric_MW.isna().sum()),
    'negative_capacity':int((d.capacity_numeric_MW<0).sum()),
    'unknown_start_year_records':int(d.start_year_unknown.sum()),
    'current_operating_unknown_start_year_records':int(d.current_operating_unknown_start.sum()),
    'missing_province':int(d.province_source_label.isna().sum()),
    'sha256':hashlib.sha256(file.read_bytes()).hexdigest(),
    'coverage_limit':'solar/wind tracking thresholds and asset coverage mean this is not automatically the complete official capacity inventory',
    'next_step':'reconcile unit dates, status, conversion links and official province totals; never infer all missing years as pre-2020'}
(OUT/'plant_tracker_source_audit.json').write_text(json.dumps(summary,indent=2))
print(json.dumps(summary,indent=2))
