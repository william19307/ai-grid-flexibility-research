"""Independent analytic/matching checks and explicitly assumed task scenarios."""
from pathlib import Path
import sys, json, itertools, hashlib
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'work/research/models'))
from sequential_tasks import Job, schedule, baseline_asap
OUT=ROOT/'outputs/research/tables'

checks=[]
# Analytic linear-power two-slot case: 1.5 work => at least .5 in event slot.
j=[Job('all',0,2,1.5)]
r=schedule(j,[1],[1],2,0,event_slots=[0],baseline_power=[.75,.75])
assert np.isclose(r['minimum_event_slot_reduction'],.25)
checks.append('analytic_two_slot_recovery_bound')
# Same total work and baseline; individual one-slot deadlines eliminate shifting.
j=[Job('early',0,1,.75),Job('late',1,2,.75)]
a=schedule(j,[1],[1],2,0,event_slots=[0],baseline_power=[.75,.75])
b=schedule(j,[1],[1],2,0,event_slots=[0],baseline_power=[.75,.75],relax_windows=True)
assert abs(a['minimum_event_slot_reduction'])<1e-9
assert np.isclose(b['minimum_event_slot_reduction'],.25)
checks.append('same_total_work_different_deadline_feasibility')
# Late jobs cannot use early-only electrical availability.
j=[Job('late',2,4,2)]
a=schedule(j,[1],[1],4,0,power_caps=[1,1,0,0])
b=schedule(j,[1],[1],4,0,power_caps=[1,1,0,0],relax_windows=True)
assert not a['feasible'] and b['feasible']
checks.append('reject_anticipatory_service_under_power_caps')
# One must not optimize average event reduction and report its minimum.
j=[Job('early',0,1,1),Job('flex',1,3,1)]
r=schedule(j,[1],[1],3,0,event_slots=[0,1],baseline_power=[1,1,0])
assert abs(r['minimum_event_slot_reduction'])<1e-9
checks.append('event_reduction_constrained_in_every_slot')
# Incomplete service is an infeasible case, not a positive savings result.
assert not schedule([Job('overload',0,1,1.01)],[1],[1],1,0)['feasible']
checks.append('no_dropped_or_terminal_spilled_work')
# Constant idle consumption and dt units.
r=schedule([Job('half_hour',0,2,.5)],[1],[3],2,1,dt=.5)
assert np.isclose(r['energy'],2.)
checks.append('idle_accounting_and_timestep_units')
# Independent oracle: unit-size jobs, unit slots. Enumeration checks all possible
# integral assignments, not the LP equations. Bipartite matching integrality
# ensures agreement with fractional feasibility in this restricted case.
rng=np.random.default_rng(112358);oracle_cases=[]
for k in range(120):
    h=4;n=int(rng.integers(1,6));caps=rng.integers(0,2,size=h)
    jobs=[]
    for i in range(n):
        release=int(rng.integers(h));deadline=int(rng.integers(release+1,h+1))
        jobs.append(Job(str(i),release,deadline,1))
    choices=[range(j.release,j.deadline) for j in jobs]
    oracle=any(np.all(np.bincount(slots,minlength=h)<=caps) for slots in itertools.product(*choices))
    result=schedule(jobs,[1],[1],h,0,power_caps=caps)
    assert result['feasible']==oracle,(jobs,caps,oracle,result)
    oracle_cases.append({'case':k,'jobs':[j.__dict__ for j in jobs],'power_caps':caps.tolist(),
                         'enumerated_feasible':bool(oracle),'solver_feasible':result['feasible']})
checks.append('120_independent_exhaustive_assignment_oracles')

data=pd.read_csv(OUT/'dvfs_measured_and_derived.csv');rows=[];examples=[]
for workload,g in data.groupby('Workload',sort=False):
    q=g['normalized throughput'].to_numpy();p=g['total GPU power'].to_numpy()
    for utilization in [.6,.75,.9,.95]:
        for delay in [1,2,4,8]:
            for idle_ratio in [0.,.2]:
                horizon=12;event=[4,5,6];idle=idle_ratio*p.max()
                # Uniform arrivals are assumed diagnostic inputs, not trace data.
                jobs=[Job(f'cohort_{t:02d}',t,min(t+delay,horizon),utilization) for t in range(horizon)]
                base=baseline_asap(jobs,q.max(),p[q.argmax()],horizon,idle)
                exact=schedule(jobs,q,p,horizon,idle,event_slots=event,baseline_power=base)
                relaxed=schedule(jobs,q,p,horizon,idle,event_slots=event,baseline_power=base,relax_windows=True)
                assert exact['feasible'] and relaxed['feasible']
                assert relaxed['minimum_event_slot_reduction']>=exact['minimum_event_slot_reduction']-1e-7
                case={'workload':workload,'utilization_assumption':utilization,'deadline_window_slots_assumption':delay,
                      'idle_power_fraction_assumption':idle_ratio,'horizon_hours':horizon,'event_start_hour':4,'event_hours':3,
                      'baseline_event_power_W':float(base[event].mean()),
                      'sequential_min_slot_reduction_W':exact['minimum_event_slot_reduction'],
                      'relaxed_min_slot_reduction_W':relaxed['minimum_event_slot_reduction'],
                      'relaxation_gap_W':relaxed['minimum_event_slot_reduction']-exact['minimum_event_slot_reduction'],
                      'sequential_energy_Wh_at_selected_max_response_solution':exact['energy'],
                      'maximum_work_error':exact['maximum_work_error'],
                      'is_empirical_workload_trace':False,'is_grid_capacity_result':False}
                rows.append(case)
                if workload=='ft_llama_8b_dolly' and utilization==.9 and idle_ratio==.2:
                    examples.append({'case':case,'jobs':[j.__dict__ for j in jobs],
                                     'baseline_power':base.tolist(),'sequential':exact,'relaxed':relaxed})
table=pd.DataFrame(rows)
table.to_csv(OUT/'sequential_task_benchmark_ASSUMED_arrivals.csv',index=False)
(OUT/'sequential_task_examples.json').write_text(json.dumps(examples,indent=2))
(OUT/'sequential_task_oracle_cases.json').write_text(json.dumps(oracle_cases,indent=2))
summary={'status':'verified_deterministic_component_NOT_grid_research', 'checks':checks,
         'enumerated_oracle_cases':len(oracle_cases),'measured_mode_scenario_cases':len(rows),
         'maximum_work_error':float(table.maximum_work_error.max()),
         'positive_relaxation_gap_cases':int((table.relaxation_gap_W>1e-7).sum()),
         'assumptions':['uniform_synthetic_arrivals','analyst_deadline_windows',
             'idle_power_zero_or_20pct_scenario_not_measured','perfect_foresight',
             'fractional_preemptive_time_sharing','one_homogeneous_pool',
             'no_switching_or_checkpoint_cost','hourly_average_response_not_instantaneous_firm',
             'ASAP_EDF_baseline_not_a_settlement_baseline','no_grid_or_network_model',
             'max_response_objective_energy_is_not_lexicographically_minimized'],
         'model_sha256':hashlib.sha256((ROOT/'work/research/models/sequential_tasks.py').read_bytes()).hexdigest()}
(OUT/'sequential_task_validation.json').write_text(json.dumps(summary,indent=2))
print(json.dumps(summary,indent=2))
