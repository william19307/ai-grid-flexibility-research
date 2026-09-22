"""Independent raw-job checks, event-sum capacity and pairwise energy bound."""
from pathlib import Path
import json,hashlib
import numpy as np,pandas as pd
ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'outputs/research/revision/replay/gang'


def main():
    manifest=json.loads((OUT/'manifest.json').read_text());snap=json.loads((OUT/'source_snapshot.json').read_text())
    for path,digest in manifest['source_sha256'].items():assert hashlib.sha256(snap[path].encode()).hexdigest()==digest
    curve_path=ROOT/'outputs/research/tables/dvfs_measured_and_derived.csv'
    assert hashlib.sha256(curve_path.read_bytes()).hexdigest()==manifest['curve_sha256']
    curve=pd.read_csv(curve_path);curve=curve[curve.Workload=='ft_llama_8b_dolly'].sort_values('GPU power cap')
    q=curve['normalized throughput'].to_numpy();p=curve['measured_power_ratio'].to_numpy()-.1
    rows=[];cache={};max_work=max_peak=max_late=0.
    for case in manifest['cases']:
        c=case['cluster'];name=f"{c}_{case['start']}_slack{case['slack']}";folder=OUT/name
        summary=json.loads((folder/'summary.json').read_text());plan=pd.read_csv(folder/'schedule.csv',float_precision='round_trip')
        src=ROOT/'work/research/sources/helios_sensetime/data'/c
        assert hashlib.sha256((src/'cluster_log.csv').read_bytes()).hexdigest()==summary['source_sha256']
        assert hashlib.sha256((src/'cluster_gpu_number.csv').read_bytes()).hexdigest()==summary['capacity_sha256']
        if c not in cache:
            cache={c:(pd.read_csv(src/'cluster_log.csv',parse_dates=['submit_time','start_time','end_time']),pd.read_csv(src/'cluster_gpu_number.csv',parse_dates=['date']).set_index('date')['total'])}
        raw,cap=cache[c];raw=raw[raw.gpu_num>0];start=pd.Timestamp(case['start']);cohort_end=start+pd.Timedelta(days=7);end=start+pd.Timedelta(hours=192)
        cohort=raw[(raw.state=='COMPLETED')&(raw.submit_time>=start)&(raw.end_time<=cohort_end)&(raw.duration>0)]
        assert plan.source_row.is_unique and plan.source_row.tolist()==cohort.index.tolist()
        gpu=cohort.gpu_num.to_numpy();work=gpu*cohort.duration.to_numpy()/3600;mode=plan['mode'].to_numpy(int)
        begin=np.round(plan.start_s.to_numpy(),8);finish=np.round(plan.end_s.to_numpy(),8)
        assert np.array_equal(plan.gpus.to_numpy(),gpu) and (finish>begin).all()
        release=(cohort.submit_time-start).dt.total_seconds().to_numpy();deadline=(cohort.end_time-start).dt.total_seconds().to_numpy()+3600*case['slack']
        error=float(np.max(np.abs((finish-begin)/3600*gpu*q[mode]-work)));max_work=max(max_work,error);assert error<1e-7
        violation=max(0.,float(np.max(release-begin)),float(np.max(finish-deadline)));max_late=max(max_late,violation);assert violation<1e-7
        bg=raw[~raw.index.isin(cohort.index)];bg=bg[(bg.start_time<end)&(bg.end_time>start)]
        bg_start=np.maximum(0,(bg.start_time-start).dt.total_seconds().to_numpy());bg_end=np.minimum(192*3600,(bg.end_time-start).dt.total_seconds().to_numpy())
        times=np.r_[bg_start,bg_end,begin,finish,np.arange(193)*3600]
        weights=np.r_[bg.gpu_num.to_numpy(),-bg.gpu_num.to_numpy(),gpu,-gpu,np.zeros(193)]
        events,inv=np.unique(times,return_inverse=True);usage=np.cumsum(np.bincount(inv,weights=weights))[:-1]
        dates=start+pd.to_timedelta(np.floor(events[:-1]/86400).astype(int),unit='D');limits=cap.reindex(dates).to_numpy(float)
        assert np.isfinite(limits).all()
        excess=max(0.,float(np.max(usage-limits)));max_peak=max(max_peak,excess);assert excess==0.
        assert np.min(usage)>=0
        energy=float(np.sum((finish-begin)/3600*gpu*p[mode]));baseline=.9*work.sum()
        # Enumerate every pair of speed points including idle; no shared hull code.
        speeds=np.r_[0,q];powers=np.r_[0,p];window=(deadline-release)/3600;rho=work/gpu/window
        lower=np.full(len(work),np.inf)
        for i in range(len(speeds)):
            for j in range(i+1,len(speeds)):
                if speeds[j]==speeds[i]:continue
                weight=(rho-speeds[i])/(speeds[j]-speeds[i]);valid=(weight>=-1e-12)&(weight<=1+1e-12)
                cost=gpu*window*(powers[i]+weight*(powers[j]-powers[i]))
                lower[valid]=np.minimum(lower[valid],cost[valid])
        assert np.isfinite(lower).all() and np.isclose(lower.sum(),summary['individual_lower_bound'],atol=1e-6,rtol=1e-10)
        assert lower.sum()<=energy+1e-6<=baseline+1e-6
        bg_gpu_h=float(np.dot(bg_end-bg_start,bg.gpu_num.to_numpy())/3600)
        daily_capacity=cap.reindex(pd.date_range(start,periods=8,freq='D')).to_numpy(float)
        total_baseline=.1*daily_capacity.sum()*24+.9*(bg_gpu_h+work.sum())
        cohort_pct=100*(baseline-energy)/baseline;all_pct=100*(baseline-energy)/total_baseline
        assert np.isclose(cohort_pct,summary['cohort_incremental_gpu_energy_saving_pct'],atol=1e-7)
        assert np.isclose(all_pct,summary['all_gpu_energy_saving_pct'],atol=1e-7)
        rows.append(dict(run=name,**case,jobs=len(work),fixed_work_gpu_h=float(work.sum()),
            cohort_incremental_gpu_energy_saving_pct=cohort_pct,all_gpu_energy_saving_pct=all_pct,
            upper_bound_on_cohort_saving_pct=100*(baseline-lower.sum())/baseline,
            exact_gang_capacity_excess_gpus=excess,max_work_error_gpu_h=error,max_deadline_or_release_violation_s=violation))
    pd.DataFrame(rows).to_csv(OUT/'certified_results.csv',index=False)
    report=dict(cases=len(rows),all_declared_cases_present=len(rows)==len(manifest['cases']),
        all_jobs_exact_gpu_counts_nonpreemptive=True,all_background_states_and_boundaries_preserved=True,
        maximum_work_error_gpu_h=max_work,maximum_aggregate_gpu_excess=max_peak,maximum_service_window_violation_s=max_late,
        independent_lower_bound_pair_enumeration=True,
        scope='Certified schedules and energy brackets within the aggregate, retrospective, homogeneous-workload model; no whole-node or grid benefit certification.')
    (OUT/'independent_verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))


if __name__=='__main__':main()
