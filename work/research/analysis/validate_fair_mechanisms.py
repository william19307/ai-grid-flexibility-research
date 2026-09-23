"""Analytic and exhaustive independent references, not empirical market results."""
from pathlib import Path
import sys,json,hashlib,itertools,copy
import numpy as np
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'work/research/models'))
from sequential_tasks import Job,schedule
from fair_mechanisms import plan_mechanisms,evaluate_frozen_plan
OUT=ROOT/'outputs/research/revision/mechanism_fairness'
checks=[];examples={};cases=[];max_physical_error=0.;max_cost_error=0.
def same(a,b):
 assert np.allclose(a,b,atol=2e-7,rtol=1e-9),(a,b)
def digest(x):return hashlib.sha256(json.dumps(x,sort_keys=True,allow_nan=False).encode()).hexdigest()
def validate(name,args):
 global max_physical_error
 p=plan_mechanisms(**args)
 if not p['feasible']:return p
 jobs=args['jobs'];T=args['horizon'];dt=args.get('dt',1.);idle=args['idle_power'];q=args['q'];power=args['power']
 svc=np.asarray(args.get('service_cost_per_work',np.zeros((len(jobs),T))))
 tariff=np.asarray(args['tariff']);forecast=np.asarray(args['forecast_cost']);caps=np.asarray(args.get('power_caps',[np.inf]*T))
 jobmap={j.name:j for j in jobs};ji={j.name:i for i,j in enumerate(jobs)}
 records=[('baseline',p['baseline'],tariff),('price',p['price'],forecast)]
 for c in p['event_candidates']:
  if c['feasible']:
   for side in ['forecast_best','forecast_worst']:
    r=c[side];records.append((f'event_{c["commitment_mw"]}_{side}',r,tariff))
    assert min(r['actual_event_reduction_mw'])>=c['commitment_mw']-2e-7
    if c['commitment_mw']>0:
     assert r['energy_bill']+r['service_cost']<=c['follower_minimum_cost']+p['follower_cost_tolerance']+2e-7
     if args.get('recovery_energy_budget_mwh') is not None:assert r['non_event_energy_change_mwh']<=args['recovery_energy_budget_mwh']+2e-7
 for label,r,prices in records:
  pool=np.zeros(T);watts=np.full(T,float(idle));completed={j.name:0. for j in jobs};service=0.
  for a in r['allocations']:
   j=jobmap[a['job']];t=a['slot'];m=a['mode'];f=a['pool_fraction']
   assert j.release<=t<j.deadline and f>=0
   pool[t]+=f;watts[t]+=(power[m]-idle)*f;work=q[m]*f*dt
   completed[j.name]+=work;service+=svc[ji[j.name],t]*work;same(work,a['work'])
  err=max(abs(completed[j.name]-j.work) for j in jobs);max_physical_error=max(max_physical_error,err)
  assert err<2e-7 and pool.max()<=1+2e-7 and np.all(watts<=caps+2e-7)
  same(watts,r['power_mw']);same(service,r['service_cost']);same(prices@watts*dt,r['energy_bill']);same(forecast@watts*dt+service,r['forecast_resource_cost'])
  same(watts.sum()*dt,r['energy_mwh'])
 # Ex-post evaluator must not alter forecasts, offers, schedules or selected quantity.
 before=digest(p)
 for actual in [forecast,forecast[::-1]+3]:
  ev=evaluate_frozen_plan(p,actual);same(ev['selected_commitment_mw'],p['selected_commitment_mw'])
  base=p['baseline'];base_supply=actual@np.asarray(base['power_mw'])*dt
  pairs=[(p['price'],ev['price'])]
  candidate=p['event_candidates'][p['selected_contract_index']]
  pairs += [(candidate[side],ev['selected_contract_'+side+'_endpoint']) for side in ['forecast_best','forecast_worst']]
  for rec,account in pairs:
   actual_supply=actual@np.asarray(rec['power_mw'])*dt
   resource=base_supply-actual_supply+base['service_cost']-rec['service_cost']
   same(resource,account['resource_saving']);same(resource,account['retailer_cash_saving']+account['provider_welfare_change'])
   assert account['weak_participation']
 assert digest(p)==before
 checks.append(name);return p

