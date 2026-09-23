"""Conditional grid evaluation of frozen fluid-task mechanism responses.

No offer selection, task optimization, grid expansion or online dispatch occurs
here. Linear-forecast follower endpoints are not bounds on nonlinear grid cost.
All money and power units must be consistent across caller inputs.
"""
import copy
import hashlib
import json
from dataclasses import asdict, is_dataclass
import numpy as np
from coupled_grid_compute import solve


def fingerprint(value):
    def encode(x):
        if is_dataclass(x): return encode(asdict(x))
        if isinstance(x, np.ndarray): return encode(x.tolist())
        if isinstance(x, np.generic): return encode(x.item())
        if isinstance(x,dict): return {k:encode(v) for k,v in x.items()}
        if isinstance(x,(list,tuple)): return [encode(v) for v in x]
        # Explicitly unlimited caps are permitted by the task model. Encode
        # infinities as tagged values instead of emitting nonstandard JSON.
        if isinstance(x,float) and np.isinf(x): return {'__nonfinite_float__':'positive_infinity' if x>0 else 'negative_infinity'}
        return x
    return hashlib.sha256(json.dumps(encode(value), sort_keys=True,
                                     allow_nan=False).encode()).hexdigest()


def audit_response(record, task, posted_prices):
    """Reconstruct every job and power slot without using the scheduler matrix."""
    T=task['horizon']; dt=task.get('dt',1.); idle=task['idle_power']
    jobs=task['jobs']; q=np.asarray(task['q'],float); power=np.asarray(task['power'],float)
    if isinstance(T,bool) or not isinstance(T,int) or T<=0 or not np.isfinite(dt) or dt<=0:
        raise ValueError('Invalid task clock')
    if not np.isfinite(idle) or idle<0 or q.ndim!=1 or len(q)==0 or power.shape!=q.shape or not np.isfinite(q).all() or not np.isfinite(power).all() or (q<=0).any() or (power<idle).any():
        raise ValueError('Invalid task power boundary')
    by_name={j.name:(i,j) for i,j in enumerate(jobs)}
    if not jobs or len(by_name)!=len(jobs): raise ValueError('Distinct nonempty jobs required')
    for j in jobs:
        if any(isinstance(v,(bool,np.bool_)) or not isinstance(v,(int,np.integer)) for v in [j.release,j.deadline]) or not 0<=j.release<j.deadline<=T or not np.isfinite(j.work) or j.work<0:
            raise ValueError('Invalid job')
    service=np.asarray(task.get('service_cost_per_work',np.zeros((len(jobs),T))),float)
    caps=np.asarray(task.get('power_caps',np.full(T,np.inf)),float)
    prices=np.asarray(posted_prices,float)
    if service.shape!=(len(jobs),T) or not np.isfinite(service).all() or (service<0).any() or caps.shape!=(T,) or np.isnan(caps).any() or (caps<idle).any() or prices.shape!=(T,) or not np.isfinite(prices).all():
        raise ValueError('Invalid task costs or limits')
    completed=np.zeros(len(jobs)); occupation=np.zeros(T); p=np.full(T,float(idle)); sv=0.
    for a in record['allocations']:
        if a['job'] not in by_name: raise ValueError('Unknown job in frozen response')
        i,j=by_name[a['job']]; t=a['slot']; m=a['mode']; f=a['pool_fraction']
        if isinstance(t,bool) or not isinstance(t,int) or isinstance(m,bool) or not isinstance(m,int) or not j.release<=t<j.deadline or not 0<=m<len(q) or not np.isfinite(f) or f<0:
            raise ValueError('Invalid task allocation')
        work=q[m]*f*dt
        if not np.isfinite(a['work']) or abs(work-a['work'])>2e-7: raise ValueError('Allocation work mismatch')
        completed[i]+=work; occupation[t]+=f; p[t]+=(power[m]-idle)*f; sv+=service[i,t]*work
    error=float(np.max(np.abs(completed-[j.work for j in jobs])))
    if error>2e-7 or occupation.max()>1+2e-7 or (p>caps+2e-7).any():
        raise ValueError('Frozen task feasibility certificate failed')
    observed=np.asarray(record['power_mw'],float)
    if observed.shape!=(T,) or not np.isfinite(observed).all() or not np.allclose(p,observed,atol=2e-7,rtol=0):
        raise ValueError('Frozen power does not match task allocations')
    for key,value in [('energy_mwh',p.sum()*dt),('service_cost',sv),('energy_bill',prices@p*dt)]:
        if not np.isfinite(record[key]) or not np.isclose(value,record[key],atol=2e-7,rtol=1e-10):
            raise ValueError('Frozen accounting mismatch: '+key)
    return dict(maximum_work_error=error,maximum_pool_fraction=float(occupation.max()),
                reconstructed_energy_mwh=float(p.sum()*dt),scope='Fluid tasks, caller-supplied power curve and service limits')


def _fixed_grid(grid,task,node):
    allowed={'nodes','scenario','generators','lines','storage','reservoirs','commitments','dt','emissions_limit_t','milp_time_limit_s'}
    if set(grid)-allowed: raise ValueError('Unsupported grid input; no overrides of fixed-load or shedding rules')
    nodes=grid['nodes']; scenario=grid['scenario']
    if node not in nodes or grid['dt']!=task.get('dt',1.) or scenario.probability!=1 or any(len(a)!=task['horizon'] for a in scenario.load_mw.values()):
        raise ValueError('Grid/task clock, node or scenario mismatch')
    for key,fields in [('generators',['max_new_mw']),('lines',['max_new_mw']),('storage',['max_new_power_mw','max_new_energy_mwh'])]:
        if any(getattr(a,f)!=0 for a in grid.get(key,[]) for f in fields):
            raise ValueError('Mechanism evaluation requires identical fixed installed capacities')
    args=copy.deepcopy(grid); args.pop('scenario'); args['scenarios']=[copy.deepcopy(scenario)]
    args.update(expected_unserved_limit_mwh=0.,pools=())
    return args


