"""Unit-level thermal/nuclear/hydro fleet for Gansu, Jiangsu, Guizhou from the GEM July-2025 China unit inventory (D11).

2020 fleet: status operating or retired-after-2020 with start year <= 2020.
2030 fleet: operating + construction (+ pre-construction flagged separately) with start <= 2030 and not retired by 2030.
Unknown start years are counted separately and NOT added to either fleet. GEM has size thresholds (coal >= 30 MW,
oil/gas >= 50 MW historically), so totals are a lower bound relative to official statistics; the archive and official
comparisons are reported side by side.
"""
from pathlib import Path
import json,pandas as pd,numpy as np
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'outputs/research/tables'
d=pd.read_csv(ROOT/'work/research/prepared/plant_tracker_2025_unit_inventory.csv',low_memory=False)
prov_map={'Gansu':'Gansu','Jiangsu':'Jiangsu','Guizhou':'Guizhou'}
d=d[d.province_source_label.isin(prov_map)]
d['start']=d.start_year_numeric;d['ret']=d.retired_year_numeric
rows=[];units={}
for p in prov_map:
    x=d[d.province_source_label==p]
    for typ in ['coal','oil/gas','nuclear','hydropower','wind','solar']:
        y=x[x.Type==typ]
        f2020=y[(y.Status.isin(['operating','retired','mothballed']))&(y.start<=2020)&((y.ret.isna())|(y.ret>2020))]
        f2030=y[(y.Status.isin(['operating','construction']))&(y.start<=2030)&((y.ret.isna())|(y.ret>2030))]
        pre=y[(y.Status.isin(['pre-construction','announced']))&(y.start<=2030)]
        unk=y[(y.Status=='operating')&(y.start.isna())]
        rows.append(dict(province=p,type=typ,mw_2020=f2020.capacity_numeric_MW.sum(),units_2020=len(f2020),mw_2030_operating_plus_construction=f2030.capacity_numeric_MW.sum(),units_2030=len(f2030),mw_2030_preconstruction_announced=pre.capacity_numeric_MW.sum(),mw_operating_unknown_start=unk.capacity_numeric_MW.sum(),units_unknown_start=len(unk),
            median_unit_mw_2030=float(f2030.capacity_numeric_MW.median()) if len(f2030) else np.nan))
        if typ in ['coal','oil/gas','nuclear','hydropower']:
            units[(p,typ)]={'2020':f2020[['GEM unit/phase ID','Plant / Project name','Unit / Phase name','capacity_numeric_MW','start','ret']].to_dict('records'),'2030':f2030[['GEM unit/phase ID','Plant / Project name','Unit / Phase name','capacity_numeric_MW','start','ret','Status']].to_dict('records')}
t=pd.DataFrame(rows);t.to_csv(OUT/'gem_fleet_three_provinces_2020_2030.csv',index=False)
json.dump({f'{p}|{ty}':v for (p,ty),v in units.items()},open(ROOT/'work/research/prepared/gem_units_three_provinces.json','w'),default=str)
# archive comparison
src=ROOT/'work/research/sources/zenodo_13987282/selected/data'
cur=pd.read_csv(src/'existing_infrastructure/China_current_capacity.csv');cur['Province']=cur.Province.str.replace(' ','')
piv=cur[cur.Province.isin(prov_map)].pivot_table(index='Province',columns='Type',values='Value',aggfunc='sum').fillna(0)
cmp=[]
for p in prov_map:
    g=t[t.province==p].set_index('type')
    cmp.append(dict(province=p,gem_coal_2020=g.loc['coal','mw_2020'],archive_coal_plus_chp=piv.loc[p].get('coal power plant',0)+piv.loc[p].get('CHP coal',0),gem_gas_2020=g.loc['oil/gas','mw_2020'],archive_ocgt=piv.loc[p].get('OCGT',0),gem_nuclear_2020=g.loc['nuclear','mw_2020'],archive_nuclear_2021vintage=piv.loc[p].get('nuclear',0),gem_hydro_2020=g.loc['hydropower','mw_2020'],archive_other_hydro=piv.loc[p].get('hydroelectricity',0),gem_wind_2020=g.loc['wind','mw_2020'],archive_wind=piv.loc[p].get('onshore wind',0)+piv.loc[p].get('offshore wind',0),gem_solar_2020=g.loc['solar','mw_2020'],archive_solar=piv.loc[p].get('solar PV',0)))
pd.DataFrame(cmp).round(0).to_csv(OUT/'gem_vs_archive_capacity_three_provinces.csv',index=False)
pd.set_option('display.width',250);print(t.round(0).to_string(index=False));print(pd.DataFrame(cmp).round(0).to_string(index=False))
