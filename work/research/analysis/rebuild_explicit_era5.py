"""Resumable explicit-ERA5 acquisition; no interpolation or old-result mutation.

The complete request plan is fixed from the archived site list. Bounded batches
respect conservative local call-equivalent limits and stop on HTTP errors.
Other applications may share the provider quota; 429 is never bypassed.
"""
from pathlib import Path
from datetime import datetime, timezone
import argparse,csv,fcntl,hashlib,json,math,time,urllib.parse,urllib.request,urllib.error
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[3]
SRC=ROOT/'work/research/sources/era5_revision_2015_2024'
OUT=ROOT/'outputs/research/revision/era5_rebuild'
SITES=ROOT/'work/research/prepared/openmeteo_sites_three_provinces.csv'
BASE='https://archive-api.open-meteo.com/v1/archive'
VARIABLES=['wind_speed_100m','shortwave_radiation','temperature_2m']


def digest(b):return hashlib.sha256(b).hexdigest()
def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':')).encode()
def save(path,obj):
    tmp=path.with_suffix(path.suffix+'.tmp')
    tmp.write_text(json.dumps(obj,indent=2)+'\n');tmp.replace(path)


def plan():
    sites=list(csv.DictReader(SITES.open()))
    points=sorted({(f'{float(r["lat"]):.3f}',f'{float(r["lon"]):.3f}') for r in sites})
    requests=[]
    for year in [2020]+[y for y in range(2015,2025) if y!=2020]:
        for lat,lon in points:
            p=dict(latitude=lat,longitude=lon,start_date=f'{year}-01-01',end_date=f'{year}-12-31',
                hourly=','.join(VARIABLES),timezone='Asia/Shanghai',models='era5',wind_speed_unit='ms',cell_selection='land')
            key=digest(canonical(p))[:24]
            hours=len(pd.date_range(p['start_date'],p['end_date']+' 23:00',freq='h'))
            requests.append(dict(id=key,year=year,parameters=p,url=BASE+'?'+urllib.parse.urlencode(p),
                expected_hours=hours,conservative_call_equivalents=math.ceil(hours/24/14)))
    result=dict(schema_version=1,site_list_sha256=digest(SITES.read_bytes()),years=list(range(2015,2025)),
        site_rows=len(sites),unique_requested_coordinates=len(points),requests=requests,
        scientific_scope='Source repair on frozen sites; not generation calibration, full spatial coverage or reliability validation',
        provider_terms='https://open-meteo.com/en/terms',provider_call_accounting='https://open-meteo.com/en/pricing')
    OUT.mkdir(parents=True,exist_ok=True);SRC.mkdir(parents=True,exist_ok=True)
    dest=OUT/'request_plan.json'
    if dest.exists() and json.loads(dest.read_text())!=result:raise ValueError('Frozen request plan changed')
    if not dest.exists():save(dest,result)
    return result


def validate(raw,request):
    d=json.loads(raw);h=d['hourly'];p=request['parameters']
    expected=pd.date_range(p['start_date'],p['end_date']+' 23:00',freq='h')
    if not pd.DatetimeIndex(h['time']).equals(expected):raise ValueError('Missing/duplicate/misaligned hourly calendar')
    if d['timezone']!='Asia/Shanghai' or d['utc_offset_seconds']!=28800:raise ValueError('Wrong time zone')
    units=d['hourly_units']
    accepted={'wind_speed_100m':['m/s'],'shortwave_radiation':['W/m²',r'W/m\u00b2'],'temperature_2m':['°C',r'\u00b0C']}
    for k in VARIABLES:
        if units[k] not in accepted[k]:raise ValueError(f'Unexpected unit for {k}: {units[k]}')
        values=np.asarray(h[k],float)
        if values.shape!=(len(expected),) or not np.isfinite(values).all():raise ValueError(f'Missing values: {k}')
        if k!='temperature_2m' and (values<0).any():raise ValueError(f'Negative physical input: {k}')
    scientific={k:v for k,v in d.items() if k!='generationtime_ms'}
    return dict(raw_sha256=digest(raw),scientific_content_sha256=digest(canonical(scientific)),
        bytes=len(raw),hours=len(expected),returned_metadata={k:v for k,v in d.items() if k!='hourly'})


def existing(request):
    raw_path=SRC/(request['id']+'.json');meta_path=SRC/(request['id']+'.meta.json')
    if not raw_path.exists() and not meta_path.exists():return None
    if not raw_path.exists() or not meta_path.exists():raise ValueError(f'Incomplete cache pair {request["id"]}; inspect manually')
    meta=json.loads(meta_path.read_text());raw=raw_path.read_bytes()
    if meta['request']!=request or digest(raw)!=meta['validation']['raw_sha256']:raise ValueError('Modified cached acquisition')
    check=validate(raw,request)
    if check!=meta['validation']:raise ValueError('Changed cache validation')
    return meta


