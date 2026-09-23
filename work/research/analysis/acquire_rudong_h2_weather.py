"""Bounded three-year H2 diagnostic; shares quota with earlier acquisitions."""
from pathlib import Path
from datetime import datetime,timezone
import fcntl,json,time,urllib.request,urllib.parse
import numpy as np
from rebuild_explicit_era5 import SRC as LEDGER_ROOT,validate,canonical,digest,save

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'outputs/research/revision/rudong_h2_validation'
SRC=ROOT/'work/research/sources/rudong_h2_observations_20260923/weather'


def check(raw,req):
    result=validate(raw,req);data=json.loads(raw)
    assert result['hours']==req['expected_hours']
    for key,unit in [('wind_speed_10m','m/s'),('surface_pressure','hPa'),
                     ('direct_radiation','W/m²'),('diffuse_radiation','W/m²')]:
        assert data['hourly_units'][key]==unit
        values=np.asarray(data['hourly'][key],float)
        assert len(values)==req['expected_hours'] and np.isfinite(values).all() and (values>=0).all()
        if key=='surface_pressure':assert (values>0).all()
    return result


def main():
    path=OUT/'site_weather_plan.json';plan=json.loads(path.read_text())
    assert plan['unit']['unit_id']=='G100000903072' and len(plan['requests'])==3
    assert [r['year'] for r in plan['requests']]==[2022,2023,2024]
    assert digest((OUT/'observation_audit.json').read_bytes())==plan['observation_audit_sha256']
    SRC.mkdir(exist_ok=True,parents=True);records=[];reason='complete'
    with (LEDGER_ROOT/'acquire.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        ledger_path=LEDGER_ROOT/'call_ledger.jsonl'
        ledger=[json.loads(x) for x in ledger_path.read_text().splitlines()]
        for req in plan['requests']:
            assert digest(canonical(req['parameters']))[:24]==req['id']
            raw_path=SRC/(req['id']+'.json');meta_path=raw_path.with_suffix('.meta.json')
            if raw_path.exists() or meta_path.exists():
                assert raw_path.exists() and meta_path.exists(),'Partial cache pair'
                meta=json.loads(meta_path.read_text())
                assert meta['request']==req and check(raw_path.read_bytes(),req)==meta['validation']
                records.append(meta);continue
            if ledger:
                delay=6-(time.time()-ledger[-1]['epoch_s'])
                if delay>0:time.sleep(delay)
            now=time.time();charge=req['conservative_call_equivalents']
            if any(sum(x['charge'] for x in ledger if now-x['epoch_s']<window)+charge>limit
                   for window,limit in [(60,450),(3600,3500),(86400,7500)]):
                reason='shared_local_rolling_quota_guard';break
            entry=dict(epoch_s=now,id=req['id'],charge=charge,scope='frozen_rudong_h2_three_year_diagnostic')
            with ledger_path.open('a') as f:f.write(json.dumps(entry)+'\n')
            ledger.append(entry)
            try:
                url='https://archive-api.open-meteo.com/v1/archive?'+urllib.parse.urlencode(req['parameters'])
                raw=urllib.request.urlopen(url,timeout=45).read()
                result=check(raw,req)
                meta=dict(request=req,url=url,retrieved_utc=datetime.now(timezone.utc).isoformat(),validation=result)
                raw_path.write_bytes(raw);save(meta_path,meta);records.append(meta)
                print(json.dumps(dict(year=req['year'],completed=len(records))),flush=True)
            except Exception as ex:
                failure=dict(request=req,error=type(ex).__name__,message=str(ex),epoch_s=time.time())
                with (OUT/'failed_acquisitions.jsonl').open('a') as f:f.write(json.dumps(failure)+'\n')
                reason='request_failed_no_automatic_retry';break
    result=dict(plan_sha256=digest(path.read_bytes()),acquirer_sha256=digest(Path(__file__).read_bytes()),
                completed=len(records),pending=3-len(records),stop_reason=reason,records=records)
    save(OUT/'acquisition.json',result)
    print(json.dumps({k:v for k,v in result.items() if k!='records'}),flush=True)


if __name__=='__main__':main()
