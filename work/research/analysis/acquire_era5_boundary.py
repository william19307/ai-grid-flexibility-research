"""Obtain next-year boundary observations for hour-ending radiation alignment.

Uses the same cache lock and conservative rate ledger as annual acquisition.
These additional requests do not alter the frozen full-year request plan.
"""
import argparse,fcntl,json,time,urllib.parse,urllib.request
from rebuild_explicit_era5 import SRC,OUT,BASE,plan,canonical,digest,existing,record,save,ensure_acquisition_allowed


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--year',type=int,required=True);args=parser.parse_args()
    p=plan()
    if args.year not in p['years']:raise ValueError('Year outside frozen plan')
    ensure_acquisition_allowed()
    requests=[]
    for original in p['requests']:
        if original['year']!=args.year:continue
        params=dict(original['parameters'],start_date=f'{args.year+1}-01-01',end_date=f'{args.year+1}-01-01')
        requests.append(dict(id=digest(canonical(params))[:24],year=args.year,parameters=params,url=BASE+'?'+urllib.parse.urlencode(params),
            expected_hours=24,conservative_call_equivalents=1,purpose='next_year_endpoint_for_hour_beginning_dispatch_intervals'))
    dest=OUT/f'boundary_plan_{args.year}.json'
    if dest.exists() and json.loads(dest.read_text())!=requests:raise ValueError('Boundary plan changed')
    if not dest.exists():save(dest,requests)
    with (SRC/'acquire.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        ledger_path=SRC/'call_ledger.jsonl'
        ledger=[json.loads(line) for line in ledger_path.read_text().splitlines()] if ledger_path.exists() else []
        records=[];reason='complete'
        for req in requests:
            cached=existing(req)
            if cached:records.append(cached);continue
            if ledger:
                delay=1-(time.time()-ledger[-1]['epoch_s'])
                if delay>0:time.sleep(delay)
            now=time.time()
            if any(sum(x['charge'] for x in ledger if now-x['epoch_s']<window)+1>limit for window,limit in [(60,450),(3600,3500),(86400,7500)]):
                reason='local_rolling_quota_guard';break
            entry=dict(epoch_s=now,id=req['id'],charge=1)
            with ledger_path.open('a') as f:f.write(json.dumps(entry)+'\n')
            ledger.append(entry)
            try:
                raw=urllib.request.urlopen(req['url'],timeout=45).read();records.append(record(req,raw,'explicit_era5_boundary_http_request'))
                print(json.dumps(dict(boundary_year=args.year,completed=len(records),expected=len(requests))),flush=True)
            except Exception as e:
                failure=dict(request=req,epoch_s=time.time(),type=type(e).__name__,message=str(e),http_status=getattr(e,'code',None))
                with (OUT/'failed_attempts.jsonl').open('a') as f:f.write(json.dumps(failure)+'\n')
                reason='request_failed_no_automatic_retry';print(json.dumps(failure),flush=True);break
        status=dict(year=args.year,completed=len(records),expected=len(requests),pending=len(requests)-len(records),stop_reason=reason,records=records)
        save(OUT/f'boundary_status_{args.year}.json',status)
        print(json.dumps({k:v for k,v in status.items() if k!='records'},indent=2),flush=True)


if __name__=='__main__':main()
