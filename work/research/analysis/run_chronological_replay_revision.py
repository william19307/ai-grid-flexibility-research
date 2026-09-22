"""Real-order completed-job cohort plus immutable all-state background."""
from pathlib import Path
from dataclasses import asdict
import sys,json,argparse,hashlib,time
import numpy as np,pandas as pd
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'work/research/models'))
from chronological_replay import ReplayJob,replay
from trace_occupancy import integrate_occupancy


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--cluster',default='Earth');ap.add_argument('--start',default='2020-04-06')
    ap.add_argument('--slack',type=float,default=0.);ap.add_argument('--max-variables',type=int,default=5000000)
    ap.add_argument('--time-limit',type=float,default=120.);ap.add_argument('--run-label',default='');a=ap.parse_args()
    if a.slack not in [0.,6.,24.]:raise ValueError('Predefined extra-completion slack is 0, 6 or 24 h')
    if a.run_label and (not a.run_label.replace('_','').isalnum()):raise ValueError('Invalid run label')
    suffix='_'+a.run_label if a.run_label else ''
    out=ROOT/'outputs/research/revision/replay/runs'/f'{a.cluster}_{a.start}_slack{a.slack:g}{suffix}'
    if out.exists():raise FileExistsError(out)
    out.mkdir(parents=True);started=time.time()
    src=ROOT/'work/research/sources/helios_sensetime/data'/a.cluster
    inputs=[src/'cluster_log.csv',src/'cluster_gpu_number.csv',ROOT/'outputs/research/tables/dvfs_measured_and_derived.csv']
    codes=[Path(__file__).resolve(),ROOT/'work/research/models/chronological_replay.py',ROOT/'work/research/models/trace_occupancy.py']
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    manifest=dict(parameters=vars(a),started_unix=started,input_sha256={str(p.relative_to(ROOT)):sha(p) for p in inputs},
                  source_sha256={str(p.relative_to(ROOT)):sha(p) for p in codes},
                  assumptions=['Cohort COMPLETED, submitted and finished within a prespecified seven-day window.',
                    'All other GPU allocation intervals remain immutable background, including tail-window arrivals.',
                    'Deadline = observed completion + specified extra slack; retrospective benchmark, not contractual SLA.',
                    'Work = recorded GPU count times duration; homogeneous counterfactual DVFS curve, not measured useful work.',
                    'Fractional preemptive resource relaxation; gang scheduling, checkpoints and hardware locality not represented.'])
    (out/'run_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (out/'implementation_snapshot.json').write_text(json.dumps({str(p.relative_to(ROOT)):p.read_text() for p in codes},indent=2)+'\n')
    d=pd.read_csv(inputs[0],parse_dates=['submit_time','start_time','end_time']);d=d[d.gpu_num>0].copy()
    if d.job_id.duplicated().any() or d[['submit_time','start_time','end_time','gpu_num','duration']].isna().any().any():raise ValueError('Trace invalid/duplicate GPU jobs')
    if ((d.end_time-d.start_time).dt.total_seconds()!=d.duration).any() or (d.duration<0).any() or (d.start_time<d.submit_time).any():raise ValueError('Runtime or release mismatch')
    t0=pd.Timestamp(a.start);t1=t0+pd.Timedelta(days=7);end=t1+pd.Timedelta(hours=24)
    eligible=(d.state=='COMPLETED')&(d.submit_time>=t0)&(d.end_time<=t1)&(d.duration>0)
    cohort=d[eligible].copy();bg=d[~eligible].copy()
    overlap=(d.start_time<end)&(d.end_time>t0);all_active=d[overlap].copy()
    bg=bg[(bg.start_time<end)&(bg.end_time>t0)]
    hours=lambda s:(s-t0).dt.total_seconds().to_numpy()/3600
    seconds=lambda s:(s-t0).dt.total_seconds().to_numpy()
    release=hours(cohort.submit_time);deadline=(seconds(cohort.end_time)+a.slack*3600)/3600
    capacity=pd.read_csv(inputs[1],parse_dates=['date']).set_index('date')['total']
    # Fixed 192-hour domain in every slack arm, with real tail background.
    edge_seconds=np.unique(np.r_[np.arange(193,dtype=np.int64)*3600,seconds(cohort.submit_time),seconds(cohort.end_time)+a.slack*3600,
        seconds(cohort.start_time),seconds(cohort.end_time),np.clip(seconds(bg.start_time),0,192*3600),np.clip(seconds(bg.end_time),0,192*3600)])
    edges=edge_seconds/3600
    if edges[0]!=0 or edges[-1]!=192:raise ValueError('Unexpected event outside fixed replay domain')
    dates=(t0+pd.to_timedelta(edges[:-1],unit='h')).floor('D')
    caps=capacity.reindex(dates).to_numpy(float)
    if not np.isfinite(caps).all():raise ValueError('Missing reported capacity')
    background=integrate_occupancy(seconds(bg.start_time),seconds(bg.end_time),bg.gpu_num.to_numpy(),edge_seconds)
    observed=integrate_occupancy(seconds(all_active.start_time),seconds(all_active.end_time),all_active.gpu_num.to_numpy(),edge_seconds)
    bg_gpus=background['mean_resources'];avail=caps-bg_gpus
    if np.max(observed['peak_resources']-caps)>1e-7 or np.min(avail)<-1e-7:raise ValueError('Observed allocation exceeds capacity')
    jobs=[ReplayJob(str(idx),float(r),float(dl),float(row.gpu_num*row.duration/3600),float(row.gpu_num))
          for (idx,row),r,dl in zip(cohort.iterrows(),release,deadline)]
    curve=pd.read_csv(inputs[2]);curve=curve[curve.Workload=='ft_llama_8b_dolly'].sort_values('GPU power cap')
    q=curve['normalized throughput'].to_numpy();power=curve['measured_power_ratio'].to_numpy()
    # GPU-only idle share is assumed; non-GPU energy is not inferred here.
    gpu_idle=.1;increment=power-gpu_idle
    result=replay(jobs,edges,avail,q,increment,max_variables=a.max_variables,time_limit=a.time_limit)
    baseline=sum(j.work_gpu_h for j in jobs)*(1-gpu_idle)
    total_original=observed['total_resource_seconds']/3600
    baseline_all_gpu_energy=gpu_idle*float(caps@np.diff(edges))+(1-gpu_idle)*total_original
    saving=baseline-result['incremental_energy'] if result['feasible'] else None
    summary=dict(parameters=vars(a),cohort_jobs=len(jobs),background_jobs=len(bg),cohort_gpu_hours=sum(j.work_gpu_h for j in jobs),
                 observed_all_state_gpu_hours_192h=total_original,cohort_share_of_observed_192h= sum(j.work_gpu_h for j in jobs)/total_original,
                 baseline_incremental_gpu_energy=baseline,gpu_idle_assumption=gpu_idle,
                 cohort_incremental_gpu_energy_saving_pct=100*saving/baseline if result['feasible'] else None,
                 all_gpu_energy_saving_pct=100*saving/baseline_all_gpu_energy if result['feasible'] else None,
                 baseline_all_gpu_normalized_energy=baseline_all_gpu_energy,
                 metric_scope='Both energy metrics are assumed GPU-only normalized energy; the first excludes idle/background, the second includes them; neither is node or site energy.',
                 execution_status=result['status'],runtime_s=time.time()-started,
                 evidence='Retrospective homogeneous-curve fractional replay; not calibrated node energy, realized service or grid benefit')
    (out/'jobs.json').write_text(json.dumps([asdict(j) for j in jobs],indent=2)+'\n')
    np.savez_compressed(out/'event_inputs.npz',edges_h=edges,available_gpus=avail,capacity_gpus=caps,background_gpus=bg_gpus,
                        observed_gpus=observed['mean_resources'],rates=q,incremental_power=increment)
    if result['feasible']:
        allocations=result.pop('allocations')
        np.savez_compressed(out/'allocations.npz',job=np.asarray(allocations['job'],np.int32),slot=np.asarray(allocations['slot'],np.int32),
                            mode=np.asarray(allocations['mode'],np.int8),gpu_hours=np.asarray(allocations['gpu_hours'],float))
        result['allocation_file']='allocations.npz'
    (out/'solution.json').write_text(json.dumps(result)+'\n')
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    (out/'terminal.json').write_text(json.dumps(dict(status=result['status'],feasible=result['feasible']),indent=2)+'\n')
    print(json.dumps(summary,indent=2),flush=True)


if __name__=='__main__':main()
