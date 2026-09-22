"""Lexicographic energy/earliness baseline and EDF reconstruction.

This baseline uses no grid prices. Slower modes still lengthen execution; call
it energy-oriented non-idling EDF, never physically unchanged load timing.
It has full workload foresight, like the coordinated comparison.
"""
import numpy as np
from sequential_tasks import schedule


def energy_earliest_edf(jobs,q,power,horizon,idle_power):
    q=np.asarray(q,float);power=np.asarray(power,float)
    scale=float(np.max(power))
    first=schedule(jobs,q,power/scale,horizon,idle_power/scale,prices=np.ones(horizon))
    if not first['feasible']:return first
    # Solve at normalized power to avoid tolerance scaling with provincial MW.
    delay=np.array([[t-j.release for t in range(horizon)] for j in jobs],float)
    second=schedule(jobs,q,power/scale,horizon,idle_power/scale,prices=np.zeros(horizon),
                    service_cost_per_work=delay,energy_limit=first['energy']+1e-8)
    if not second['feasible']:return second
    mode_time=np.zeros((horizon,len(q)))
    for a in second['allocations']:
        mode_time[a['slot'],a['mode']]+=a['pool_fraction']
    # Relabel the feasible aggregate speed profile using a common EDF policy.
    remaining=np.array([j.work for j in jobs],float)
    allocations=[];max_idle_with_backlog=0.;max_overdue=0.;max_fraction=0.
    for t in range(horizon):
        ready=sorted([i for i,j in enumerate(jobs) if j.release<=t<j.deadline and remaining[i]>1e-9],
                     key=lambda i:(jobs[i].deadline,jobs[i].release,jobs[i].name))
        for m in range(len(q)):
            capacity=float(mode_time[t,m])
            for i in ready:
                take=min(capacity,remaining[i]/q[m])
                if take>1e-10:
                    work=take*q[m];remaining[i]-=work;capacity-=take
                    allocations.append(dict(job=jobs[i].name,slot=t,mode=m,pool_fraction=take,work=work))
            if capacity>1e-6:raise AssertionError(('Unassigned mode capacity',t,m,capacity))
        backlog=sum(remaining[i] for i in ready)
        used=float(mode_time[t].sum());max_fraction=max(max_fraction,used)
        if backlog>1e-6:max_idle_with_backlog=max(max_idle_with_backlog,max(0.,1-used))
        max_overdue=max(max_overdue,sum(remaining[i] for i,j in enumerate(jobs) if j.deadline<=t+1))
    audit=dict(energy_optimum_normalized=first['energy'],energy_excess_normalized=second['energy']-first['energy'],
               max_idle_fraction_with_released_unfinished_work=max_idle_with_backlog,
               max_overdue_work=max_overdue,max_remaining_work=float(max(remaining)),
               max_pool_fraction=max_fraction,policy='lexicographic minimum-energy then earliest-work; EDF relabelled')
    if max_idle_with_backlog>1e-5 or max_overdue>1e-5 or max(remaining)>1e-5:
        raise AssertionError(audit)
    if second['energy']>first['energy']+2e-7:raise AssertionError(audit)
    second['allocations']=allocations
    second['slot_average_power']=(np.asarray(second['slot_average_power'])*scale).tolist()
    second['energy']*=scale
    second['energy_cost']=second['energy']
    second['baseline_audit']=audit
    return second