# Interior quantity is optimal; maximum response creates costly rebound.
base=dict(jobs=[Job('j',0,3,1)],q=[1],power=[1],horizon=3,idle_power=0,
          tariff=[0,1,2],forecast_cost=[10,0,40],event_slots=[0],offered_commitments=[0,.5,1],power_caps=[1,.5,1],follower_cost_tolerance=0)
p=validate('interior_contract_beats_maximum_reduction',base)
same(p['selected_commitment_mw'],.5);same([c['worst_case_forecast_resource_saving'] for c in p['event_candidates']],[0,5,-10])
examples['interior_quantity']={'plan':p,'evaluation':evaluate_frozen_plan(p,base['forecast_cost'])}
before=digest(p)
adverse=evaluate_frozen_plan(p,[0,10,1])
same(adverse['selected_commitment_mw'],.5)
same(adverse['selected_contract_forecast_worst_endpoint']['resource_saving'],-5)
assert digest(p)==before
examples['adverse_realization_without_reselection']=adverse
checks.append('forecast_error_can_reverse_gain_without_oracle_reselection')
# Under equally cheap private responses, opposite system effects are possible.
ties=dict(base,tariff=[0,1,1],power_caps=[1,1,1],offered_commitments=[0,1])
p=validate('follower_tie_bounds_prevent_optimistic_selection',ties)
c=p['event_candidates'][1];same(c['forecast_best']['forecast_resource_cost'],0);same(c['forecast_worst']['forecast_resource_cost'],40);same(p['selected_commitment_mw'],0)
examples['follower_ties']=p
recovery=dict(base,recovery_energy_budget_mwh=0)
p=validate('zero_recovery_budget_rejects_shifted_work_not_deadline_repair',recovery)
assert all(not c['feasible'] for c in p['event_candidates'][1:]);same(p['selected_commitment_mw'],0)
examples['recovery_bound']=p
# Half-hour accounting with idle and explicit service costs, negative tariff.
args=dict(jobs=[Job('j',0,3,.5)],q=[1],power=[1.2],horizon=3,idle_power=.2,dt=.5,
 tariff=[-2,1,3],forecast_cost=[8,-1,10],event_slots=[0],offered_commitments=[0,.5,1],
 service_cost_per_work=[[0,.4,.8]],follower_cost_tolerance=0)
p=validate('negative_price_half_hour_idle_and_service_accounting',args)
examples['half_hour_idle_service']=p
# Explicit epsilon-optimal bounds are wider; tolerance is reported, never concealed.
p=validate('epsilon_follower_ties_are_explicit',dict(base,follower_cost_tolerance=.05))
assert p['follower_cost_tolerance']==.05
# Direct constraints: changing the optimization objective must not change the reference bill.
r=schedule([Job('j',0,2,1)],[1],[1],2,0,prices=[-5,-10],
 reference_objective_ceiling={'prices':[1,3],'service_cost_per_work':[[0,0]],'maximum':1.5})
same(r['slot_average_power'],[.75,.25]);checks.append('reference_bill_constraint_independent_of_secondary_objective')
r=schedule([Job('j',0,2,.5)],[1],[1],2,.2,dt=.5,energy_window_limits=[([0,1],.59)])
assert not r['feasible'];checks.append('window_energy_accounts_for_idle_and_dt')
r=schedule([Job('j',0,2,.5)],[1],[1],2,.2,dt=.5,energy_window_limits=[([0,1],.6)])
assert r['feasible'];same(r['energy'],.6);checks.append('window_energy_exact_idle_boundary')
r=schedule([Job('j',0,2,.5)],[1],[1],2,.2,dt=.5,prices=[-10,0],
 reference_objective_ceiling={'prices':[2,0],'service_cost_per_work':[[0,0]],'maximum':.2})
