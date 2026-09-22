"""Acquire only the frozen paired grid-selection pilot, sharing all API quota.

Does not resume the research-held legacy plan or authorize full-grid acquisition.
"""
from pathlib import Path
from datetime import datetime,timezone
import fcntl,json,time,urllib.request,urllib.parse
import numpy as np
from rebuild_explicit_era5 import SRC as LEDGER_ROOT,validate,canonical,digest,save

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'outputs/research/revision/weather_fleet_v2'
SRC=ROOT/'work/research/sources/weather_fleet_revision_v2/pilot'
BASE='https://archive-api.open-meteo.com/v1/archive'


def check(raw,req):
    audit=validate(raw,req);d=json.loads(raw);h=d['hourly'];units=d['hourly_units']
    accepted={'wind_speed_10m':['m/s'],'surface_pressure':['hPa'],
              'direct_radiation':['W/m²',r'W/m\u00b2'],'diffuse_radiation':['W/m²',r'W/m\u00b2']}
    assert audit['hours']==req['expected_hours']==8808
    for name,allowed in accepted.items():
        if units[name] not in allowed:raise ValueError(('units',name,units[name]))
        v=np.asarray(h[name],float)
        if v.shape!=(8808,) or not np.isfinite(v).all() or (v<0).any():raise ValueError(('values',name))
        if name=='surface_pressure' and (v<=0).any():raise ValueError('Nonpositive surface pressure')
    return audit


def main():
    SRC.mkdir(parents=True,exist_ok=True)
    plan_path=OUT/'pilot_plan.json';p=json.loads(plan_path.read_text());requests=p['pilot_requests']
    if len(requests)!=8 or p['full_grid_acquisition_authorized_by_this_plan'] is not False:raise ValueError('Not the bounded pilot')
    records=[];reason='complete'
    with (LEDGER_ROOT/'acquire.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        ledger_path=LEDGER_ROOT/'call_ledger.jsonl'
        ledger=[json.loads(x) for x in ledger_path.read_text().splitlines()]
        for req in requests:
            if digest(canonical(req['parameters']))[:24]!=req['id']:raise ValueError('Changed request ID')
            f=SRC/(req['id']+'.json');m=f.with_suffix('.meta.json')
            if f.exists() or m.exists():
                if not (f.exists() and m.exists()):raise ValueError('Partial cache pair: inspect before continuing')
                meta=json.loads(m.read_text())
                if meta['request']!=req or check(f.read_bytes(),req)!=meta['validation']:raise ValueError('Changed cache')
                records.append(meta);continue
            if ledger:
                delay=6-(time.time()-ledger[-1]['epoch_s'])
                if delay>0:time.sleep(delay)
            now=time.time();charge=req['conservative_call_equivalents']
            if any(sum(x['charge'] for x in ledger if now-x['epoch_s']<window)+charge>limit
                   for window,limit in [(60,450),(3600,3500),(86400,7500)]):
                reason='shared_local_rolling_quota_guard';break
            entry=dict(epoch_s=now,id=req['id'],charge=charge,scope='frozen_v2_grid_pilot')
            with ledger_path.open('a') as f_ledger:f_ledger.write(json.dumps(entry)+'\n')
            ledger.append(entry)
            try:
                url=BASE+'?'+urllib.parse.urlencode(req['parameters']);raw=urllib.request.urlopen(url,timeout=45).read()
                validation=check(raw,req)
                meta=dict(request=req,url=url,retrieved_utc=datetime.now(timezone.utc).isoformat(),validation=validation)
                tmp=f.with_suffix('.download');tmp.write_bytes(raw);tmp.replace(f);save(m,meta)
                records.append(meta);print(json.dumps(dict(completed=len(records),total=8,id=req['id'])),flush=True)
            except Exception as ex:
                failure=dict(request=req,epoch_s=time.time(),error=type(ex).__name__,message=str(ex),http_status=getattr(ex,'code',None))
                with (OUT/'pilot_failed_attempts.jsonl').open('a') as failures:failures.write(json.dumps(failure)+'\n')
                reason='request_failed_no_automatic_retry';print(json.dumps(failure),flush=True);break
        status=dict(plan_sha256=digest(plan_path.read_bytes()),acquirer_sha256=digest(Path(__file__).read_bytes()),
            completed=len(records),pending=8-len(records),stop_reason=reason,records=records)
        save(OUT/'pilot_acquisition.json',status)
        print(json.dumps({k:v for k,v in status.items() if k!='records'},indent=2),flush=True)


if __name__=='__main__':main()
