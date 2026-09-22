"""Event-resolved fractional scheduling with per-job GPU parallelism limits.

This is a preemptive/malleable relaxation, not fixed-size gang scheduling.
Each job preserves a GPU-hour work proxy and an ex ante completion benchmark.
Prices/powers are caller-supplied assumptions, not measurements from the trace.
"""
from dataclasses import dataclass
import numpy as np
from scipy.optimize import linprog
from scipy.sparse import coo_matrix,vstack


@dataclass(frozen=True)
class ReplayJob:
    name:str
    release_h:float
    deadline_h:float
    work_gpu_h:float
    max_gpus:float


def replay(jobs,edges_h,available_gpus,rates,incremental_power,prices=None,max_variables=5000000,time_limit=120.,method='highs-ipm'):
    edges=np.asarray(edges_h,float);capacity=np.asarray(available_gpus,float);dt=np.diff(edges)
    q=np.asarray(rates,float);p=np.asarray(incremental_power,float)
    if len(edges)<2 or (dt<=0).any() or capacity.shape!=dt.shape or not np.isfinite(capacity).all() or (capacity<-1e-8).any():raise ValueError('Invalid timeline/capacity')
    if len(q)==0 or q.shape!=p.shape or (q<=0).any() or (p<0).any() or not np.isfinite(q).all() or not np.isfinite(p).all():raise ValueError('Invalid modes')
    price=np.ones(len(dt)) if prices is None else np.asarray(prices,float)
    if price.shape!=dt.shape or not np.isfinite(price).all():raise ValueError('Invalid prices')
    if len({j.name for j in jobs})!=len(jobs):raise ValueError('Duplicate jobs')
    if not jobs:raise ValueError('Empty replay')
    ji=[];ti=[];pair_job=[];pair_time=[]
    for i,j in enumerate(jobs):
        if not (edges[0]<=j.release_h<j.deadline_h<=edges[-1] and j.max_gpus>0 and j.work_gpu_h>0):raise ValueError(('Invalid job',j))
        left=np.searchsorted(edges,j.release_h);right=np.searchsorted(edges,j.deadline_h)
        if not np.isclose(edges[left],j.release_h,atol=1e-10,rtol=0) or not np.isclose(edges[right],j.deadline_h,atol=1e-10,rtol=0):raise ValueError('Every release/deadline must be an event edge')
        slots=np.arange(left,right,dtype=np.int32)
        pair_job.append(np.full(len(slots),i,dtype=np.int32));pair_time.append(slots)
    pj=np.concatenate(pair_job);pt=np.concatenate(pair_time);pairs=len(pj);M=len(q);n=pairs*M
    # Tight jobs have a mathematically forced full-speed allocation. Eliminate
    # those variables exactly, instead of weakening their windows or work.
    full=float(q.max());fixed=[];flex=[]
    for i,j in enumerate(jobs):
        maximum=j.max_gpus*(j.deadline_h-j.release_h)*full
        if j.work_gpu_h>maximum+1e-8:return dict(feasible=False,status='infeasible',witness='single-job parallelism bound',job=j.name)
        (fixed if abs(j.work_gpu_h-maximum)<1e-10 else flex).append(i)
    if fixed:
        delta=np.zeros(len(edges));allocation={'job':[],'slot':[],'mode':[],'gpu_hours':[]};fixed_energy=0.;fixed_cost=0.
        full_modes=np.flatnonzero(q==full);mode_hours=np.zeros(M)
        for i in fixed:
            j=jobs[i];left=np.searchsorted(edges,j.release_h);right=np.searchsorted(edges,j.deadline_h)
            delta[left]+=j.max_gpus;delta[right]-=j.max_gpus
            for t in range(left,right):
                m=int(full_modes[np.argmin(p[full_modes]*price[t])]);amount=j.max_gpus*dt[t]
                allocation['job'].append(i);allocation['slot'].append(t);allocation['mode'].append(m);allocation['gpu_hours'].append(float(amount))
                mode_hours[m]+=amount;fixed_energy+=amount*p[m];fixed_cost+=amount*p[m]*price[t]
        residual=capacity-np.cumsum(delta)[:-1]
        if residual.min()<-1e-7:return dict(feasible=False,status='infeasible',witness='forced full-speed jobs exceed remaining capacity')
        if flex:
            result=replay([jobs[i] for i in flex],edges,np.maximum(residual,0),q,p,price,max_variables,time_limit,method)
            if result['feasible'] is not True:return result
            rest=result['allocations'];rest['job']=[flex[i] for i in rest['job']]
            for key in allocation:allocation[key]+=rest[key]
            mode_hours+=np.asarray(result['mode_gpu_hours']);fixed_energy+=result['incremental_energy'];fixed_cost+=result['objective']
        else:
            result=dict(feasible=True,status='optimal',variables=0,maximum_work_error_gpu_h=0.,maximum_pool_excess_gpu_h=0.,maximum_job_excess_gpu_h=0.)
        result.update(allocations=allocation,mode_gpu_hours=mode_hours.tolist(),incremental_energy=fixed_energy,objective=fixed_cost,
                      total_work_gpu_h=float(sum(j.work_gpu_h for j in jobs)),jobs=len(jobs),event_intervals=len(dt),
                      forced_full_speed_jobs=len(fixed),variables_before_reduction=n,
                      scope='Fractional preemptive GPU allocation; exact elimination of tight jobs; gang packing not enforced')
        return result
    if n>max_variables:return dict(feasible=None,status='resource_limit',variables=n,limit=max_variables)
    # x = GPU-hours assigned to one job/mode within one exact event interval.
    ji=np.repeat(pj,M);ti=np.repeat(pt,M);mi=np.tile(np.arange(M),pairs);cols=np.arange(n)
    equal=coo_matrix((q[mi],(ji,cols)),shape=(len(jobs),n)).tocsr()
    total=coo_matrix((np.ones(n),(ti,cols)),shape=(len(dt),n)).tocsr()
    individual=coo_matrix((np.ones(n),(np.repeat(np.arange(pairs),M),cols)),shape=(pairs,n)).tocsr()
    upper=vstack([total,individual],format='csr')
    gpus=np.array([j.max_gpus for j in jobs]);work=np.array([j.work_gpu_h for j in jobs])
    bound=np.r_[np.maximum(capacity,0)*dt,gpus[pj]*dt[pt]]
    fit=linprog(p[mi]*price[ti],A_eq=equal,b_eq=work,A_ub=upper,b_ub=bound,bounds=(0,None),
                method=method,options={'time_limit':time_limit,'primal_feasibility_tolerance':1e-8,'dual_feasibility_tolerance':1e-8})
    if not fit.success:return dict(feasible=False if fit.status==2 else None,status='infeasible' if fit.status==2 else 'solver_unresolved',
                                  solver_status=int(fit.status),message=fit.message,variables=n)
    x=fit.x;completed=equal@x;use=total@x;per_job=individual@x
    work_error=float(np.max(np.abs(completed-work)));global_excess=float(np.max(use-capacity*dt));job_excess=float(np.max(per_job-gpus[pj]*dt[pt]))
    if max(work_error,global_excess,job_excess)>1e-5:raise AssertionError((work_error,global_excess,job_excess))
    mode_gpu_h=np.bincount(mi,weights=x,minlength=M)
    selected=np.flatnonzero(x>1e-10)
    # Compact arrays retain the actual allocation for independent replay audits.
    return dict(feasible=True,status='optimal',variables=n,event_intervals=len(dt),jobs=len(jobs),
                incremental_energy=float(mode_gpu_h@p),objective=float(fit.fun),mode_gpu_hours=mode_gpu_h.tolist(),
                total_work_gpu_h=float(work.sum()),maximum_work_error_gpu_h=work_error,
                maximum_pool_excess_gpu_h=max(0.,global_excess),maximum_job_excess_gpu_h=max(0.,job_excess),
                allocations=dict(job=ji[selected].tolist(),slot=ti[selected].tolist(),mode=mi[selected].tolist(),gpu_hours=x[selected].tolist()),
                scope='Fractional preemptive GPU allocation with per-job maximum GPU counts; gang packing and transition costs not enforced')
