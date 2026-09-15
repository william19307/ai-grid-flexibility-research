"""Fixed-commitment cost and deterministic participation thresholds.

Caller selects consistent units: MW + hours + currency/MWh => currency.
This is an operational partial-equilibrium component, not a grid-market model.
The outside option is reoptimized, not the cost of an arbitrary fixed baseline.
"""
import numpy as np
from sequential_tasks import schedule


def fixed_response(jobs,q,power,horizon,idle_power,baseline,event_slots,
                   commitment,prices,dt=1.,power_caps=None,service_cost_per_work=None):
    event=sorted(set(event_slots));base=np.asarray(baseline,float)
    if not event or min(event)<0 or max(event)>=horizon:
        raise ValueError('A nonempty event within the horizon is required')
    if base.shape!=(horizon,) or not np.isfinite(base).all() or not np.isfinite(commitment):
        raise ValueError('Explicit finite baseline and commitment required')
    physical_caps=np.full(horizon,np.inf) if power_caps is None else np.asarray(power_caps,float)
    caps=physical_caps.copy()
    caps[event]=np.minimum(caps[event],base[event]-commitment)
    common=dict(jobs=jobs,q=q,power=power,horizon=horizon,idle_power=idle_power,
                dt=dt,prices=prices,service_cost_per_work=service_cost_per_work)
    outside=schedule(**common,power_caps=physical_caps)
    if not outside['feasible']:
        return {'feasible':False,'reason':'outside_option_infeasible','outside_option':outside}
    constrained=schedule(**common,power_caps=caps)
    if not constrained['feasible']:
        return {'feasible':False,'reason':'commitment_infeasible','commitment':float(commitment),
                'outside_option_cost':outside['objective_cost'],'solver':constrained}
    opportunity=constrained['objective_cost']-outside['objective_cost']
    assert opportunity>=-1e-7
    delivered=base[event]-np.asarray(constrained['slot_average_power'])[event]
    assert delivered.min()>=commitment-1e-7
    # An active stricter physical cap makes an event RHS locally independent of k.
    active=[t for t in event if base[t]-commitment<physical_caps[t]]
    marginal=-sum(constrained['power_cap_cost_marginals'][t] for t in active)
    return {'feasible':True,'commitment':float(commitment),
            'outside_option_cost':outside['objective_cost'],
            'committed_minimum_cost':constrained['objective_cost'],
            'opportunity_cost':float(opportunity),
            'minimum_total_compensation_for_weak_participation':float(max(0,opportunity)),
            'commitment_cost_subgradient':float(marginal),
            'minimum_delivered_slot_reduction':float(delivered.min()),
            'outside_option':outside,'committed':constrained}


def cost_at_max_response(jobs,q,power,horizon,idle_power,baseline,event_slots,
                         prices,dt=1.,power_caps=None,service_cost_per_work=None):
    """Two-stage solve: maximize response, then minimize cost at that response.

Both stages use exactly the same tasks, capacity and service cost parameters.
Service costs do not alter first-stage max k, but select the second-stage solution.
    """
    maximum=schedule(jobs,q,power,horizon,idle_power,dt=dt,prices=prices,
        power_caps=power_caps,event_slots=event_slots,baseline_power=baseline,
        service_cost_per_work=service_cost_per_work)
    if not maximum['feasible']:
        return {'feasible':False,'reason':'maximum_response_problem_infeasible','solver':maximum}
    result=fixed_response(jobs,q,power,horizon,idle_power,baseline,event_slots,
        maximum['minimum_event_slot_reduction'],prices,dt=dt,power_caps=power_caps,
        service_cost_per_work=service_cost_per_work)
    if result['feasible']:
        assert result['committed_minimum_cost']<=maximum['objective_cost']+1e-7
        result['stage_one_arbitrary_solution_cost']=maximum['objective_cost']
    return result
