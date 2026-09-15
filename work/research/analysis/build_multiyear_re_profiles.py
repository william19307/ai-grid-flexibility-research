"""Multi-year (2015-2024) hourly wind and solar capacity factors for Gansu, Jiangsu, Guizhou from Open-Meteo ERA5 archive.

Sites: operating wind/solar units from the GEM July-2025 tracker with coordinates; the largest N sites per province and
technology (capacity share reported). Wind: 100 m wind speed -> generic IEC-class power curve (cut-in 3 m/s, rated 12 m/s,
cut-out 25 m/s, cubic ramp) x 0.85 availability/wake factor. Solar: GHI/1000 x temperature derating 0.004/K above 25 C x
0.85 performance ratio (horizontal plane, no tracking). Province profile = capacity-weighted mean. Each year is then
scaled so that the 2020 annual mean equals the archive 2020 profile mean (one factor per province/technology), so levels
follow the archive while inter-annual variability and hourly shape follow ERA5. Evidence tier: reanalysis-derived
profiles with a simple conversion; not measured generation. Open-Meteo: free, no key, CC-BY 4.0 (ERA5 via Copernicus).
"""
from pathlib import Path
import json,time,hashlib,sys
import numpy as np,pandas as pd,requests
ROOT=Path(__file__).resolve().parents[3];PREP=ROOT/'work/research/prepared';OUT=ROOT/'outputs/research/tables'
N=int(__import__("os").environ.get("RE_SITES","8"));YEARS=(2015,2024)
x=pd.read_excel(ROOT/'work/research/sources/zenodo_16810831/Global-integrated-Plant-Tracker-July-2025_china.xlsx',sheet_name='Power facilities')
pc='Subnational unit (state, province)'
sub=x[(x[pc].isin(['Gansu','Jiangsu','Guizhou']))&(x['Type'].isin(['wind','solar']))&(x['Status']=='operating')&x['Latitude'].notna()]
sites=[];meta={}
for (p,t),g in sub.groupby([pc,'Type']):
    g=g.sort_values('Capacity (MW)',ascending=False);top=g.head(N)
    meta[f'{p}|{t}']=dict(n_sites=int(len(g)),mw_total=float(g['Capacity (MW)'].sum()),top_share=float(top['Capacity (MW)'].sum()/g['Capacity (MW)'].sum()))
    for _,r in top.iterrows():sites.append(dict(province=p,tech=t,name=r['Plant / Project name'],mw=float(r['Capacity (MW)']),lat=float(r['Latitude']),lon=float(r['Longitude'])))
sites=pd.DataFrame(sites);sites.to_csv(PREP/'openmeteo_sites_three_provinces.csv',index=False)
cache=PREP/'openmeteo_cache';cache.mkdir(exist_ok=True)
def pull(lat,lon):
    key=hashlib.md5(f'{lat:.3f},{lon:.3f},{YEARS}'.encode()).hexdigest();f=cache/f'{key}.json'
    if f.exists():return json.load(open(f))
    url=f'https://archive-api.open-meteo.com/v1/archive?latitude={lat:.3f}&longitude={lon:.3f}&start_date={YEARS[0]}-01-01&end_date={YEARS[1]}-12-31&hourly=wind_speed_100m,shortwave_radiation,temperature_2m&timezone=Asia%2FShanghai'
    for k in range(5):
        r=requests.get(url,timeout=180)
        if r.status_code==200:d=r.json();json.dump(d,open(f,'w'));return d
        time.sleep(10*(k+1))
    raise RuntimeError(('openmeteo failed',lat,lon,r.status_code,r.text[:200]))
def wind_cf(ws_kmh):
    v=np.asarray(ws_kmh,float)/3.6;cf=np.where(v<3,0,np.where(v<12,((v-3)/9)**3,np.where(v<25,1.0,0.0)));return 0.85*cf
def solar_cf(ghi,t2m):
    ghi=np.asarray(ghi,float);t=np.asarray(t2m,float);return np.clip(0.85*ghi/1000*(1-0.004*np.maximum(t-25,0)),0,1)
prof={};idx=None
for _,s in sites.iterrows():
    d=pull(s.lat,s.lon);h=d['hourly'];t=pd.to_datetime(h['time'])
    if idx is None:idx=t
    cf=wind_cf(h['wind_speed_100m']) if s.tech=='wind' else solar_cf(h['shortwave_radiation'],h['temperature_2m'])
    cf=pd.Series(cf,index=t).reindex(idx).interpolate(limit_direction='both').values
    prof.setdefault((s.province,s.tech),[]).append((s.mw,cf));print('pulled',s.province,s.tech,s['name'][:30],flush=True)
# archive 2020 means for level scaling
a=np.load(PREP/'archive_2020_source_inputs_NOT_calibrated.npz');provs=list(a['provinces'])
res={};scale={}
for (p,t),lst in prof.items():
    w=np.array([m for m,_ in lst]);cf=np.vstack([c for _,c in lst]);agg=(w[:,None]*cf).sum(0)/w.sum()
    ser=pd.Series(agg,index=idx);i=provs.index(p);arch=a['onwind_pu'][:,i] if t=='wind' else a['solar_pu'][:,i]
    m2020=ser[ser.index.year==2020].mean();k=float(np.nanmean(arch)/m2020) if m2020>0 else 1.0;ser=np.clip(ser*k,0,1)
    r2020=ser[ser.index.year==2020].values[:8784];corr=float(np.corrcoef(r2020,arch[:len(r2020)])[0,1])
    res[(p,t)]=ser;scale[f'{p}|{t}']=dict(level_scale=k,corr_with_archive_2020=corr,mean_cf_by_year={int(y):float(v) for y,v in ser.groupby(ser.index.year).mean().items()})
df=pd.DataFrame({f'{p}|{t}':s for (p,t),s in res.items()});df.index.name='time_utc8';df.to_csv(PREP/'re_profiles_2015_2024_three_provinces.csv.gz',compression='gzip')
json.dump(dict(sites=meta,scaling=scale,method=open(__file__).read().split('"""')[1]),open(OUT/'multiyear_re_profiles_audit.json','w'),indent=1)
print(json.dumps(scale,indent=1));print('RE_PROFILES_DONE')
