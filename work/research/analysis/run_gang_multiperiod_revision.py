"""Frozen temporal validation; each failed arm remains in the outcome inventory."""
from pathlib import Path
import sys,json,hashlib,time,traceback,itertools
import numpy as np,pandas as pd
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'work/research/models'))
from gang_replay import schedule_gangs
from trace_occupancy import integrate_occupancy
OUT=ROOT/'outputs/research/revision/multiperiod'
CURVE=ROOT/'outputs/research/tables/dvfs_measured_and_derived.csv'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def freeze():
    OUT.mkdir(exist_ok=False)
    curve=pd.read_csv(CURVE)
    cases=[dict(cluster=c,start=d,workload=w,slack=s) for c,d,w,s in itertools.product(
        ['Earth','Venus','Saturn','Uranus'],['2020-05-04','2020-07-06','2020-09-07'],curve.Workload.unique().tolist(),[0,6,24])]
    sources=[Path(__file__).resolve(),ROOT/'work/research/models/gang_replay.py',ROOT/'work/research/models/trace_occupancy.py',ROOT/'work/research/analysis/verify_gang_multiperiod_revision.py']
    inputs=[CURVE]+[ROOT/'work/research/sources/helios_sensetime/data'/c/f for c in ['Earth','Venus','Saturn','Uranus'] for f in ['cluster_log.csv','cluster_gpu_number.csv']]
    snap={str(p.relative_to(ROOT)):p.read_text() for p in sources}
    (OUT/'source_snapshot.json').write_text(json.dumps(snap,indent=2)+'\n')
    spec=dict(written_unix=time.time(),cases=cases,source_sha256={str(p.relative_to(ROOT)):sha(p) for p in sources},input_sha256={str(p.relative_to(ROOT)):sha(p) for p in inputs},
        temporal_rule='First Monday of May, July and September 2020; selected by calendar, before computing outcomes; April 6 development week excluded.',
        scope='Temporal validation of a frozen retrospective aggregate-pool algorithm; not prospective validation, actual SLA, useful-work or node-power evidence.',
        cohort='COMPLETED positive-GPU positive-duration jobs submitted and ended within the 168h week; identical cohort for every curve and allowance.',
        background='All other states and cross-boundary allocations retained over 192h, including next-day arrivals.',
        hardware='Homogeneous counterfactual: each curve assigned to all eligible tasks separately; idle=0.10; curves are correlated conditions, not independent replications.',
        outcomes='Report every scheduled arm including errors; no date or cohort replacement; full job/event verification, coverage and bound gaps.',
        units='Normalized GPU-only energy; total baseline includes all published GPU idle plus above-idle energy of every recorded allocation.')
    (OUT/'manifest.json').write_text(json.dumps(spec,indent=2)+'\n')
    print(f'Frozen {len(cases)} cases before any outcomes')

