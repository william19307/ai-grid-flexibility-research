"""Region selection matrix for the first-round regional S0/S1/S2 studies.

Every column is labelled by evidence tier. Capacity columns come from the
PyPSA-China V3.0 archive (UNVERIFIED as 2020 installed capacity); the load
anchor comes from the official 2020 provincial electricity table; hub flags
come from the 2022 national compute-hub approvals (source URL in the output).
This is a screening table, not a research result.
"""
from pathlib import Path
import json
import numpy as np, pandas as pd
ROOT=Path(__file__).resolve().parents[3]
SRC=ROOT/'work/research/sources/zenodo_13987282/selected/data'
OUT=ROOT/'outputs/research/tables'

code={'Beijing':'BJ','Tianjin':'TJ','Hebei':'HE','Shanxi':'SX','InnerMongolia':'NM','Shandong':'SD','Liaoning':'LN','Jilin':'JL','Heilongjiang':'HL','Shanghai':'SH','Jiangsu':'JS','Zhejiang':'ZJ','Anhui':'AH','Fujian':'FJ','Jiangxi':'JX','Henan':'HA','Hubei':'HB','Hunan':'HN','Chongqing':'CQ','Sichuan':'SC','Guangdong':'GD','Guangxi':'GX','Hainan':'HI','Guizhou':'GZ','Yunnan':'YN','Shaanxi':'SN','Gansu':'GS','Qinghai':'QH','Ningxia':'NX','Xinjiang':'XJ','Tibet':'XZ'}
cal=pd.read_csv(OUT/'provincial_load_2020_annual_calibration.csv').set_index('province')
cur=pd.read_csv(SRC/'existing_infrastructure/China_current_capacity.csv')
cur['Province']=cur['Province'].str.replace('Inner Mongolia','InnerMongolia').str.replace(' ','')
piv=cur.pivot_table(index='Province',columns='Type',values='Value',aggfunc='sum').fillna(0)
dams=pd.read_csv(SRC/'hydro/dams_large.csv')
dam_col=[c for c in dams.columns if 'rovince' in c][0]
dam_cap_col=[c for c in dams.columns if 'apacity' in c or 'MW' in c or 'nom' in c][0]
dams['prov']=dams[dam_col].astype(str).str.replace(' ','').str.replace('InnerMongolia','InnerMongolia')
big_hydro=dams.groupby('prov')[dam_cap_col].sum()*10  # source column is in units of 10 MW
hvdc=pd.read_csv(ROOT/'work/research/prepared/HVDC_source_list_rebuilt_UNVERIFIED_GW.csv',index_col=0)
hvac=pd.read_csv(ROOT/'work/research/prepared/HVAC_source_list_rebuilt_UNVERIFIED_GW.csv',index_col=0)
inter=(hvdc.sum(axis=1)+hvac.sum(axis=1))*1000  # MW, both directions share capacity
conflict={'HL','HB','HA','HN'}
# National integrated compute-hub approvals, Feb 2022 (NDRC/CAC/MIIT/NEA); province-level flags.
hubs={'HE':'京津冀枢纽（张家口集群）','SH':'长三角枢纽','JS':'长三角枢纽','ZJ':'长三角枢纽','AH':'长三角枢纽（芜湖集群）','GD':'粤港澳大湾区枢纽（韶关集群）','SC':'成渝枢纽（天府集群）','CQ':'成渝枢纽（重庆集群）','NM':'内蒙古枢纽（和林格尔集群）','GZ':'贵州枢纽（贵安集群）','GS':'甘肃枢纽（庆阳集群）','NX':'宁夏枢纽（中卫集群）'}
hub_source='https://www.ndrc.gov.cn/xwdt/xwfb/202202/t20220217_1315624.html'
grid_notes={'NM':'蒙西电网独立运行，蒙东属东北电网；省级建模需拆分','HI':'海南通过联网工程与广东相连','XZ':'西藏电网与西南主网弱联','XJ':'新疆主要经哈密—郑州特高压外送'}
rows=[]
for p,c in code.items():
    peak=cal.loc[p,'adjusted_peak_hourly_average_MW'];annual=cal.loc[p,'official_2020_TWh']
    g=piv.loc[p] if p in piv.index else pd.Series(dtype=float)
    wind=g.get('onshore wind',0)+g.get('offshore wind',0);solar=g.get('solar PV',0)
    coal=g.get('coal power plant',0)+g.get('CHP coal',0);gas=g.get('OCGT',0);nuclear=g.get('nuclear',0)
    other_hydro=g.get('hydroelectricity',0);big=float(big_hydro.get(p,0))
    firm=coal+gas+nuclear+other_hydro+big
    rows.append(dict(province=p,code=c,official_2020_TWh=annual,anchored_peak_MW=round(peak),
        load_anchor_abs_dev_pct=round(abs(cal.loc[p,'source_relative_difference_pct']),2),
        wind_MW_archive=wind,solar_MW_archive=solar,re_over_peak=round((wind+solar)/peak,2),
        coal_MW_archive=coal,gas_MW_archive=gas,nuclear_MW_archive_2021vintage=nuclear,
        other_hydro_MW_archive=other_hydro,large_dam_MW_archive=big,hydro_share_of_firm=round((other_hydro+big)/firm,2) if firm else np.nan,
        interconnection_MW_rebuilt_unverified=round(inter.get(c,0)),interconnection_over_peak=round(inter.get(c,0)/peak,2),
        transmission_conflict_flag=c in conflict,compute_hub=hubs.get(c,''),grid_note=grid_notes.get(c,'')))
