"""Resolve archive nuclear vintage using official 2020/2021 unit tables.

2021 HTML rows are parsed. 2020 capacity/generation rows are independently
transcribed from the official table image, visually reviewed on 2026-09-14.
Operating here means first fuel loading, not necessarily commercial operation.
"""
from pathlib import Path
from io import StringIO
import pandas as pd,numpy as np,json,hashlib
ROOT=Path(__file__).resolve().parents[3]
SRC=ROOT/'work/research/sources/official_nuclear';OUT=ROOT/'outputs/research/tables'
archive=ROOT/'work/research/sources/zenodo_13987282/selected/data/existing_infrastructure/nuclear capacity.csv'
tables=pd.read_html(StringIO((SRC/'caea_nuclear_2021.html').read_text()))
assert len(tables)==6
pd.testing.assert_frame_equal(tables[2],tables[5])  # desktop/mobile copies, NOT separate observations
t=tables[2].iloc[1:-1].copy()
t.columns=['plant','unit','rated_MWe','gross_generation_100million_kWh','net_generation_100million_kWh','utilization_hours','capability_factor_percent']
t['plant']=t.plant.str.replace(r'\s+','',regex=True);t['unit']=t.unit.str.replace(r'\s+','',regex=True)
for c in t.columns[2:]:t[c]=pd.to_numeric(t[c],errors='coerce')
province={'秦山核电厂':'Zhejiang','大亚湾核电厂':'Guangdong','秦山第二核电厂':'Zhejiang','岭澳核电厂':'Guangdong',
          '秦山第三核电厂':'Zhejiang','田湾核电站':'Jiangsu','红沿河核电厂':'Liaoning','宁德核电厂':'Fujian',
          '福清核电厂':'Fujian','阳江核电厂':'Guangdong','方家山核电厂':'Zhejiang','三门核电厂':'Zhejiang',
          '海阳核电厂':'Shandong','台山核电厂':'Guangdong','昌江核电厂':'Hainan','防城港核电厂':'Guangxi','石岛湾核电厂':'Shandong'}
t['province']=t.plant.map(province);assert t.province.notna().all()
assert len(t)==53 and not t.duplicated(['plant','unit']).any()
assert np.isclose(t.rated_MWe.sum(),54646.95,atol=1e-7,rtol=0)
t['year']=2021;t['scope']='first-fuel-loaded operating fleet, not commercial-only fleet'
t.to_csv(OUT/'official_nuclear_2021_unit_statistics.csv',index=False)

# (plant, per-unit capacities, gross generation, net generation), transcribed
# from caea_nuclear_2020_table2.jpg. Generation unit is 100 million kWh.
raw=[
 ('秦山核电厂',[330],[26.82],[24.97]),
 ('大亚湾核电厂',[984]*2,[87.86,78.15],[83.98,74.75]),
 ('秦山第二核电厂',[650,650,660,660],[55.66,52.02,50.63,56.24],[52.28,48.68,47.46,52.66]),
 ('岭澳核电厂',[990,990,1086,1086],[78.88,73.21,80.34,78.09],[75.57,70.07,75.43,73.34]),
 ('秦山第三核电厂',[728,728],[60.68,55.96],[56.15,51.61]),
 ('田湾核电站',[1060,1060,1126,1126,1118],[79.96,83.70,77.41,83.37,30.95],[74.14,77.87,71.65,77.,28.79]),
 ('红沿河核电厂',[1118.79]*4,[84.41,83.07,74.33,85.22],[79.04,77.93,69.64,79.89]),
 ('宁德核电厂',[1089]*4,[79.61,86.40,83.59,77.92],[74.49,80.79,78.10,73.01]),
 ('福清核电厂',[1089]*4+[1150],[89.55,83.78,78.50,71.74,1.46],[83.30,78.11,73.31,67.11,1.27]),
 ('阳江核电厂',[1086]*6,[86.66,69.55,70.33,84.92,78.12,63.49],[81.23,65.40,66.,79.55,73.19,59.57]),
 ('方家山核电厂',[1089]*2,[76.76,88.26],[72.15,82.83]),
 ('三门核电厂',[1251]*2,[94.46,94.67],[87.50,87.95]),
 ('海阳核电厂',[1253]*2,[93.62,96.89],[87.66,90.71]),
 ('台山核电厂',[1750]*2,[97.65,133.53],[91.18,124.55]),
 ('昌江核电厂',[650]*2,[48.92,46.71],[45.20,43.28]),
 ('防城港核电厂',[1086]*2,[84.35,84.03],[79.19,79.01]),
]
rows=[]
for plant,capacities,gross,net in raw:
    assert len(capacities)==len(gross)==len(net)
    for i,(c,g,n) in enumerate(zip(capacities,gross,net),1):
        rows.append({'plant':plant,'unit':f'{i}号机组','province':province[plant],'rated_MWe':c,
                     'gross_generation_100million_kWh':g,'net_generation_100million_kWh':n,'year':2020,
                     'first_grid_connection_in_2020':{'田湾核电站5号机组':'2020-08-08','福清核电厂5号机组':'2020-11-27'}.get(plant+f'{i}号机组',''),
                     'scope':'first-fuel-loaded operating fleet, not commercial-only fleet',
                     'method':'manual transcription of visually reviewed official table image'})
