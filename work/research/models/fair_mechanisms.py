"""Same-information price and event benchmarks for the fluid task model.

Forecast costs are exogenous linear marginal resource costs, not endogenous
prices from a realized grid optimum. No investment, network equilibrium,
private information or actual forecast-quality claim is implemented here.
Event procurement is optimal only over the supplied finite offer set. Follower
cost ties are bounded, not silently settled in the operator's favour.
"""
import copy
import numpy as np
from sequential_tasks import schedule


def plan_mechanisms(jobs,q,power,horizon,idle_power,tariff,forecast_cost,
                    event_slots,offered_commitments,dt=1.,power_caps=None,
                    service_cost_per_work=None,recovery_energy_budget_mwh=None,
                    follower_cost_tolerance=1e-7):
    """Make a plan without access to realized costs.

Zero commitment is a true opt-out (the immutable outside schedule). Positive
commitments require the same minimum reduction in every event interval.
Optional recovery budget limits total non-event energy above the outside
schedule, not work or service completion. A participation payment is a transfer,
not a new physical resource cost. Rates/powers use the caller's consistent units.
    """
    jobs=list(jobs)
    tariff=np.asarray(tariff,float);forecast=np.asarray(forecast_cost,float)
    if tariff.shape!=(horizon,) or forecast.shape!=(horizon,) or not np.isfinite(tariff).all() or not np.isfinite(forecast).all():
        raise ValueError('Finite tariff and decision-time forecast required')
    event=list(event_slots)
    if not event or len(set(event))!=len(event) or any(not isinstance(t,(int,np.integer)) or isinstance(t,(bool,np.bool_)) or not 0<=t<horizon for t in event):
        raise ValueError('Distinct integer event slots required')
    event=sorted(event);non_event=sorted(set(range(horizon))-set(event))
    offers=list(offered_commitments)
    if not offers or any(not np.isfinite(k) or k<0 for k in offers) or 0 not in offers or len(set(offers))!=len(offers):
        raise ValueError('Distinct nonnegative offers including zero opt-out required')
    offers=sorted(float(k) for k in offers)
    if not np.isfinite(follower_cost_tolerance) or follower_cost_tolerance<0:
        raise ValueError('Invalid follower objective tolerance')
    if recovery_energy_budget_mwh is not None and (not np.isfinite(recovery_energy_budget_mwh) or recovery_energy_budget_mwh<0):
        raise ValueError('Recovery budget must be finite and nonnegative')
    service=np.zeros((len(jobs),horizon)) if service_cost_per_work is None else np.asarray(service_cost_per_work,float)
    if service.shape!=(len(jobs),horizon) or not np.isfinite(service).all() or (service<0).any():
        raise ValueError('Finite nonnegative service costs required')
    caps=np.full(horizon,np.inf) if power_caps is None else np.asarray(power_caps,float)
    common=dict(jobs=jobs,q=q,power=power,horizon=horizon,idle_power=idle_power,dt=dt)
    outside=schedule(**common,prices=tariff,power_caps=caps,service_cost_per_work=service)
    if not outside['feasible']:
        return {'feasible':False,'reason':'outside_option_infeasible','solver':outside}
    baseline=np.asarray(outside['slot_average_power'])
    outside_cost=float(outside['objective_cost'])
    ji={j.name:i for i,j in enumerate(jobs)}

    def record(solution,posted_prices,participation=True):
        p=np.asarray(solution['slot_average_power'])
        service_amount=float(sum(service[ji[a['job']],a['slot']]*a['work'] for a in solution['allocations']))
        bill=float(posted_prices@p*dt)
        payment=max(0.,bill+service_amount-outside_cost) if participation else 0.
        return dict(power_mw=p.tolist(),allocations=copy.deepcopy(solution['allocations']),
                    energy_mwh=float(p.sum()*dt),energy_bill=bill,service_cost=service_amount,
                    participation_transfer=float(payment),
                    forecast_resource_cost=float(forecast@p*dt+service_amount),
                    actual_event_reduction_mw=(baseline[event]-p[event]).tolist(),
                    non_event_energy_change_mwh=float((p[non_event]-baseline[non_event]).sum()*dt))

    reference=record(outside,tariff,False)
    price_fit=schedule(**common,prices=forecast,power_caps=caps,service_cost_per_work=service)
    if not price_fit['feasible']:raise RuntimeError('Shared-feasible price problem unexpectedly infeasible')
    price=record(price_fit,forecast)
    candidates=[dict(commitment_mw=0.,feasible=True,mode='opt_out',
                     follower_minimum_cost=outside_cost,
                     forecast_best=copy.deepcopy(reference),forecast_worst=copy.deepcopy(reference),
                     worst_case_forecast_resource_saving=0.)]
    for k in offers[1:]:
        limited=caps.copy();limited[event]=np.minimum(limited[event],baseline[event]-k)
        windows=[]
        if recovery_energy_budget_mwh is not None and non_event:
            windows=[(non_event,float(baseline[non_event].sum()*dt+recovery_energy_budget_mwh))]
        kwargs=dict(common,power_caps=limited,energy_window_limits=windows)
        follower=schedule(**kwargs,prices=tariff,service_cost_per_work=service)
        if not follower['feasible']:
            candidates.append(dict(commitment_mw=k,feasible=False,reason='commitment_or_recovery_infeasible'))
            continue
        ceiling=dict(prices=tariff,service_cost_per_work=service,
                     maximum=follower['objective_cost']+follower_cost_tolerance)
        best=schedule(**kwargs,prices=forecast,service_cost_per_work=service,reference_objective_ceiling=ceiling)
        worst=schedule(**kwargs,prices=-forecast,service_cost_per_work=-service,reference_objective_ceiling=ceiling)
        if not best['feasible'] or not worst['feasible']:raise RuntimeError('Follower tie-bound solve failed')
        lo=record(best,tariff);hi=record(worst,tariff)
        if lo['forecast_resource_cost']>hi['forecast_resource_cost']+1e-6:raise RuntimeError('Reversed tie bounds')
        candidates.append(dict(commitment_mw=k,feasible=True,mode='event_contract',
                               follower_minimum_cost=float(follower['objective_cost']),
                               forecast_best=lo,forecast_worst=hi,
                               worst_case_forecast_resource_saving=reference['forecast_resource_cost']-hi['forecast_resource_cost']))
    # Zero is admissible; equal-value offers choose the smaller commitment.
    selection_tolerance=1e-7  # absolute resource-cost units, reported in plan
    selected=0
    for i,c in enumerate(candidates):
        if c['feasible'] and c['worst_case_forecast_resource_saving']>candidates[selected]['worst_case_forecast_resource_saving']+selection_tolerance:
            selected=i
    return dict(feasible=True,horizon=horizon,dt=float(dt),tariff=tariff.tolist(),forecast_cost=forecast.tolist(),
                event_slots=event,baseline=reference,price=price,event_candidates=candidates,
                selected_contract_index=selected,selected_commitment_mw=candidates[selected]['commitment_mw'],
                follower_cost_tolerance=float(follower_cost_tolerance),
                selection_value_tolerance=selection_tolerance,
                recovery_energy_budget_mwh=recovery_energy_budget_mwh,
                scope='FINITE_OFFER_SET_FLUID_MODEL_MATHEMATICAL_BENCHMARK',
                assumptions=['Exogenous linear forecast resource costs, no realized cost in planning',
                             'Complete known job set, preemptive time sharing, no task dropping',
                             'All physical caps and service requirements common across mechanisms',
                             'Contract tie bounds within explicit bill tolerance; pessimistic forecast endpoint retained',
                             'Participation transfer is an accounting floor for the prescribed response, not an incentive-compatible payment rule',
                             'Recovery cap is a contract term, not a change in the shared service requirement',
                             'No provincial, reliability, market-equilibrium or deployability result'])