same(r['slot_average_power'],[.2,1]);checks.append('reference_bill_retains_idle_constant_and_dt')
# Enumeration uses individual integer job-to-slot assignments, not LP matrices.
rng=np.random.default_rng(20260923)
for k in range(60):
 T=4;jobs=[]
 for j in range(2):
  release=int(rng.integers(0,T));deadline=int(rng.integers(release+1,T+1));jobs.append(Job(str(j),release,deadline,1))
 tariff=rng.integers(-2,8,T);forecast=rng.integers(-3,15,T);service=rng.integers(0,3,(2,T))
 schedules=[]
 for slots in itertools.product(*[range(j.release,j.deadline) for j in jobs]):
  if len(set(slots))<len(slots):continue
  power=np.bincount(slots,minlength=T).astype(float);sv=sum(service[i,t] for i,t in enumerate(slots))
  schedules.append(dict(power=power,firm=float(tariff@power+sv),resource=float(forecast@power+sv)))
 args=dict(jobs=jobs,q=[1],power=[1],horizon=T,idle_power=0,tariff=tariff,forecast_cost=forecast,event_slots=[0],offered_commitments=[0,1],service_cost_per_work=service,follower_cost_tolerance=0)
 p=validate(f'exhaustive_assignment_case_{k}',args)
 if not schedules:
  assert not p['feasible'];checks.append(f'exhaustive_infeasible_{k}');cases.append(dict(case=k,feasible=False));continue
 assert p['feasible'];same(p['baseline']['energy_bill']+p['baseline']['service_cost'],min(s['firm'] for s in schedules))
 same(p['price']['forecast_resource_cost'],min(s['resource'] for s in schedules))
 basepower=np.asarray(p['baseline']['power_mw']);c=p['event_candidates'][1]
 eligible=[s for s in schedules if s['power'][0]<=basepower[0]-1+1e-8]
 if not eligible:assert not c['feasible'];chosen=0
 else:
  optimum=min(s['firm'] for s in eligible);followers=[s for s in eligible if s['firm']==optimum]
  lo=min(s['resource'] for s in followers);hi=max(s['resource'] for s in followers)
  same(c['follower_minimum_cost'],optimum);same(c['forecast_best']['forecast_resource_cost'],lo);same(c['forecast_worst']['forecast_resource_cost'],hi)
  chosen=1 if p['baseline']['forecast_resource_cost']-hi>1e-7 else 0
 same(p['selected_commitment_mw'],chosen)
 cases.append(dict(case=k,feasible=True,enumerated_assignments=len(schedules),selected_commitment_mw=chosen))
# Invalid input must fail before producing an apparently legitimate comparison.
for key,value in [('offered_commitments',[1]),('offered_commitments',[0,0]),('offered_commitments',[0,-1]),('event_slots',[0,0]),('event_slots',[.5]),('forecast_cost',[1,2]),('forecast_cost',[1,2,float('nan')]),('recovery_energy_budget_mwh',-1),('follower_cost_tolerance',-1),('service_cost_per_work',[[0,-1,0]])]:
 try:plan_mechanisms(**dict(base,**{key:value}))
 except ValueError:checks.append('reject_'+key+'_'+str(value))
 else:raise AssertionError((key,value))
for kwargs in [dict(energy_window_limits=[([0,0],1)]),dict(energy_window_limits=[([2],1)]),dict(reference_objective_ceiling={'maximum':1})]:
 try:schedule([Job('j',0,2,1)],[1],[1],2,0,**kwargs)
 except ValueError:checks.append('reject_malformed_scheduler_extension')
 else:raise AssertionError(kwargs)
# Planning cannot accept realized costs at all.
try:plan_mechanisms(**base,realized_cost=[1,2,3])
except TypeError:checks.append('planning_api_rejects_realized_information')
else:raise AssertionError('realized data leaked into planning')
for filename,obj in [('analytic_examples.json',examples),('enumerated_cases.json',cases)]:
 (OUT/filename).write_text(json.dumps(obj,indent=2,allow_nan=False)+'\n')
summary=dict(status='PASS_MATHEMATICAL_FRAMEWORK_ONLY',checks=checks,number_of_checks=len(checks),exhaustive_cases=len(cases),exhaustive_feasible_cases=sum(c['feasible'] for c in cases),maximum_reconstructed_work_error=max_physical_error,
 source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [ROOT/'work/research/models/sequential_tasks.py',ROOT/'work/research/models/fair_mechanisms.py',Path(__file__)]},
 scope='Synthetic analytical examples and exhaustive reference assignments, not measured price/contract performance or calibrated regional gains.')
(OUT/'validation.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps({k:v for k,v in summary.items() if k!='checks'},indent=2))