u=pd.DataFrame(rows);assert len(u)==49 and not u.duplicated(['plant','unit']).any()
assert np.isclose(u.rated_MWe.sum(),51027.16,atol=1e-7,rtol=0)
assert abs(u.gross_generation_100million_kWh.sum()-3662.43)<1e-7
assert abs(u.net_generation_100million_kWh.sum()-3428.54)<1e-7
u.to_csv(OUT/'official_nuclear_2020_unit_statistics.csv',index=False)

# Province-by-province fingerprint, rather than merely comparing national totals.
a=pd.read_csv(archive).set_index('Province')['2020'].rename('archive_labeled_2020_MW')
b=t.groupby('province').rated_MWe.sum().reindex(a.index,fill_value=0).rename('official_2021_first_loaded_MWe')
c=u.groupby('province').rated_MWe.sum().reindex(a.index,fill_value=0).rename('official_2020_first_loaded_MWe')
comparison=pd.concat([a,b,c],axis=1)
comparison['archive_minus_rounded_official_2021_MW']=a-b.round()
comparison['archive_minus_official_2020_MW']=a-c
assert comparison.archive_minus_rounded_official_2021_MW.eq(0).all()
comparison.to_csv(OUT/'nuclear_archive_vintage_reconciliation.csv')

# Separate set changes from changes in capacity ratings of the same unit.
joined=t.merge(u,on=['plant','unit'],how='outer',suffixes=('_2021','_2020'),indicator=True)
new=joined[joined._merge.eq('left_only')]
assert len(new)==4 and not joined._merge.eq('right_only').any()
changed=joined[joined._merge.eq('both') & ~np.isclose(joined.rated_MWe_2021,joined.rated_MWe_2020)]
assert len(changed)==1 and changed.iloc[0].plant=='福清核电厂' and changed.iloc[0].unit=='5号机组'
delta_new=float(new.rated_MWe_2021.sum());delta_rating=float((changed.rated_MWe_2021-changed.rated_MWe_2020).sum())
assert np.isclose(t.rated_MWe.sum()-u.rated_MWe.sum(),delta_new+delta_rating)
joined[['plant','unit','rated_MWe_2020','rated_MWe_2021','_merge']].to_csv(OUT/'nuclear_unit_vintage_crosswalk_2020_2021.csv',index=False)

# Produce explicit annual generation calibration targets, not a dispatch series.
targets=u.groupby('province')[['rated_MWe','gross_generation_100million_kWh','net_generation_100million_kWh']].sum()
targets['gross_generation_MWh']=targets.gross_generation_100million_kWh*1e5
targets['net_generation_MWh']=targets.net_generation_100million_kWh*1e5
targets['status']='annual source target only; commissioned dates and gross/net boundary must be modeled'
targets.to_csv(ROOT/'work/research/prepared/nuclear_2020_province_annual_targets.csv')

summary={'status':'archive_2020_column_matches_rounded_official_2021_first_loaded_fleet_in_all_31_provinces',
 'archive_labeled_year':2020,'archive_total_MW':float(a.sum()),'official_2021_total_MWe':float(t.rated_MWe.sum()),
 'official_2020_first_loaded_total_MWe':float(u.rated_MWe.sum()),'province_rows_checked':len(comparison),
 'exact_rounded_matches':int(comparison.archive_minus_rounded_official_2021_MW.eq(0).sum()),
 'difference_2021_minus_2020_MWe':float(t.rated_MWe.sum()-u.rated_MWe.sum()),
 'new_first_loaded_units_MWe':delta_new,'changed_rating_same_unit_MWe':delta_rating,
 'new_units':new[['plant','unit','rated_MWe_2021']].to_dict('records'),
 'changed_ratings':changed[['plant','unit','rated_MWe_2020','rated_MWe_2021']].to_dict('records'),
 '2020_unit_generation_sums_100million_kWh':{'gross':float(u.gross_generation_100million_kWh.sum()),'net':float(u.net_generation_100million_kWh.sum())},
 '2020_source_reported_generation_totals_100million_kWh':{'gross':3662.43,'net':3428.54},
 '2020_rounding_residual_100million_kWh':{'gross':float(u.gross_generation_100million_kWh.sum()-3662.43),'net':float(u.net_generation_100million_kWh.sum()-3428.54)},
 'source_urls':['https://www.caea.gov.cn/n6760340/n6760356/c6827514/content.html','https://www.caea.gov.cn/n6760340/n6760356/c6827530/content.html'],
 'source_image_visually_reviewed':'2026-09-14, official 2020 tables 1 and 2',
 'limitations':['exact numerical fingerprint establishes year/scope inconsistency, not the unpublished provenance history of the archive',
 'first fuel loading, first grid connection and commercial operation are distinct dates',
 '2020 table includes Fuqing 5 prior to commercial operation; not equivalent to official commercial-only or other statistical fleet totals',
 'capacity rating changes across publications do not by themselves prove physical capacity upgrades',
 'annual unit generation is rounded; preserve residual, do not force totals by altering a unit',
 'year-end nameplate cannot be assumed available for all 8784 hours',
 'net/gross generation boundary requires consistent auxiliary-power treatment in the grid model'],
 'archive_sha256':hashlib.sha256(archive.read_bytes()).hexdigest()}
(OUT/'nuclear_baseyear_reconciliation.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False))
print(json.dumps(summary,indent=2,ensure_ascii=False))