def record(request,raw,origin):
    check=validate(raw,request)
    meta=dict(request=request,retrieved_utc=datetime.now(timezone.utc).isoformat(),origin=origin,validation=check)
    raw_path=SRC/(request['id']+'.json');meta_path=SRC/(request['id']+'.meta.json')
    if raw_path.exists() or meta_path.exists():raise ValueError('Refusing to replace cached data')
    tmp=raw_path.with_suffix('.download');tmp.write_bytes(raw);tmp.replace(raw_path);save(meta_path,meta)
    return meta


def snapshot(p,records,reason):
    done={x['request']['id'] for x in records}
    by_year={str(y):sum(x['year']==y and x['id'] in done for x in p['requests']) for y in p['years']}
    result=dict(plan_sha256=digest((OUT/'request_plan.json').read_bytes()),downloaded=len(done),
        pending=len(p['requests'])-len(done),expected=len(p['requests']),by_year=by_year,stop_reason=reason,
        observed_utc=datetime.now(timezone.utc).isoformat(),records=records)
    save(OUT/'acquisition_status.json',result)
    return result


def main():
    a=argparse.ArgumentParser();a.add_argument('--plan-only',action='store_true');a.add_argument('--max-requests',type=int,default=115)
    a.add_argument('--min-interval-s',type=float,default=6.);args=a.parse_args()
    if args.max_requests<1 or args.min_interval_s<6:raise ValueError('Positive batch and at least 6s spacing required')
    p=plan()
    if args.plan_only:
        print(json.dumps({k:v for k,v in p.items() if k!='requests'},indent=2));print('requests',len(p['requests']));return
    with (SRC/'acquire.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        records=[]
        for req in p['requests']:
            cached=existing(req)
            if cached:records.append(cached)
        # Reuse the previously verified explicit-model pilot without a second API call.
        pilot_path=ROOT/'outputs/research/revision/weather_input_audit/explicit_era5_pilot_manifest.json'
        pilot=json.loads(pilot_path.read_text())
        for req in p['requests']:
            if req['parameters']==pilot['explicit_parameters'] and not any(x['request']['id']==req['id'] for x in records):
                raw=(ROOT/'work/research/sources/weather_revision_era5/gansu_solar_largest_site_2020_era5.json').read_bytes()
                if digest(raw)!=pilot['sha256']:raise ValueError('Changed pilot')
                records.append(record(req,raw,'reused_verified_pilot_original_retrieval_2026-09-22'))
        ledger_path=SRC/'call_ledger.jsonl'
        ledger=[json.loads(line) for line in ledger_path.read_text().splitlines()] if ledger_path.exists() else []
        attempted=0;reason='complete';done={x['request']['id'] for x in records}
        snapshot(p,records,'running')
        for req in p['requests']:
            if req['id'] in done:continue
            if attempted>=args.max_requests:reason='bounded_batch_complete';break
            if ledger:
                delay=args.min_interval_s-(time.time()-ledger[-1]['epoch_s'])
                if delay>0:time.sleep(delay)
            now=time.time();charge=req['conservative_call_equivalents']
            # This ledger covers this acquisition only. Safety margins reserve quota
            # for the pilot/other work; provider errors still stop the run immediately.
            limits=[(60,450),(3600,3500),(86400,7500)]
            exceeded=[window for window,limit in limits if sum(x['charge'] for x in ledger if now-x['epoch_s']<window)+charge>limit]
            if exceeded:reason='local_rolling_quota_guard_'+str(exceeded);break
            entry=dict(epoch_s=now,id=req['id'],charge=charge)
            with ledger_path.open('a') as f:f.write(json.dumps(entry)+'\n')
            ledger.append(entry);attempted+=1
            try:
                raw=urllib.request.urlopen(req['url'],timeout=45).read()
                meta=record(req,raw,'explicit_era5_http_request')
                records.append(meta);done.add(req['id'])
                print(json.dumps(dict(completed=len(done),total=len(p['requests']),year=req['year'],id=req['id'])),flush=True)
                snapshot(p,records,'running')
            except Exception as e:
                failure=dict(request=req,epoch_s=time.time(),type=type(e).__name__,message=str(e),http_status=getattr(e,'code',None))
                with (OUT/'failed_attempts.jsonl').open('a') as f:f.write(json.dumps(failure)+'\n')
                reason='request_failed_no_automatic_retry';print(json.dumps(failure),flush=True);break
        result=snapshot(p,records,reason)
        print(json.dumps({k:v for k,v in result.items() if k!='records'},indent=2),flush=True)


if __name__=='__main__':main()
