"""Deterministic, preemptive, single-pool task scheduling LP.

Service units are full-speed pool-hours for ONE fixed workload configuration.
Time sharing and perfect foresight are optimistic assumptions. Idle power is an
explicit scenario input, not an observed Emerald power measurement. Each slot
power is an AVERAGE, not a within-slot firm instantaneous guarantee.
"""
from dataclasses import dataclass
from typing import Sequence
import numpy as np
from scipy.optimize import linprog
from scipy.sparse import coo_matrix, vstack, hstack, csr_matrix


@dataclass(frozen=True)
class Job:
    name: str
    release: int
    deadline: int  # exclusive slot boundary
    work: float  # full-speed pool-hours


def schedule(jobs: Sequence[Job], q, power, horizon: int, idle_power: float,
             dt: float = 1., prices=None, power_caps=None,
             event_slots=None, baseline_power=None, relax_windows=False,
             service_cost_per_work=None, energy_limit=None,
             energy_window_limits=(), reference_objective_ceiling=None):
    """Minimize energy cost, or maximize minimum per-slot event reduction.

No work dropping or spilling outside horizon. Infeasibility is returned, never
silently converted to load shedding. relax_windows is an explicit upper-bound
comparison in which all releases/deadlines become 0/horizon.
energy_window_limits contains (unique slot indices, maximum MWh) pairs.
reference_objective_ceiling constrains another explicitly specified linear
bill-plus-service objective while the current objective breaks its ties.
    """
    q, power = np.asarray(q, float), np.asarray(power, float)
    if horizon <= 0 or dt <= 0 or q.ndim != 1 or power.shape != q.shape:
        raise ValueError('Invalid time or mode dimensions')
    if not (np.isfinite(q).all() and np.isfinite(power).all() and np.isfinite(idle_power)):
        raise ValueError('Non-finite mode parameters')
    if len(q) == 0 or (q <= 0).any() or (power < idle_power).any() or idle_power < 0:
        raise ValueError('Modes require positive throughput and power >= nonnegative idle')
    if len({j.name for j in jobs}) != len(jobs):
        raise ValueError('Job names must be unique')
    for j in jobs:
        if not (0 <= j.release < j.deadline <= horizon and np.isfinite(j.work) and j.work >= 0):
            raise ValueError(f'Invalid job window/work: {j}')
    prices = np.ones(horizon) if prices is None else np.asarray(prices, float)
    caps = np.full(horizon, np.inf) if power_caps is None else np.asarray(power_caps, float)
    if prices.shape != (horizon,) or not np.isfinite(prices).all() or caps.shape != (horizon,) or np.isnan(caps).any():
        raise ValueError('Invalid prices or power caps')
    service_cost = np.zeros((len(jobs),horizon)) if service_cost_per_work is None else np.asarray(service_cost_per_work,float)
    if service_cost.shape != (len(jobs),horizon) or not np.isfinite(service_cost).all():
        raise ValueError('Service cost must be a finite job by time array, in currency per work unit')
    windows=[]
    for slots,limit in energy_window_limits:
        slots=list(slots)
        if (not slots or any(not isinstance(t,(int,np.integer)) or isinstance(t,(bool,np.bool_)) or not 0<=t<horizon for t in slots)
                or len(set(slots))!=len(slots) or not np.isfinite(limit) or limit<0):
            raise ValueError('Invalid energy-window slots or limit')
        windows.append((slots,float(limit)))
    reference=None
    if reference_objective_ceiling is not None:
        if set(reference_objective_ceiling)!={'prices','service_cost_per_work','maximum'}:
            raise ValueError('Reference objective requires prices, service costs and maximum')
        rp=np.asarray(reference_objective_ceiling['prices'],float)
        rs=np.asarray(reference_objective_ceiling['service_cost_per_work'],float)
        maximum=reference_objective_ceiling['maximum']
        if rp.shape!=(horizon,) or rs.shape!=(len(jobs),horizon) or not np.isfinite(rp).all() or not np.isfinite(rs).all() or not np.isfinite(maximum):
            raise ValueError('Invalid reference objective')
        reference=(rp,rs,float(maximum))
    event = [] if event_slots is None else sorted(set(event_slots))
    if event and (min(event) < 0 or max(event) >= horizon):
        raise ValueError('Event outside horizon')
    base = None if baseline_power is None else np.asarray(baseline_power, float)
    if event and (base is None or base.shape != (horizon,) or not np.isfinite(base).all()):
        raise ValueError('An explicit fixed baseline is required for event optimization')
    # y[j,t,m] is fraction of the pool-slot assigned to job j in mode m.
    variables = [(i,t,m) for i,j in enumerate(jobs)
                 for t in range(0 if relax_windows else j.release,
                                horizon if relax_windows else j.deadline)
                 for m in range(len(q))]
    n = len(variables)
    if n == 0:
        raise ValueError('At least one job required')
    cols = np.arange(n)
    ji = np.array([x[0] for x in variables]); ti = np.array([x[1] for x in variables]); mi = np.array([x[2] for x in variables])
    ae = coo_matrix((q[mi]*dt, (ji, cols)), shape=(len(jobs), n)).tocsr()
    resources = coo_matrix((np.ones(n), (ti, cols)), shape=(horizon,n)).tocsr()
    pm = coo_matrix((power[mi]-idle_power, (ti, cols)), shape=(horizon,n)).tocsr()
    finite = np.flatnonzero(np.isfinite(caps))
    au = vstack([resources, pm[finite]], format='csr')
    bu = np.r_[np.ones(horizon), caps[finite]-idle_power]
    if energy_limit is not None:
        if not np.isfinite(energy_limit):raise ValueError('Nonfinite energy limit')
        energy_row=csr_matrix((power[mi]-idle_power)*dt).reshape((1,n))
        au=vstack([au,energy_row],format='csr')
        bu=np.r_[bu,float(energy_limit)-horizon*idle_power*dt]
    for slots,limit in windows:
        row=csr_matrix(np.asarray(pm[slots].sum(axis=0))*dt)
        au=vstack([au,row],format='csr')
        bu=np.r_[bu,limit-len(slots)*idle_power*dt]
    if reference is not None:
        rp,rs,maximum=reference
        row=csr_matrix(rp[ti]*(power[mi]-idle_power)*dt+rs[ji,ti]*q[mi]*dt).reshape((1,n))
        au=vstack([au,row],format='csr')
        bu=np.r_[bu,maximum-idle_power*dt*rp.sum()]
    c = prices[ti]*(power[mi]-idle_power)*dt + service_cost[ji,ti]*q[mi]*dt
    bounds = [(0,1)]*n
    if event:
        # pm*y + k <= baseline-idle in EVERY event slot.
        ae = hstack([ae, csr_matrix((len(jobs),1))], format='csr')
        au = hstack([au, csr_matrix((au.shape[0],1))], format='csr')
        er = hstack([pm[event], csr_matrix(np.ones((len(event),1)))], format='csr')
        au = vstack([au,er], format='csr');bu = np.r_[bu,base[event]-idle_power]
        c = np.r_[np.zeros(n),-1.]
        # k may be negative: return forced event rebound instead of false feasibility.
        bounds += [(None,None)]
    fit = linprog(c, A_ub=au, b_ub=bu, A_eq=ae,
                  b_eq=[j.work for j in jobs], bounds=bounds, method='highs')
    if not fit.success:
        return {'feasible':False,'solver_status':int(fit.status),'message':fit.message,
                'relaxed_windows':relax_windows}
    y = fit.x[:n]
    slotpower = idle_power + pm@y
    slotwork = np.zeros(horizon);np.add.at(slotwork,ti,q[mi]*dt*y)
    completed = np.zeros(len(jobs));np.add.at(completed,ji,q[mi]*dt*y)
    allocations = [{'job':jobs[i].name,'slot':t,'mode':m,'pool_fraction':float(v),
                    'work':float(q[m]*dt*v)} for (i,t,m),v in zip(variables,y) if v > 1e-10]
    capacity_violation = float(np.maximum(resources@y-1,0).max())
    work_error = float(np.max(np.abs(completed-np.array([j.work for j in jobs]))))
    assert work_error < 1e-7 and capacity_violation < 1e-7
    assert not finite.size or np.max(slotpower[finite]-caps[finite]) < 1e-7
    assert all(slotpower[slots].sum()*dt<=limit+1e-7 for slots,limit in windows)
    if reference is not None:
        rp,rs,maximum=reference
        assert rp@slotpower*dt+np.sum(rs[ji,ti]*q[mi]*dt*y)<=maximum+1e-7
    if not relax_windows:
        lookup = {j.name:j for j in jobs}
        assert all(lookup[a['job']].release <= a['slot'] < lookup[a['job']].deadline for a in allocations)
    cap_shadow = np.zeros(horizon)
    if not event:
        cap_shadow[finite] = fit.ineqlin.marginals[horizon:horizon+len(finite)]
    service_total = float(np.sum(service_cost[ji,ti]*q[mi]*dt*y))
    return {'feasible':True,'relaxed_windows':relax_windows,
            'slot_average_power':slotpower.tolist(),'slot_completed_work':slotwork.tolist(),
            'completed_work_by_job':dict(zip([j.name for j in jobs],completed.tolist())),
            'energy':float(slotpower.sum()*dt),'energy_cost':float(prices@slotpower*dt),
            'service_cost':service_total,
            'objective_cost':float(prices@slotpower*dt)+service_total,
            'power_cap_cost_marginals':cap_shadow.tolist() if not event else None,
            'minimum_event_slot_reduction':float(fit.x[-1]) if event else None,
            'maximum_work_error':work_error,'maximum_capacity_violation':capacity_violation,
            'allocations':allocations}


def baseline_asap(jobs, max_q, max_power, horizon, idle_power, dt=1.):
    """Deterministic work-conserving earliest-deadline service at max mode.

Fractional slots are averaged with idle power. It is a documented comparator,
not an estimated operator policy or an incentive-compatible settlement baseline.
    """
    remaining = np.array([j.work for j in jobs],float)
    out = np.full(horizon,float(idle_power))
    for t in range(horizon):
        if any(remaining[i]>1e-8 and j.deadline<=t for i,j in enumerate(jobs)):
            raise ValueError('ASAP baseline misses deadline')
        capacity = max_q*dt;used=0.
        for i in sorted(range(len(jobs)), key=lambda i:(jobs[i].deadline,i)):
            if jobs[i].release<=t<jobs[i].deadline:
                w=min(capacity,remaining[i]);remaining[i]-=w;capacity-=w;used+=w
        out[t] += used/(max_q*dt)*(max_power-idle_power)
    if remaining.max()>1e-8:
        raise ValueError('ASAP baseline cannot complete all tasks')
    return out
