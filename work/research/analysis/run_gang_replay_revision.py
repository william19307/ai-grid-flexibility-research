"""Construct feasible gang schedules for every prespecified pilot arm."""
from pathlib import Path
import sys,json,hashlib,time
import numpy as np,pandas as pd
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'work/research/models'))
from gang_replay import schedule_gangs
from trace_occupancy import integrate_occupancy
OUT=ROOT/'outputs/research/revision/replay'


def main():
    target=OUT/'gang'
    if target.exists():raise FileExistsError(target)
    target.mkdir()
    spec=json.loads((OUT/'pilot_specification.json').read_text())
    curve_path=ROOT/'outputs/research/tables/dvfs_measured_and_derived.csv'
    curve=pd.read_csv(curve_path);curve=curve[curve.Workload=='ft_llama_8b_dolly'].sort_values('GPU power cap')
    q=curve['normalized throughput'].to_numpy();p=curve['measured_power_ratio'].to_numpy()-.1
    sources=[Path(__file__).resolve(),ROOT/'work/research/models/gang_replay.py',ROOT/'work/research/models/trace_occupancy.py']
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    (target/'source_snapshot.json').write_text(json.dumps({str(p.relative_to(ROOT)):p.read_text() for p in sources},indent=2)+'\n')
    (target/'manifest.json').write_text(json.dumps(dict(source_sha256={str(p.relative_to(ROOT)):sha(p) for p in sources},curve_sha256=sha(curve_path),
        cases=spec['cases'],criterion='Construct feasibility; no global optimality claim; identical fixed cohort/background as LP'),indent=2)+'\n')
    rows=[]
    for case in spec['cases']:
        started=time.time();cluster=case['cluster'];src=ROOT/'work/research/sources/helios_sensetime/data'/cluster
        d=pd.read_csv(src/'cluster_log.csv',parse_dates=['submit_time','start_time','end_time']);d=d[d.gpu_num>0]
        cap=pd.read_csv(src/'cluster_gpu_number.csv',parse_dates=['date']).set_index('date')['total']
        t0=pd.Timestamp(case['start']);t1=t0+pd.Timedelta(days=7);end=t0+pd.Timedelta(hours=192)
        cohort=d[(d.state=='COMPLETED')&(d.submit_time>=t0)&(d.end_time<=t1)&(d.duration>0)]
        active=d[(d.start_time<end)&(d.end_time>t0)];hours=lambda s:(s-t0).dt.total_seconds().to_numpy()/3600
        seconds=lambda s:(s-t0).dt.total_seconds().to_numpy()
        release=hours(cohort.submit_time);deadline=(seconds(cohort.end_time)+case['slack']*3600)/3600
        edge_seconds=np.unique(np.r_[np.arange(193)*3600,seconds(cohort.submit_time),deadline*3600,
                                    np.clip(seconds(active.start_time),0,192*3600),np.clip(seconds(active.end_time),0,192*3600)])
        edge_seconds=np.unique(np.round(edge_seconds).astype(np.int64));edges=edge_seconds/3600
        baseline=integrate_occupancy(seconds(active.start_time),seconds(active.end_time),active.gpu_num.to_numpy(),edge_seconds)
        capacities=cap.reindex((t0+pd.to_timedelta(edges[:-1],unit='h')).floor('D')).to_numpy(float)
        result=schedule_gangs(release,deadline,hours(cohort.start_time),hours(cohort.end_time),cohort.gpu_num.to_numpy(),edges,
                              capacities-baseline['mean_resources'],q,p)
        plan=np.array(result.pop('schedule'));indices=plan[:,0].astype(int)
        # Canonical seconds avoid false nanosecond overlaps when converting
        # an exact raw-second boundary through binary floating-point hours.
        start_seconds=np.round(plan[:,1]*3600,8);end_seconds=np.round(plan[:,2]*3600,8)
        s=start_seconds/3600;e=end_seconds/3600;mode=plan[:,3].astype(int)
        assert np.array_equal(indices,np.arange(len(cohort)))
        gpu=cohort.gpu_num.to_numpy();work=gpu*cohort.duration.to_numpy()/3600
        max_work=float(np.max(np.abs((e-s)*gpu*q[mode]-work)))
        assert max_work<1e-7 and np.min(s-release)>-1e-8 and np.max(e-deadline)<1e-8
        background=active[~active.index.isin(cohort.index)]
        # Independent sweep of combined background and all chosen whole gangs.
        audit_seconds=np.unique(np.r_[np.arange(193)*3600,start_seconds,end_seconds,np.clip(seconds(background.start_time),0,192*3600),np.clip(seconds(background.end_time),0,192*3600)])
        combined=integrate_occupancy(np.r_[seconds(background.start_time),start_seconds],np.r_[seconds(background.end_time),end_seconds],
                                     np.r_[background.gpu_num.to_numpy(),gpu],audit_seconds)
        audit_cap=cap.reindex((t0+pd.to_timedelta(audit_seconds[:-1],unit='s')).floor('D')).to_numpy(float)
        excess=max(0.,float(np.max(combined['peak_resources']-audit_cap)));assert excess<1e-7
        original=.9*float(work.sum());all_original=.1*float(capacities@np.diff(edges))+.9*baseline['total_resource_seconds']/3600
        name=f"{cluster}_{case['start']}_slack{case['slack']}";folder=target/name;folder.mkdir()
        pd.DataFrame(dict(source_row=cohort.index,start_s=start_seconds,end_s=end_seconds,start_h=s,end_h=e,mode=mode,gpus=gpu,work_gpu_h=work,release_h=release,deadline_h=deadline)).to_csv(folder/'schedule.csv',index=False)
        row=dict(run=name,**case,cohort_jobs=len(cohort),cohort_work_gpu_h=float(work.sum()),cohort_incremental_gpu_energy_saving_pct=100*(original-result['incremental_energy'])/original,
                 all_gpu_energy_saving_pct=100*(original-result['incremental_energy'])/all_original,
                 individual_upper_bound_on_cohort_saving_pct=100*(original-result['individual_lower_bound'])/original,
                 max_work_error_gpu_h=max_work,max_capacity_excess_gpus=excess,runtime_s=time.time()-started,
                 source_sha256=sha(src/'cluster_log.csv'),capacity_sha256=sha(src/'cluster_gpu_number.csv'))
        (folder/'summary.json').write_text(json.dumps({**result,**row},indent=2)+'\n');rows.append(row)
        print(json.dumps(row),flush=True)
    pd.DataFrame(rows).to_csv(target/'results.csv',index=False)
    (target/'complete.json').write_text(json.dumps(dict(cases=len(rows),all_fixed_size_nonpreemptive=True,all_feasible=True,
        limitations='Aggregate GPU gang feasibility only; hardware placement, quality, actual node energy and nonanticipative decisions unverified'),indent=2)+'\n')


if __name__=='__main__':main()
