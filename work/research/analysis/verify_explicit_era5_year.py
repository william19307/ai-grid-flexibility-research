"""Independent scalar/time-key checks of stratified hourly profile values.

Does not import the acquisition, conversion or aggregation implementation.
This verifies declared arithmetic and time alignment, not physical calibration.
"""
from pathlib import Path
import argparse,calendar,csv,hashlib,json,math
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'outputs/research/revision/era5_rebuild'
SRC=ROOT/'work/research/sources/era5_revision_2015_2024'


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--year',type=int,required=True);args=parser.parse_args();year=args.year
    audit=json.loads((OUT/f'profile_audit_{year}.json').read_text())
    plan=json.loads((OUT/'request_plan.json').read_text())
    file=OUT/f'profiles_{year}_generic_INTERVAL_ALIGNED_UNCALIBRATED.csv.gz'
    assert sha(file)==audit['output_sha256']
    sites_path=ROOT/'work/research/prepared/openmeteo_sites_three_provinces.csv'
    assert sha(sites_path)==plan['site_list_sha256']
    data=pd.read_csv(file,index_col=0,parse_dates=True)
    if data.index.tz is None:raise ValueError('Exported clock lost timezone')
    # CSV preserves UTC offsets, not the IANA zone name. Convert while retaining
    # instants; do not strip timezone or silently shift timestamps.
    data.index=data.index.tz_convert('Asia/Shanghai')
    expected=pd.date_range(f'{year}-01-01',f'{year+1}-01-01',freq='h',inclusive='left',tz='Asia/Shanghai')
    assert data.index.equals(expected) and np.isfinite(data.to_numpy()).all()
    samples=set()
    for month in range(1,13):
        for day,hour in [(1,0),(15,12),(calendar.monthrange(year,month)[1],23)]:
            samples.add(pd.Timestamp(year=year,month=month,day=day,hour=hour,tz='Asia/Shanghai'))
    rng=np.random.default_rng(20260923)
    samples.update(expected[i] for i in rng.choice(len(expected),24,replace=False))
    if calendar.isleap(year):samples.add(pd.Timestamp(f'{year}-02-29 12:00',tz='Asia/Shanghai'))
    samples=sorted(samples)
    values={};source_checks=0
    for source in audit['sources']:
        tables={}
        for kind in ['year','boundary']:
            raw=SRC/(source[kind+'_request']+'.json')
            assert sha(raw)==source[kind+'_raw_sha256'];source_checks+=1
            h=json.loads(raw.read_text())['hourly']
            for i,t in enumerate(h['time']):
                if t in tables:raise ValueError('Unexpected overlapping source timestamps')
                tables[t]=(h['wind_speed_100m'][i],h['shortwave_radiation'][i],h['temperature_2m'][i])
        rows=[]
        for t in samples:
            left=t.tz_localize(None).isoformat(timespec='minutes')
            right=(t+pd.Timedelta(hours=1)).tz_localize(None).isoformat(timespec='minutes')
            v0,_,a0=tables[left];v1,irr,a1=tables[right]
            power=[]
            for speed in [v0,v1]:
                power.append(0. if speed>=25 else .85*min(1.,max(0.,(speed-3)/9))**3)
            wind=.5*math.fsum(power)
            solar=min(1.,max(0.,.85*irr/1000*(1-.004*max(0.,(a0+a1)/2-25))))
            rows.append({'wind':wind,'solar':solar})
        values[tuple(source['point'])]=rows
    sites=list(csv.DictReader(sites_path.open()));checks=[]
    for group in data.columns:
        province,tech=group.split('|');selected=[s for s in sites if s['province']==province and s['tech']==tech]
        denom=math.fsum(float(s['mw']) for s in selected)
        for j,t in enumerate(samples):
            ref=math.fsum(float(s['mw'])*values[(f'{float(s["lat"]):.3f}',f'{float(s["lon"]):.3f}')][j][tech] for s in selected)/denom
            actual=float(data.loc[t,group]);error=abs(ref-actual)
            if error>2e-12:raise ValueError((group,str(t),ref,actual))
            checks.append(dict(group=group,time=t.isoformat(),independent_value=ref,stored_value=actual,absolute_error=error))
    result=dict(year=year,hours=len(data),independent_sample_hours=len(samples),sample_value_checks=len(checks),
        source_hash_checks=source_checks,maximum_absolute_error=max(x['absolute_error'] for x in checks),
        scope='Stratified scalar re-computation using raw timestamp keys; not all-hour independent recomputation or physical calibration',
        profile_sha256=sha(file),verifier_sha256=sha(Path(__file__)),checks=checks)
    (OUT/f'independent_verification_{year}.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='checks'},indent=2))


if __name__=='__main__':main()
