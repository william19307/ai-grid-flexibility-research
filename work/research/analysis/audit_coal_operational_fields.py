"""Restore operational context omitted by the aggregate fleet extraction.

Blank CHP/captive fields remain unknown. Flags do not establish dispatch limits,
heat obligations, grid access, or whether the unit is currently operational.
"""
from pathlib import Path
import json,hashlib,time
import numpy as np,pandas as pd
ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'outputs/research/revision/commitment/fleet_audit';OUT.mkdir(parents=True,exist_ok=True)
source=ROOT/'work/research/sources/zenodo_16810831/Global-integrated-Plant-Tracker-July-2025_china.xlsx'
selection=ROOT/'work/research/prepared/gem_units_three_provinces.json'
raw=pd.read_excel(source,sheet_name='Power facilities');units=json.loads(selection.read_text())
frames=[];summary=[]
fields=['Technology','Fuel','CHP','Captive Industry Type','Captive Industry Use','Captive Non Industry Use']
for province in ['Gansu','Jiangsu','Guizhou']:
    selected=pd.DataFrame(units[f'{province}|coal']['2030'])
    assert selected['GEM unit/phase ID'].is_unique
    subset=raw[raw['GEM unit/phase ID'].isin(selected['GEM unit/phase ID'])]
    assert len(subset)==len(selected) and subset['GEM unit/phase ID'].is_unique
    merged=selected.merge(subset[['GEM unit/phase ID','Capacity (MW)',*fields]],on='GEM unit/phase ID',validate='one_to_one')
    assert np.allclose(merged['capacity_numeric_MW'],pd.to_numeric(merged['Capacity (MW)']),atol=1e-9,rtol=0)
    chp=merged.CHP.fillna('').str.strip().str.lower()
    assert set(chp)<=set(['','yes','no']),set(chp)
    merged['chp_yes']=chp.eq('yes');merged['chp_unknown']=chp.eq('')
    merged['captive_use_documented']=merged[fields[3:]].notna().any(axis=1)
    merged['province']=province;merged['capacity_mw']=merged.capacity_numeric_MW
    # Missing operational parameters stay missing, not silently filled by assumptions.
    for field in ['minimum_output_mw','ramp_up_mw_per_hour','ramp_down_mw_per_hour','startup_cost',
                  'shutdown_cost','no_load_cost_per_hour','minimum_up_hours','minimum_down_hours',
                  'heat_demand_profile','initial_commitment_state','forced_outage_series']:
        merged[field]=pd.NA
    frames.append(merged)
    mw=merged.capacity_mw;total=float(mw.sum())
    row=dict(province=province,units=len(merged),capacity_mw=total)
    for label,flag in [('chp_yes',merged.chp_yes),('chp_unknown',merged.chp_unknown),
                       ('captive_documented',merged.captive_use_documented),
                       ('chp_or_captive_documented',merged.chp_yes|merged.captive_use_documented)]:
        row[label+'_units']=int(flag.sum());row[label+'_mw']=float(mw[flag].sum());row[label+'_capacity_pct']=100*float(mw[flag].sum())/total
    summary.append(row)
all_units=pd.concat(frames,ignore_index=True)
assert all_units['GEM unit/phase ID'].is_unique
prepared=ROOT/'work/research/prepared/coal_operational_context_2030_candidate.csv'
all_units.to_csv(prepared,index=False)
pd.DataFrame(summary).to_csv(OUT/'coal_operational_context_summary.csv',index=False)
paths=[source,selection,Path(__file__),prepared]
report=dict(audit_unix=time.time(),selection='Existing frozen 2030 operating-plus-construction coal selection; not a validated forecast',
    units=len(all_units),total_capacity_mw=float(all_units.capacity_mw.sum()),
    chp_yes_units=int(all_units.chp_yes.sum()),chp_unknown_units=int(all_units.chp_unknown.sum()),
    captive_context_units=int(all_units.captive_use_documented.sum()),
    capacity_match_to_existing_selection=True,raw_columns=raw.columns.tolist(),
    source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
    limitations=['Blank flags mean unknown, not no CHP/captive use',
                 'CHP/captive labels do not establish heat dispatch, grid access or available electric capacity',
                 'No unit-specific commitment/ramp/startup/heat/outage parameter is calibrated by this audit',
                 'Frozen fleet and manuscript tables are not overwritten; candidate unit table stays in excluded prepared data'])
(OUT/'audit.json').write_text(json.dumps(report,indent=2)+'\n')
(OUT/'source_snapshot.json').write_text(json.dumps({str(Path(__file__).relative_to(ROOT)):Path(__file__).read_text()},indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in ['source_sha256','raw_columns','limitations']},indent=2))
print(pd.DataFrame(summary).to_string(index=False))