def evaluate_frozen_response(record,task,posted_prices,grid,compute_node):
    """Dispatch the complete grid with a mandatory, independently audited load."""
    certificate=audit_response(record,task,posted_prices)
    args=_fixed_grid(grid,task,compute_node)
    external={n:[0.]*task['horizon'] for n in grid['nodes']}
    external[compute_node]=list(record['power_mw'])
    result=solve(**args,external_fixed_load={grid['scenario'].name:external})
    terminal=None
    if result['feasible'] is True:
        terminal=any(v['remaining_minimum_time_steps']>0 for v in result['scenarios'][grid['scenario'].name]['terminal_unit_state'].values())
        if abs(result['cost_components']['investment'])>1e-8 or result['expected_unserved_mwh']>1e-7:
            raise RuntimeError('Fixed-capacity/no-shedding contract violated')
    return dict(task_certificate=certificate,grid=result,terminal_minimum_time_obligation=terminal)


def evaluate_plan_on_grid(plan,task,grid,compute_node):
    """Evaluate all forecast endpoints; retain the previously selected offer.

Grid dispatch has conditional full-horizon foresight and may change commitment
between responses. The method is not realized online operations or a worst-case
optimization over the follower polytope. No ranking is inferred from endpoints.
    """
    before=fingerprint(plan)
    if not plan.get('feasible') or plan['horizon']!=task['horizon'] or plan['dt']!=task.get('dt',1.):
        raise ValueError('Feasible plan and matching task clock required')
    _fixed_grid(grid,task,compute_node)
    candidates=plan['event_candidates']; chosen=plan['selected_contract_index']
    if not 0<=chosen<len(candidates) or not candidates[chosen]['feasible'] or candidates[chosen]['commitment_mw']!=plan['selected_commitment_mw']:
        raise ValueError('Invalid frozen selection')
    records=[('baseline',plan['baseline'],plan['tariff']),('price',plan['price'],plan['forecast_cost'])]
    for i,c in enumerate(candidates):
        if c['feasible']:
            for side in ['forecast_best','forecast_worst']:
                r=c[side]; event=plan['event_slots']
                if c['commitment_mw']==0 and fingerprint(r)!=fingerprint(plan['baseline']):
                    raise ValueError('Zero offer must preserve the frozen outside option')
                reduction=np.asarray(plan['baseline']['power_mw'])[event]-np.asarray(r['power_mw'])[event]
                if (reduction<c['commitment_mw']-2e-7).any(): raise ValueError('Frozen event commitment violated')
                if c['commitment_mw']>0:
                    if r['energy_bill']+r['service_cost']>c['follower_minimum_cost']+plan['follower_cost_tolerance']+2e-7:
                        raise ValueError('Response outside declared follower cost set')
                    budget=plan.get('recovery_energy_budget_mwh')
                    non_event=sorted(set(range(task['horizon']))-set(event))
                    recovery=(np.asarray(r['power_mw'])[non_event]-np.asarray(plan['baseline']['power_mw'])[non_event]).sum()*plan['dt']
                    if budget is not None and recovery>budget+2e-7: raise ValueError('Recovery limit violated')
                records.append((f'offer_{i}_{side}',c[side],plan['tariff']))
    results={}; base=plan['baseline']; cache={}
    for label,r,posted in records:
        payment=r['participation_transfer']
        floor=max(0.,r['energy_bill']+r['service_cost']-base['energy_bill']-base['service_cost'])
        if not np.isfinite(payment) or not np.isclose(payment,floor,atol=2e-7,rtol=1e-10):
            raise ValueError('Participation accounting mismatch')
        certificate=audit_response(r,task,posted)
        key=tuple(r['power_mw'])
        if key not in cache: cache[key]=evaluate_frozen_response(r,task,posted,grid,compute_node)
        results[label]=copy.deepcopy(cache[key]); results[label]['task_certificate']=certificate
        result=results[label]; result['accounting']=None
        baseline_grid=results['baseline']['grid']
        if result['grid']['feasible'] is True and baseline_grid['feasible'] is True:
            delta=baseline_grid['total_cost']-result['grid']['total_cost']
            bill=r['energy_bill']-base['energy_bill']; sv=r['service_cost']-base['service_cost']
            resource=delta-sv; retailer=delta+bill-payment; provider=payment-bill-sv
            if not np.isclose(resource,retailer+provider,atol=1e-7): raise RuntimeError('Transfer identity failed')
            result['accounting']=dict(horizon_resource_saving=resource,grid_cost_saving=delta,
                retailer_cash_saving=retailer,provider_welfare_change=provider,
                participation_transfer=payment,weak_participation=provider>=-2e-7,
                unresolved_terminal_obligations=bool(result['terminal_minimum_time_obligation'] or results['baseline']['terminal_minimum_time_obligation']))
    if fingerprint(plan)!=before: raise RuntimeError('Frozen plan mutated')
    return dict(plan_sha256=before,task_sha256=fingerprint(task),grid_sha256=fingerprint(grid),
        selected_commitment_mw=plan['selected_commitment_mw'],selected_contract_index=chosen,
        selected_endpoint_labels=[f'offer_{chosen}_forecast_best',f'offer_{chosen}_forecast_worst'],
        responses=results,unique_grid_solves=len(cache),
        scope='Fixed-capacity full-horizon conditional redispatch of frozen fluid responses; forecast endpoints are NOT grid-cost bounds; not provincial or online market evidence')
