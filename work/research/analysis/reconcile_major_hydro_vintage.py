"""Reproduce two-dam 2020 capacity checks from reviewed operator evidence."""
from pathlib import Path
import json,pandas as pd
ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'outputs/research/tables'
sources=json.loads((ROOT/'work/research/sources/official_hydro/manifest.json').read_text())
source_by_name={s['name']:s for s in sources}
fleet=pd.read_csv(ROOT/'work/research/prepared/plant_tracker_2025_unit_inventory.csv',low_memory=False)
hydro=fleet[fleet.Type.eq('hydropower')]
archive=pd.read_csv(ROOT/'work/research/sources/zenodo_13987282/selected/data/hydro/dams_large.csv').set_index('Dam_names')
rows=[]
for dam,key in [('Baihetan','baihetan_2021_first_units'),('Wudongde','wudongde_2020_eight_units')]:
    source=source_by_name[key];fact=source['factual_extraction']
    capacity=0 if fact['first_production']>'2020-12-31' else fact['year_end_2020_operating_units']*fact['unit_MW']
    matches=hydro[hydro['Plant / Project name'].str.contains(dam,case=False,na=False)]
    assert len(matches)==1
    gem=matches.iloc[0];a=archive.loc[dam]
    rows.append({'dam':dam,'archived_nameplate_MW':a.installed_capacity_10MW*10,
      'confirmed_2020_year_end_operating_MW':capacity,'first_production_date':fact['first_production'],
      'source_url':source['url'],'GEM_2025_plant_capacity_MW':gem.capacity_numeric_MW,
      'GEM_start_year':gem.start_year_numeric,'GEM_unit_phase_field':gem['Unit / Phase name'],
      'archive_province_label':a.Province,'GEM_province_label':gem.province_source_label,
      'status':'verified year-end bound; full commissioning trajectory and cross-province allocation unresolved'})
r=pd.DataFrame(rows);r.to_csv(OUT/'major_hydro_2020_vintage_reconciliation.csv',index=False)
result={'status':'two_large_dam_vintages_reconciled_to_2020_year_end_not_complete_hydro_baseline',
 'archive_combined_MW':float(r.archived_nameplate_MW.sum()),
 'confirmed_2020_year_end_MW':float(r.confirmed_2020_year_end_operating_MW.sum()),
 'difference_MW':float((r.archived_nameplate_MW-r.confirmed_2020_year_end_operating_MW).sum()),
 'GEM_hydropower_records':len(hydro),
 'GEM_hydropower_records_without_unit_phase_label':int(hydro['Unit / Phase name'].isna().sum()),
 'implication':'GEM plant-level start year cannot automatically recover individual units partially commissioned in 2020; province labels require physical/electrical mapping',
 'cases':r.fillna('').to_dict('records')}
assert result['difference_MW']==19400 and result['confirmed_2020_year_end_MW']==6800
(OUT/'major_hydro_vintage_audit.json').write_text(json.dumps(result,indent=2,ensure_ascii=False))
print('Reproduced two-dam vintage reconciliation from saved operator evidence')
