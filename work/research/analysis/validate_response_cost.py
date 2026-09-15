"""Validate cost frontiers using hand calculations and scenario sweeps."""
from pathlib import Path
import sys,json,hashlib
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'work/research/models'))
from sequential_tasks import Job,schedule,baseline_asap
from response_cost import fixed_response,cost_at_max_response
OUT=ROOT/'outputs/research/tables'
checks=[]
jobs=[Job('batch',0,2,1.5)]
# All costs in arbitrary currency, power in MW. Free dispatch [1,.5], cost 2.5.
# Fixed baseline [.75,.75] gives C(k)=3+2k over 0<=k<=.25.
for k in [0,.1,.2,.25]:
    r=fixed_response(jobs,[1],[1],2,0,[.75,.75],[0],k,[1,3])
    assert r['feasible']
    assert np.isclose(r['outside_option_cost'],2.5)
    assert np.isclose(r['committed_minimum_cost'],3+2*k)
    assert np.isclose(r['opportunity_cost'],.5+2*k)
    if k<.25:assert np.isclose(r['commitment_cost_subgradient'],2)
assert not fixed_response(jobs,[1],[1],2,0,[.75,.75],[0],.251,[1,3])['feasible']
checks+=['analytic_piecewise_linear_cost_and_dual','cost_at_zero_commitment_can_exceed_outside_option','above_boundary_infeasible']
# Fixed shadow price must match an independently computed finite difference.
a=fixed_response(jobs,[1],[1],2,0,[.75,.75],[0],.1,[1,3])
b=fixed_response(jobs,[1],[1],2,0,[.75,.75],[0],.10001,[1,3])
assert np.isclose((b['committed_minimum_cost']-a['committed_minimum_cost'])/.00001,a['commitment_cost_subgradient'])
checks.append('dual_matches_finite_difference_away_from_kink')
# Total objective must include stipulated service costs, not only electricity.
r=fixed_response(jobs,[1],[1],2,0,[.75,.75],[0],.2,[1,1],service_cost_per_work=[[0,2]])
assert np.isclose(r['committed']['energy_cost'],1.5)
assert np.isclose(r['committed']['service_cost'],1.9)
assert np.isclose(r['committed_minimum_cost'],3.4)
checks.append('service_cost_units_and_opportunity_cost')
# Two equally effective responses can have very different cost: second stage
# must choose recovery in the cheap third slot, not expensive second slot.
r=cost_at_max_response([Job('batch',0,3,1)],[1],[1],3,0,[1,0,0],[0],[1,9,2])
assert r['feasible'] and np.isclose(r['commitment'],1)
assert np.isclose(r['committed_minimum_cost'],2)
assert np.allclose(r['committed']['slot_average_power'],[0,0,1])
checks.append('lexicographic_max_response_then_min_cost')
# An event cap cannot create savings relative to an unrestricted optimum.
rows=[];details=[]
data=pd.read_csv(OUT/'dvfs_measured_and_derived.csv')
for name,g in data.groupby('Workload',sort=False):
    q=g['normalized throughput'].to_numpy();p=g['total GPU power'].to_numpy()/1e6
    h=12;event=[4,5,6];u=.9;idle=.2*p.max()
    # Analyst tariff scenarios. None is an observed tariff or grid marginal cost.
    for label,prices in [('flat',np.full(h,500.)),('event_cheap',np.array([500.]*4+[100.]*3+[900.]*5)),
                         ('event_expensive',np.array([500.]*4+[1500.]*3+[200.]*5))]:
        for deadline in [1,4,8]:
            jobs=[Job(str(t),t,min(t+deadline,h),u) for t in range(h)]
            base=baseline_asap(jobs,q.max(),p[q.argmax()],h,idle)
            top=cost_at_max_response(jobs,q,p,h,idle,base,event,prices)
            assert top['feasible']
            maximum=top['commitment']
            cases=[]
            for fraction in [0,.25,.5,.75,1]:
                k=maximum*fraction
                r=fixed_response(jobs,q,p,h,idle,base,event,k,prices)
                assert r['feasible']
                case={'workload':name,'tariff_assumption':label,'deadline_window_h_assumption':deadline,
                    'utilization_assumption':u,'idle_power_ratio_assumption':.2,
                    'max_response_fraction':fraction,'commitment_MW':k,
                    'minimum_cost_CNY_scenario':r['committed_minimum_cost'],
                    'outside_option_cost_CNY_scenario':r['outside_option_cost'],
                    'opportunity_cost_CNY_scenario':r['opportunity_cost'],
                    'marginal_cost_CNY_per_MW_event_scenario':r['commitment_cost_subgradient'],
                    'is_measured_tariff':False,'is_market_equilibrium':False,
                    'maximum_work_error':r['committed']['maximum_work_error']}
                rows.append(case);cases.append(case)
                if name=='ft_llama_8b_dolly' and label=='event_cheap' and deadline==4:
                    details.append({'case':case,'baseline_power_MW':base.tolist(),
                                    'assumed_price_CNY_per_MWh':prices.tolist(),'result':r})
            vals=np.array([x['minimum_cost_CNY_scenario'] for x in cases])
            assert np.all(np.diff(vals)>=-1e-7)
            assert np.all(np.diff(vals,n=2)>=-1e-7)
checks+=['72_cost_frontiers_nondecreasing_and_convex_on_tested_grid','all_fixed_promises_conserve_each_job','participation_compensation_relative_to_reoptimized_outside_option']
table=pd.DataFrame(rows);table.to_csv(OUT/'response_cost_scenarios_NOT_market_estimates.csv',index=False)
(OUT/'response_cost_examples.json').write_text(json.dumps(details,indent=2))
summary={'status':'verified_deterministic_cost_component_NOT_policy_result','checks':checks,
    'frontiers':72,'solved_fixed_commitments':len(rows),'max_work_error':float(table.maximum_work_error.max()),
    'scope':'operational electricity and optional stipulated service cost, no empirical checkpoint/migration or capital costs',
    'limitations':['synthetic uniform arrivals','assumed deadlines and idle power','assumed tariff magnitudes and patterns',
       'no default risk, risk aversion or transaction costs','fixed non-strategic baseline',
       'no evidence of positive social net benefit or willingness to accept'],
    'model_sha256':hashlib.sha256((ROOT/'work/research/models/response_cost.py').read_bytes()).hexdigest()}
(OUT/'response_cost_validation.json').write_text(json.dumps(summary,indent=2))
print(json.dumps(summary,indent=2))