def run():
    spec=json.loads((OUT/'manifest.json').read_text())
    for p,h in {**spec['source_sha256'],**spec['input_sha256']}.items():assert sha(ROOT/p)==h,p
    target=OUT/'runs';target.mkdir(exist_ok=False)
    curves=pd.read_csv(CURVE);cached=None;rows=[]
    for case in spec['cases']:
        name='_'.join(str(case[k]) for k in ['cluster','start','workload','slack']);folder=target/name;folder.mkdir()
        started=time.time()
        try:
            c=case['cluster'];src=ROOT/'work/research/sources/helios_sensetime/data'/c
            if cached!=c:
                d=pd.read_csv(src/'cluster_log.csv',parse_dates=['submit_time','start_time','end_time']);d=d[d.gpu_num>0]
                cap=pd.read_csv(src/'cluster_gpu_number.csv',parse_dates=['date']).set_index('date')['total'];cached=c
            t0=pd.Timestamp(case['start']);t1=t0+pd.Timedelta(days=7);end=t0+pd.Timedelta(hours=192)
            cohort=d[(d.state=='COMPLETED')&(d.submit_time>=t0)&(d.end_time<=t1)&(d.duration>0)]
            if cohort.empty:raise ValueError('Empty predefined cohort')
            active=d[(d.start_time<end)&(d.end_time>t0)]
            seconds=lambda s:(s-t0).dt.total_seconds().to_numpy()
            release=seconds(cohort.submit_time)/3600;deadline_seconds=seconds(cohort.end_time)+case['slack']*3600
            edge_seconds=np.unique(np.r_[np.arange(193)*3600,seconds(cohort.submit_time),deadline_seconds,np.clip(seconds(active.start_time),0,192*3600),np.clip(seconds(active.end_time),0,192*3600)])
            edges=edge_seconds/3600
            baseline=integrate_occupancy(seconds(active.start_time),seconds(active.end_time),active.gpu_num.to_numpy(),edge_seconds)
            capacities=cap.reindex(t0+pd.to_timedelta(np.floor(edge_seconds[:-1]/86400).astype(int),unit='D')).to_numpy(float)
            if not np.isfinite(capacities).all():raise ValueError('Missing capacity date')
            cv=curves[curves.Workload==case['workload']].sort_values('GPU power cap')
            q=cv['normalized throughput'].to_numpy();p=cv['measured_power_ratio'].to_numpy()-.1
            result=schedule_gangs(release,deadline_seconds/3600,seconds(cohort.start_time)/3600,seconds(cohort.end_time)/3600,cohort.gpu_num.to_numpy(),edges,capacities-baseline['mean_resources'],q,p)
            plan=np.array(result.pop('schedule'));assert np.array_equal(plan[:,0],np.arange(len(cohort)))
            begin=np.round(plan[:,1]*3600,8);finish=np.round(plan[:,2]*3600,8);mode=plan[:,3].astype(int)
            gpu=cohort.gpu_num.to_numpy();work=gpu*cohort.duration.to_numpy()/3600
            original=.9*work.sum();all_original=.1*(capacities@np.diff(edges))+.9*baseline['total_resource_seconds']/3600
            pd.DataFrame(dict(source_row=cohort.index,start_s=begin,end_s=finish,mode=mode,gpus=gpu)).to_csv(folder/'schedule.csv.gz',index=False,compression={'method':'gzip','mtime':0})
            # Coverage denominator is all observed GPU occupation in the 168h source week.
            week=integrate_occupancy(seconds(active.start_time),seconds(active.end_time),active.gpu_num.to_numpy(),[0,168*3600])
            row=dict(run=name,**case,status='constructed_pending_independent_verification',cohort_jobs=len(cohort),cohort_work_gpu_h=float(work.sum()),
                week_allocation_gpu_h=week['total_resource_seconds']/3600,cohort_share_of_week_gpu_h=float(work.sum())/(week['total_resource_seconds']/3600),
                cohort_incremental_gpu_energy_saving_pct=100*(original-result['incremental_energy'])/original,
                all_gpu_energy_saving_pct=100*(original-result['incremental_energy'])/all_original,
                individual_upper_bound_on_cohort_saving_pct=100*(original-result['individual_lower_bound'])/original,runtime_s=time.time()-started)
            (folder/'summary.json').write_text(json.dumps({**result,**row},indent=2)+'\n')
        except Exception as e:
            row=dict(run=name,**case,status='error',error_type=type(e).__name__,error=str(e),runtime_s=time.time()-started)
            (folder/'error.txt').write_text(traceback.format_exc());(folder/'summary.json').write_text(json.dumps(row,indent=2)+'\n')
        rows.append(row);pd.DataFrame(rows).to_csv(OUT/'outcomes.csv',index=False)
        print(json.dumps({k:row[k] for k in ['run','status','runtime_s']}),flush=True)
    (OUT/'complete.json').write_text(json.dumps(dict(cases=len(rows),errors=sum(r['status']=='error' for r in rows),all_planned_arms_attempted=len(rows)==len(spec['cases'])),indent=2)+'\n')

if __name__=='__main__':
    if len(sys.argv)!=2 or sys.argv[1] not in ['freeze','run']:raise SystemExit('Use freeze or run')
    freeze() if sys.argv[1]=='freeze' else run()
