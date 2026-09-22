"""Fixed-window diagnostics for the historical resampled Helios workload.

Deadlines are analyst scenarios, not measured SLAs. No feasibility guards.
The full-tail variant keeps whole sampled runtimes and later deadlines; it is
a finite-cohort diagnostic, not a steady-state or annual workload replay.
"""
from functools import lru_cache
from pathlib import Path
import numpy as np
import pandas as pd
from sequential_tasks import Job

ROOT=Path(__file__).resolve().parents[3]


@lru_cache(maxsize=1)
def source_table():
    d=pd.read_csv(ROOT/'work/research/prepared/helios_completed_gpu_jobs_sample.csv.gz')
    if d[['gpu_num','duration','queue']].isna().any().any() or (d.gpu_num<=0).any() or (d.duration<=0).any() or (d.queue<0).any():
        raise ValueError('Invalid source workload')
    return d


def sample_fixed_windows(T,u,start_hour,slack_mult,slack_base_h,seed,boundary='historical_clip'):
    if boundary not in {'historical_clip','full_tail'}:raise ValueError(boundary)
    if T<=0 or not np.isfinite(u) or u<=0 or slack_mult<0 or slack_base_h<0:raise ValueError('Invalid workload scenario')
    d=source_table();rng=np.random.default_rng(seed);byh=d.groupby('hour').size();byh=byh/byh.sum()
    ref_gpus=float((d.gpu_num*d.duration).sum()/d.duration.sum())
    batches={};sampled=0;runtime_crossing=0;deadline_crossing=0;raw_gpu_hours=0.;clipped_gpu_hours=0.
    for t in range(T):
        h=(start_hour+t)%24;n=rng.poisson(max(1e-9,byh.get(h,0))*40)
        if n==0:continue
        sub=d.iloc[rng.choice(len(d),n,replace=True)]
        for _,r in sub.iterrows():
            runtime=float(r.duration/3600);raw_gpu_hours+=float(r.gpu_num*runtime);sampled+=1
            runtime_crossing+=int(t+runtime>T)
            clipped_gpu_hours+=float(r.gpu_num*max(0.,runtime-(T-t)))
            slack=float(r.queue/3600*slack_mult+slack_base_h)
            deadline_crossing+=int(t+int(np.ceil(runtime))+int(np.ceil(slack))>T)
            run_h=min(runtime,T-t) if boundary=='historical_clip' else runtime
            deadline=t+int(np.ceil(run_h))+int(np.ceil(slack))
            if boundary=='historical_clip':deadline=min(T,deadline)
            deadline=max(t+1,deadline)
            work=float(r.gpu_num*run_h/ref_gpus/24.)
            batches[(t,deadline)]=batches.get((t,deadline),0.)+work
    if not batches:raise ValueError('Empty sampled cohort')
    target=u*T;factor=target/sum(batches.values())
    jobs=[Job(f'h{r}_d{d}',r,d,w*factor) for (r,d),w in sorted(batches.items())]
    horizon=max(T,max(j.deadline for j in jobs))
    meta=dict(boundary=boundary,arrival_horizon=T,service_horizon=horizon,target_work=target,
              actual_work=sum(j.work for j in jobs),target_utilization_over_arrival_horizon=u,
              service_horizon_average_utilization=target/horizon,slack_multiplier=slack_mult,slack_base_h=slack_base_h,
              seed=seed,sampled_jobs=sampled,aggregated_batches=len(jobs),runtime_crossing_jobs=runtime_crossing,
              deadline_crossing_jobs=deadline_crossing,raw_sampled_gpu_hours=raw_gpu_hours,
              gpu_hours_clipped_by_historical_boundary=clipped_gpu_hours,
              raw_gpu_hour_clipping_share=clipped_gpu_hours/raw_gpu_hours,
              work_normalization_factor=factor,no_feasibility_dependent_changes=True,
              deadlines_evidence='analyst-assumed queue multiplier plus additive slack; not measured service limits',
              scope='resampled completed-job cohort, fractional homogeneous pool, no job-specific parallelism cap')
    return jobs,horizon,meta


def demand_bound(jobs,rate=1.):
    """Exact maximum interval demand for preemptive single-pool fixed windows.

Any interval must accommodate all jobs whose complete windows it contains.
Return an explicit infeasibility witness; independent EDF and LP checks are
used by the audit to verify both feasibility and the scaling threshold.
"""
    if rate<=0:raise ValueError('Invalid rate')
    releases=np.array([j.release for j in jobs]);deadlines=np.array([j.deadline for j in jobs]);work=np.array([j.work for j in jobs])
    best=0.;witness=None
    for a in np.unique(releases):
        for b in np.unique(deadlines[deadlines>a]):
            contained=(releases>=a)&(deadlines<=b);required=float(work[contained].sum())
            density=required/(float(b-a)*rate)
            if density>best:
                best=density;witness=dict(start=int(a),end=int(b),required_work=required,available_work=float(b-a)*rate,
                                          contained_jobs=[jobs[i].name for i in np.flatnonzero(contained)])
    return dict(maximum_density=best,maximum_work_scale=1/best if best>0 else None,
                feasible=best<=1+1e-9,critical_interval=witness)


def edf_replay(jobs,horizon,rate=1.):
    """Independent greedy full-speed replay with explicit late/unserved work."""
    remaining=np.array([j.work for j in jobs],float);profile=np.zeros(horizon);completion={}
    for t in range(horizon):
        free=rate
        ready=sorted([i for i,j in enumerate(jobs) if j.release<=t<j.deadline and remaining[i]>1e-10],
                     key=lambda i:(jobs[i].deadline,jobs[i].release,jobs[i].name))
        for i in ready:
            take=min(free,remaining[i]);remaining[i]-=take;free-=take;profile[t]+=take
            if remaining[i]<=1e-10:completion[jobs[i].name]=t+1
            if free<=1e-10:break
    missed=[dict(job=j.name,release=j.release,deadline=j.deadline,unserved_work=float(remaining[i]))
            for i,j in enumerate(jobs) if remaining[i]>1e-7]
    return dict(feasible=not missed,unfinished_work=float(remaining.sum()),missed_jobs=missed,
                completed_work=float(profile.sum()),slot_work=profile.tolist(),completion_slot=completion)
