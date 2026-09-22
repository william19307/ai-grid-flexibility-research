"""Recalculate strict witnesses and audit chronological output against raw rows."""
from pathlib import Path
import json,csv,hashlib
import numpy as np,pandas as pd
ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'outputs/research/revision/service'


def main():
    manifest=json.loads((OUT/'run_manifest.json').read_text());snapshot=json.loads((OUT/'implementation_snapshot.json').read_text())
    for path,digest in manifest['source_sha256'].items():assert hashlib.sha256(snapshot[path].encode()).hexdigest()==digest
    for path,digest in manifest['input_sha256'].items():assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==digest
    table=pd.read_csv(OUT/'strict_service_results.csv').set_index('case');shapes={};infeasible=0;worst=0.
    for path in sorted((OUT/'cases').glob('*.json')):
        case=json.loads(path.read_text());p=case['parameters'];jobs=case['jobs'];row=table.loc[case['name']]
        target=168*p['u'];assert np.isclose(sum(j['work'] for j in jobs),target,atol=1e-10)
        # source_meta intentionally records the unit-utilization cohort before scaling.
        assert case['source_meta']['target_utilization_over_arrival_horizon']==1.
        shape=[(j['release'],j['deadline'],j['work']/p['u']) for j in jobs]
        key=(p['season'],p['slack'],p['boundary'])
        if key in shapes:assert np.allclose(shape,shapes[key],atol=1e-12)
        else:shapes[key]=shape
        max_density=0.
        for left in {j['release'] for j in jobs}:
            for right in {j['deadline'] for j in jobs if j['deadline']>left}:
                work=sum(j['work'] for j in jobs if j['release']>=left and j['deadline']<=right)
                max_density=max(max_density,work/(right-left))
        assert np.isclose(max_density,case['demand_bound']['maximum_density'],atol=1e-10)
        assert np.isclose(p['u']/max_density,row.maximum_feasible_arrival_utilization,atol=1e-10)
        feasible=max_density<=1+1e-9
        assert feasible==case['lp']['feasible']==case['edf']['feasible']==bool(row.strict_feasible)
        if not feasible:
            infeasible+=1;w=case['demand_bound']['critical_interval']
            total=sum(j['work'] for j in jobs if j['name'] in w['contained_jobs'])
            assert total>w['end']-w['start']+1e-7
        residual=abs(case['edf']['completed_work']+case['edf']['unfinished_work']-target)
        worst=max(worst,residual);assert residual<1e-8
    chronology=json.loads((OUT/'chronological/audit.json').read_text())
    hourly=pd.read_csv(OUT/'chronological/hourly_allocations.csv.gz',parse_dates=['time'])
    max_integral_error=0.;sample_count=0;duplicate_gpu_ids={};post_hashes={}
    for cluster,meta in chronology['clusters'].items():
        src=ROOT/'work/research/sources/helios_sensetime/data'/cluster
        path=src/'cluster_log.csv';cap_path=src/'cluster_gpu_number.csv'
        for p,digest in [(path,meta['source_sha256']),(cap_path,meta['capacity_sha256'])]:
            assert hashlib.sha256(p.read_bytes()).hexdigest()==digest;post_hashes[str(p.relative_to(ROOT))]=digest
        raw=pd.read_csv(path,parse_dates=['start_time','end_time']);raw=raw[raw.gpu_num>0]
        duplicate_gpu_ids[cluster]=int(raw.job_id.duplicated().sum());assert duplicate_gpu_ids[cluster]==0
        h=hourly[hourly.cluster==cluster].reset_index(drop=True)
        assert np.isclose(h.all_mean_gpus.sum(),meta['total_gpu_hours'],atol=1e-7)
        assert np.isclose(h.completed_mean_gpus.sum(),meta['completed_gpu_hours'],atol=1e-7)
        for i in np.unique(np.linspace(0,len(h)-1,8,dtype=int)):
            row=h.iloc[i];start=row.time;end=start+pd.Timedelta(hours=1)
            overlap=raw[(raw.start_time<end)&(raw.end_time>start)].copy()
            left=np.maximum((overlap.start_time-start).dt.total_seconds().to_numpy(),0)
            right=np.minimum((overlap.end_time-start).dt.total_seconds().to_numpy(),3600)
            gpu=overlap.gpu_num.to_numpy();done=(overlap.state=='COMPLETED').to_numpy()
            for mask,mean_col,peak_col in [(np.ones(len(gpu),bool),'all_mean_gpus','all_peak_gpus'),(done,'completed_mean_gpus','completed_peak_gpus')]:
                expected=float(np.sum((right-left)[mask]*gpu[mask])/3600)
                error=abs(expected-float(row[mean_col]));max_integral_error=max(max_integral_error,error);assert error<1e-8
                cuts=sorted(set([0.,3600.]+list(left[mask])+list(right[mask])))
                peak=max([float(gpu[mask& (left<=(a+b)/2)&(right>(a+b)/2)].sum()) for a,b in zip(cuts[:-1],cuts[1:])] or [0.])
                assert peak==float(row[peak_col]);sample_count+=1
        assert int((h.all_peak_gpus>h.reported_gpus+1e-7).sum())==meta['hours_all_peak_exceeds_reported_capacity']
    source_paths=['work/research/analysis/audit_chronological_helios.py','work/research/models/trace_occupancy.py',
                  'work/research/analysis/verify_service_results.py','work/research/analysis/validate_strict_service_revision.py']
    report=dict(strict_cases=len(table),strict_infeasible=infeasible,all_witnesses_recomputed=True,
                fixed_windows_and_work_shape_identical_across_utilization=True,
                max_edf_work_accounting_error=worst,chronological_raw_row_sample_checks=sample_count,
                max_sampled_gpu_hour_error=max_integral_error,duplicate_gpu_job_ids=duplicate_gpu_ids,
                chronological_input_sha256=post_hashes,
                source_sha256_post_run={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in source_paths},
                provenance_note='Chronological source hashes verified after run; not represented as a pre-run code snapshot.',
                scope='Strict-case checks cover all 64 cases; raw chronological hour checks sample 8 hours per cluster and 2 state groups.')
    (OUT/'independent_verification.json').write_text(json.dumps(report,indent=2)+'\n')
    (OUT/'chronological/source_snapshot_post_run.json').write_text(json.dumps({p:(ROOT/p).read_text() for p in source_paths},indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if 'sha256' not in k},indent=2))


if __name__=='__main__':main()