def evaluate_frozen_plan(plan,realized_cost):
    """Evaluate frozen trajectories; never reselect an offer or reschedule jobs."""
    if not plan.get('feasible'):raise ValueError('Cannot evaluate infeasible plan')
    realized=np.asarray(realized_cost,float)
    if realized.shape!=(plan['horizon'],) or not np.isfinite(realized).all():raise ValueError('Invalid realized resource costs')
    dt=plan['dt'];base=plan['baseline'];base_supply=float(realized@np.asarray(base['power_mw'])*dt)
    def account(r):
        supply=float(realized@np.asarray(r['power_mw'])*dt)
        bill_change=r['energy_bill']-base['energy_bill'];service_change=r['service_cost']-base['service_cost'];payment=r['participation_transfer']
        resource=base_supply-supply-service_change
        retailer=base_supply-supply+bill_change-payment
        provider=payment-bill_change-service_change
        if not np.isclose(resource,retailer+provider,atol=1e-7,rtol=1e-10):raise RuntimeError('Transfer accounting identity failed')
        return dict(realized_supply_cost=supply,resource_saving=resource,retailer_cash_saving=retailer,
                    provider_welfare_change=provider,participation_transfer=payment,
                    energy_bill_change=bill_change,service_cost_change=service_change,
                    weak_participation=provider>=-1e-7)
    selected=plan['event_candidates'][plan['selected_contract_index']]
    return dict(realized_cost=realized.tolist(),selected_commitment_mw=plan['selected_commitment_mw'],
                baseline=account(base),price=account(plan['price']),
                selected_contract_forecast_best_endpoint=account(selected['forecast_best']),
                selected_contract_forecast_worst_endpoint=account(selected['forecast_worst']),
                alternatives=[dict(commitment_mw=c['commitment_mw'],forecast_best_endpoint=account(c['forecast_best']),forecast_worst_endpoint=account(c['forecast_worst'])) for c in plan['event_candidates'] if c['feasible']],
                scope='Ex-post evaluation of frozen forecast endpoints, not realized-optimal tie bounds or oracle reoptimization')