df=pd.DataFrame(rows)
# Screening: three archetypes.
def archetype(r):
    tags=[]
    if r.compute_hub and r.re_over_peak>=0.6 and r.hydro_share_of_firm<0.25:tags.append('A_RE-rich_hub_low_hydro')
    if r.compute_hub and r.official_2020_TWh>=400:tags.append('B_load-centre_hub')
    if r.compute_hub and r.hydro_share_of_firm>=0.25:tags.append('C_hydro-mixed_hub')
    return ';'.join(tags)
df['archetype']=df.apply(archetype,axis=1)
df=df.sort_values(['archetype','load_anchor_abs_dev_pct'],ascending=[False,True])
df.to_csv(OUT/'region_selection_matrix.csv',index=False)
meta={'hub_source':hub_source,'hub_source_note':'2022-02 national integrated big-data-centre hub approvals; province flags derived from the eight hubs / ten clusters; URL to be re-verified on next fetch',
 'capacity_source':'PyPSA-China V3.0 archive China_current_capacity.csv and dams_large.csv; NOT verified as 2020 installed capacity (nuclear column is 2021 vintage, see nuclear_baseyear_reconciliation.json)',
 'load_source':'official 2020 provincial electricity (NBS yearbook 2021 table 9-14) anchored shape; hourly shape unvalidated',
 'interconnection_source':'HVDC/HVAC line lists rebuilt from Wu & Kan appendix; UNVERIFIED; conflict provinces flagged',
 'screening_rule':'A: hub, (wind+solar)/peak>=0.6, hydro share of firm capacity<0.25; B: hub, annual load>=400 TWh; C: hub, hydro share>=0.25',
 'status':'screening table, not a research result'}
json.dump(meta,open(OUT/'region_selection_matrix_meta.json','w'),ensure_ascii=False,indent=1)
pd.set_option('display.width',250);pd.set_option('display.max_columns',30)
print(df[df.archetype!=''][['province','code','official_2020_TWh','anchored_peak_MW','load_anchor_abs_dev_pct','re_over_peak','hydro_share_of_firm','interconnection_over_peak','transmission_conflict_flag','compute_hub','archetype','grid_note']].to_string(index=False))
print('\nlarge dam columns used:',dam_col,dam_cap_col)
