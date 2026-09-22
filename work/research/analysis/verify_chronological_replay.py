"""Audit every allocation against immutable raw jobs and independent event sums."""
from pathlib import Path
from functools import lru_cache
import json,hashlib,csv
import numpy as np,pandas as pd
ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'outputs/research/revision/replay'


@lru_cache(maxsize=1)
def trace(cluster):
    src=ROOT/'work/research/sources/helios_sensetime/data'/cluster
    return (pd.read_csv(src/'cluster_log.csv',parse_dates=['submit_time','start_time','end_time']),
            pd.read_csv(src/'cluster_gpu_number.csv',parse_dates=['date']).set_index('date')['total'])


def main():
    spec=json.loads((OUT/'pilot_specification.json').read_text())
    process_file=OUT/'pilot_process_results_corrected.json'
    if not process_file.exists():process_file=OUT/'pilot_process_results.json'
    processes=json.loads(process_file.read_text())
    if len(processes)!=len(spec['cases']):raise RuntimeError('Pilot is still incomplete; do not certify a partial sweep')
    expected={f"{c['cluster']}_{c['start']}_slack{c['slack']}_pilot" for c in spec['cases']}
    assert expected=={p.get('case_id',p['name']) for p in processes}
    rows=[];max_work=max_pool=max_job=0.;statuses={};work_by_cluster={};solved=0
    for process in processes:
        folder=OUT/'runs'/process['name'];manifest=json.loads((folder/'run_manifest.json').read_text())
        snapshot=json.loads((folder/'implementation_snapshot.json').read_text())
        for path,digest in manifest['source_sha256'].items():assert hashlib.sha256(snapshot[path].encode()).hexdigest()==digest
        for path,digest in manifest['input_sha256'].items():assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==digest
        summary=json.loads((folder/'summary.json').read_text());solution=json.loads((folder/'solution.json').read_text())
        jobs=json.loads((folder/'jobs.json').read_text());inp=np.load(folder/'event_inputs.npz')
        a=manifest['parameters'];edges=inp['edges_h'];dt=np.diff(edges);T=len(dt)
        raw,caps=trace(a['cluster']);raw=raw[raw.gpu_num>0]
        start=pd.Timestamp(a['start']);cohort_end=start+pd.Timedelta(days=7);end=start+pd.Timedelta(hours=192)
        cohort=raw[(raw.state=='COMPLETED')&(raw.submit_time>=start)&(raw.end_time<=cohort_end)&(raw.duration>0)]
        assert [str(i) for i in cohort.index]==[j['name'] for j in jobs]
        work=np.array([j['work_gpu_h'] for j in jobs]);gpus=np.array([j['max_gpus'] for j in jobs])
        release=np.array([j['release_h'] for j in jobs]);deadline=np.array([j['deadline_h'] for j in jobs])
        assert np.allclose(work,(cohort.gpu_num*cohort.duration/3600).to_numpy(),atol=1e-10)
        assert np.array_equal(gpus,cohort.gpu_num.to_numpy())
        assert np.allclose(release,(cohort.submit_time-start).dt.total_seconds()/3600,atol=1e-10)
        assert np.allclose(deadline,(cohort.end_time-start).dt.total_seconds()/3600+a['slack'],atol=1e-10)
        fingerprint=hashlib.sha256(np.c_[cohort.index,work,gpus,release].tobytes()).hexdigest()
        if a['cluster'] in work_by_cluster:assert fingerprint==work_by_cluster[a['cluster']]
        else:work_by_cluster[a['cluster']]=fingerprint
        # Independently sum start/end jumps, rather than reuse the interval integrator.
        bg=raw[~raw.index.isin(cohort.index)];bg=bg[(bg.start_time<end)&(bg.end_time>start)]
        left=np.maximum(0,(bg.start_time-start).dt.total_seconds().to_numpy()/3600)
        right=np.minimum(192,(bg.end_time-start).dt.total_seconds().to_numpy()/3600)
        delta=np.zeros(T+1)
        np.add.at(delta,np.searchsorted(edges,left),bg.gpu_num.to_numpy())
        np.add.at(delta,np.searchsorted(edges,right),-bg.gpu_num.to_numpy())
        direct_bg=np.cumsum(delta)[:-1]
        assert np.allclose(direct_bg,inp['background_gpus'],atol=1e-6)
        direct_cap=caps.reindex((start+pd.to_timedelta(edges[:-1],unit='h')).floor('D')).to_numpy(float)
        assert np.array_equal(direct_cap,inp['capacity_gpus'])
        assert np.allclose(direct_cap-direct_bg,inp['available_gpus'],atol=1e-6)
        status=solution['status'];statuses[status]=statuses.get(status,0)+1
        assert status==process['status']==summary['execution_status']
        row=dict(run=process['name'],cluster=a['cluster'],start=a['start'],slack_h=a['slack'],status=status,
                 cohort_jobs=len(jobs),cohort_gpu_hours=float(work.sum()),coverage_of_observed_allocation=summary['cohort_share_of_observed_192h'],
                 cohort_incremental_gpu_energy_saving_pct=None,all_gpu_energy_saving_pct=None,
                 deadline_violation_h=None,max_job_excess_gpu_h=None,max_pool_excess_gpu_h=None,
                 variables=solution.get('variables'),runtime_s=summary['runtime_s'])
        if solution['feasible'] is True:
            allocation=np.load(folder/solution['allocation_file'])
            ji=allocation['job'];ti=allocation['slot'];mi=allocation['mode'];x=allocation['gpu_hours']
            assert len(ji)==len(ti)==len(mi)==len(x) and (x>=0).all()
            assert np.all((ji>=0)&(ji<len(jobs))) and np.all((ti>=0)&(ti<T)) and np.all((mi>=0)&(mi<len(inp['rates'])))
            violation=float(max(0.,np.max(release[ji]-edges[ti]),np.max(edges[ti+1]-deadline[ji])))
            assert violation<1e-8
            completed=np.bincount(ji,weights=x*inp['rates'][mi],minlength=len(jobs))
            work_error=float(np.max(np.abs(completed-work)));max_work=max(max_work,work_error);assert work_error<1e-5
            usage=np.bincount(ti,weights=x,minlength=T)
            pool_error=max(0.,float(np.max(usage-inp['available_gpus']*dt)));max_pool=max(max_pool,pool_error);assert pool_error<1e-5
            key=ji.astype(np.int64)*T+ti;unique,index=np.unique(key,return_inverse=True)
            totals=np.bincount(index,weights=x);j=unique//T;t=unique%T
            job_error=max(0.,float(np.max(totals-gpus[j]*dt[t])));max_job=max(max_job,job_error);assert job_error<1e-5
            energy=float(np.dot(x,inp['incremental_power'][mi]));assert np.isclose(energy,solution['incremental_energy'],atol=1e-5,rtol=1e-10)
            baseline=.9*float(work.sum());all_base=.1*float(direct_cap@dt)+.9*float(inp['observed_gpus']@dt)
            gain=baseline-energy;cohort_pct=100*gain/baseline;all_pct=100*gain/all_base
            assert np.isclose(cohort_pct,summary['cohort_incremental_gpu_energy_saving_pct'],atol=1e-7)
            assert np.isclose(all_pct,summary['all_gpu_energy_saving_pct'],atol=1e-7)
            assert gain>=-1e-5
            row.update(cohort_incremental_gpu_energy_saving_pct=cohort_pct,all_gpu_energy_saving_pct=all_pct,
                       deadline_violation_h=violation,max_job_excess_gpu_h=job_error,max_pool_excess_gpu_h=pool_error)
            solved+=1
        rows.append(row)
    with (OUT/'pilot_results.csv').open('w') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');writer.writeheader();writer.writerows(rows)
    report=dict(planned_cases=len(spec['cases']),terminal_cases=len(rows),optimal_cases=solved,status_counts=statuses,
                same_cohort_work_and_resources_across_slack=True,all_background_intervals_and_raw_job_fields_verified=True,
                maximum_work_error_gpu_h=max_work,maximum_pool_excess_gpu_h=max_pool,maximum_job_excess_gpu_h=max_job,
                limitations=['Fractional allocations do not certify feasible gang packing.',
                             'Actual deadlines and node power remain unmeasured.',
                             'One week and a single hypothetical common DVFS curve do not establish generality.',
                             'Non-optimal terminal statuses are unresolved, not discarded or labelled infeasible.'])
    (OUT/'pilot_verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))


if __name__=='__main__':main()
