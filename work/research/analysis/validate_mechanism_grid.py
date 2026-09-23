"""Independent hand-cost and physical references for frozen-response grid linkage."""
from pathlib import Path
from dataclasses import replace, asdict
import copy, json, sys, hashlib
from unittest.mock import patch
import numpy as np
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'work/research/models'))
from sequential_tasks import Job
from fair_mechanisms import plan_mechanisms
from coupled_grid_compute import Generator,Scenario,Line,Storage
from thermal_commitment import ThermalCommitment
from mechanism_grid import evaluate_plan_on_grid,evaluate_frozen_response,fingerprint
OUT=ROOT/'outputs/research/revision/mechanism_grid'
checks=[]; examples={}; errors=[]
def same(a,b):
    err=float(np.max(np.abs(np.asarray(a)-np.asarray(b))))
    errors.append(err); assert err<2e-7,(a,b,err)

def reconstruct(result,grid,power,node):
    """Rebuild grid balances and costs from asset records, not solver matrices."""
    if result['feasible'] is not True:return
    sc=grid['scenario']; r=result['scenarios'][sc.name]; dt=grid['dt']; T=len(power)
    net={n:np.zeros(T) for n in grid['nodes']}; total=0.
    for g in grid['generators']:
        p=np.asarray(r['generation'][g.name]); net[g.node]+=p; total+=p.sum()*dt*g.marginal_cost
        assert (p>=-2e-7).all() and (p<=g.existing_mw*np.asarray(g.availability.get(sc.name,[1]*T))+2e-7).all()
    for l in grid.get('lines',[]):
        f=np.asarray(r['line_forward'][l.name]); b=np.asarray(r['line_reverse'][l.name])
        assert (f+b<=l.existing_mw+2e-7).all()
        net[l.source]+=(1-l.loss_fraction)*b-f; net[l.target]+=(1-l.loss_fraction)*f-b
        total+=(f+b).sum()*dt*l.flow_cost_per_mwh
    for control in grid.get('commitments',[]):
        u=r['unit_commitment'][control.generator]; on=np.rint(u['on']).astype(int)
        start=np.maximum(on-np.r_[int(control.initial_on),on[:-1]],0)
        stop=np.maximum(np.r_[int(control.initial_on),on[:-1]]-on,0)
        same(u['startup'],start);same(u['shutdown'],stop)
        total+=start.sum()*control.startup_cost+stop.sum()*control.shutdown_cost+on.sum()*dt*control.no_load_cost_per_hour
    for n in grid['nodes']:
        expected=np.asarray(sc.load_mw[n])+ (np.asarray(power) if n==node else 0)
        same(net[n],expected); same(r['unserved'][n],0)
    same(total,result['total_cost']);same(result['expected_unserved_mwh'],0)

task=dict(jobs=[Job('j',0,3,1)],q=[1],power=[1],horizon=3,idle_power=0)
args=dict(task,tariff=[0,1,1],forecast_cost=[30,0,1],event_slots=[0],offered_commitments=[0,1],follower_cost_tolerance=0)
plan=plan_mechanisms(**args); before=fingerprint(plan);same(plan['selected_commitment_mw'],1)
grid=dict(nodes=['A'],scenario=Scenario('s',1,{'A':[0,0,0]}),dt=1.,generators=[
    Generator('existing','A',1,0,0,5,availability={'s':[1,0,0]}),
    Generator('recovery1','A',1,0,0,0,availability={'s':[0,1,0]}),
    Generator('recovery2','A',1,0,0,0,availability={'s':[0,0,1]})],
    commitments=[ThermalCommitment('recovery1',startup_cost=10),ThermalCommitment('recovery2',startup_cost=10)])
evaluated=evaluate_plan_on_grid(plan,task,grid,'A')
same(evaluated['responses']['baseline']['grid']['total_cost'],5)
for label in ['price']+evaluated['selected_endpoint_labels']:
    r=evaluated['responses'][label]
    same(r['grid']['total_cost'],10);same(r['accounting']['horizon_resource_saving'],-5)
    same(r['accounting']['horizon_resource_saving'],r['accounting']['retailer_cash_saving']+r['accounting']['provider_welfare_change'])
same(plan['event_candidates'][1]['worst_case_forecast_resource_saving'],29)
assert fingerprint(plan)==before and evaluated['selected_commitment_mw']==1
checks+=['startup_cost_reverses_forecast_gain_without_reselection','transfer_identity_under_nonlinear_supply_cost','plan_unchanged_by_grid_evaluation']
# Any interior split requires both cold, time-specific resources. Endpoints need
# one start. This independent piecewise formula proves the entire continuum:
# C(x)=10 at x=0,1; C(x)=20 for 0<x<1, since positive output forces that unit on.
# Both recovery slots have tariff 1, so the entire line remains follower-optimal.
mixtures=[]
for x in np.linspace(0,1,21):
    rec=copy.deepcopy(plan['event_candidates'][1]['forecast_best'])
    rec['power_mw']=[0,float(x),float(1-x)]; rec['allocations']=[]
    for t,w in [(1,float(x)),(2,float(1-x))]:
        if w>0:rec['allocations'].append(dict(job='j',slot=t,mode=0,pool_fraction=w,work=w))
    rec['forecast_resource_cost']=1-float(x)
    out=evaluate_frozen_response(rec,task,args['tariff'],grid,'A')
    expected=10*int(x>0)+10*int(x<1)
    same(rec['energy_bill'],1);same(rec['service_cost'],0);same(out['grid']['total_cost'],expected)
    reconstruct(out['grid'],grid,rec['power_mw'],'A')
    mixtures.append(dict(x=float(x),record=rec,evaluation=out,independent_cost=expected))
same(mixtures[10]['evaluation']['grid']['total_cost'],20)
checks.append('21_follower_mixtures_match_independent_continuous_startup_formula')
examples['nonlinear_follower_interior']={'plan':plan,'grid_evaluation':evaluated,'mixtures':mixtures,
    'separate_analytic_grid_aware_comparator':{'offer_set':[0,1],'worst_resource_savings':[0,-15],
        'optimal_commitment_mw':0,'basis':'Continuous piecewise startup-cost proof, not inference from the 21-point sweep',
        'not_applied_to_frozen_plan':True}}

# Congestion and losses: source needs .5 MW to deliver .4 MW on a 20%-loss line;
# remaining .6 MWh is supplied locally at 20; full-hour physical saving = 8.
t2=dict(jobs=[Job('j',0,2,1)],q=[1],power=[1],horizon=2,idle_power=0)
p2=plan_mechanisms(**t2,tariff=[0,1],forecast_cost=[10,0],event_slots=[0],offered_commitments=[0,1],follower_cost_tolerance=0)
g2=dict(nodes=['A','B'],scenario=Scenario('s',1,{'A':[0,0],'B':[0,0]}),dt=1.,generators=[
    Generator('renewable','A',2,0,0,0,availability={'s':[0,1]}),Generator('local','B',1,0,0,20)],
    lines=[Line('link','A','B',.5,loss_fraction=.2,flow_cost_per_mwh=0)])
e2=evaluate_plan_on_grid(p2,t2,g2,'B')
same(e2['responses']['baseline']['grid']['total_cost'],20)
same(e2['responses']['price']['grid']['total_cost'],12)
same(e2['responses']['price']['accounting']['horizon_resource_saving'],8)
for label,r in e2['responses'].items():
    power=p2['baseline']['power_mw'] if label in ['baseline','offer_0_forecast_best','offer_0_forecast_worst'] else p2['price']['power_mw']
    reconstruct(r['grid'],g2,power,'B')
checks.append('transmission_capacity_and_losses_restrict_grid_value')
examples['lossy_congestion']={'plan':p2,'evaluation':e2}

# Infeasible shifted load remains infeasible; no investment or shedding repairs it.
bad=copy.deepcopy(grid);bad['generators']=bad['generators'][:1];bad['commitments']=[]
eb=evaluate_plan_on_grid(plan,task,bad,'A')
assert eb['responses']['baseline']['grid']['feasible'] is True
for label in eb['selected_endpoint_labels']:
    assert eb['responses'][label]['grid']['proven_infeasible'] and eb['responses'][label]['accounting'] is None
checks.append('grid_infeasibility_retained_without_reselection_or_demand_repair')
examples['infeasible_grid_response']=eb
# An unresolved solver state is distinct from a proof of infeasibility.
with patch('mechanism_grid.solve',return_value=dict(feasible=None,solver_status=1,proven_infeasible=False,accepted_optimal_solution=False)):
    unknown=evaluate_plan_on_grid(plan,task,grid,'A')
assert all(r['grid']['feasible'] is None and r['accounting'] is None for r in unknown['responses'].values())
checks.append('unresolved_solver_state_not_misreported_as_infeasible')
# End-of-horizon obligations are retained; the accounting is horizon-limited.
tail=dict(g2,nodes=['B'],scenario=Scenario('s',1,{'B':[0,0]}),lines=[],generators=[Generator('u','B',1,0,0,1)],
          commitments=[ThermalCommitment('u',min_up_steps=3,startup_cost=2)])
et=evaluate_plan_on_grid(p2,t2,tail,'B')
assert et['responses']['price']['terminal_minimum_time_obligation']
assert et['responses']['price']['accounting']['unresolved_terminal_obligations']
checks.append('terminal_minimum_time_obligations_explicit')
examples['unsettled_terminal_boundary']=et

# Half-hour idle and service costs retained in the external power boundary.
th=dict(jobs=[Job('j',0,2,.5)],q=[1],power=[1.2],horizon=2,idle_power=.2,dt=.5,service_cost_per_work=[[0,2]])
ph=plan_mechanisms(**th,tariff=[0,1],forecast_cost=[20,0],event_slots=[0],offered_commitments=[0,1],follower_cost_tolerance=0)
gh=dict(nodes=['A'],scenario=Scenario('s',1,{'A':[0,0]}),dt=.5,generators=[Generator('u','A',2,0,0,3)])
eh=evaluate_plan_on_grid(ph,th,gh,'A')
same(eh['responses']['price']['grid']['total_cost'],2.1)
same(eh['responses']['price']['accounting']['horizon_resource_saving'],-1)
same(eh['responses']['price']['task_certificate']['reconstructed_energy_mwh'],.7)
checks.append('half_hour_idle_and_service_costs_preserved')
unlimited=evaluate_plan_on_grid(ph,dict(th,power_caps=[np.inf,np.inf]),gh,'A')
same(unlimited['responses']['price']['grid']['total_cost'],2.1)
checks.append('explicit_unlimited_task_caps_have_portable_fingerprint')

def rejected(name,fn):
    try:fn()
    except ValueError:checks.append(name)
    else:raise AssertionError('Invalid input accepted: '+name)
for field,modified in [
    ('generation',dict(grid,generators=[replace(grid['generators'][0],max_new_mw=1)]+grid['generators'][1:])),
    ('line',dict(g2,lines=[replace(g2['lines'][0],max_new_mw=1)])),
    ('storage',dict(grid,storage=[Storage('b','A',max_new_energy_mwh=1)]))]:
    pp,tt,nn=(p2,t2,'B') if field=='line' else (plan,task,'A')
    rejected('reject_'+field+'_expansion',lambda:evaluate_plan_on_grid(pp,tt,modified,nn))
rejected('reject_clock_mismatch',lambda:evaluate_plan_on_grid(plan,task,dict(grid,dt=.5),'A'))
rejected('reject_shedding_override',lambda:evaluate_plan_on_grid(plan,task,dict(grid,expected_unserved_limit_mwh=1),'A'))
corrupt=copy.deepcopy(plan);corrupt['price']['power_mw'][1]+=.2
rejected('reject_power_without_matching_work',lambda:evaluate_plan_on_grid(corrupt,task,grid,'A'))
corrupt=copy.deepcopy(plan);corrupt['price']['allocations'][0]['work']+=.1
rejected('reject_modified_task_work',lambda:evaluate_plan_on_grid(corrupt,task,grid,'A'))
corrupt=copy.deepcopy(plan);corrupt['price']['participation_transfer']+=1
rejected('reject_modified_transfer_floor',lambda:evaluate_plan_on_grid(corrupt,task,grid,'A'))
corrupt=copy.deepcopy(plan);corrupt['event_candidates'][1]['forecast_best']=copy.deepcopy(corrupt['baseline'])
rejected('reject_broken_event_commitment',lambda:evaluate_plan_on_grid(corrupt,task,grid,'A'))
corrupt=copy.deepcopy(plan);corrupt['event_candidates'][0]['forecast_best']=copy.deepcopy(corrupt['price'])
rejected('reject_replaced_zero_offer_outside_option',lambda:evaluate_plan_on_grid(corrupt,task,grid,'A'))

files=[Path(__file__),ROOT/'work/research/models/mechanism_grid.py',ROOT/'work/research/models/fair_mechanisms.py',ROOT/'work/research/models/sequential_tasks.py',ROOT/'work/research/models/coupled_grid_compute.py',ROOT/'work/research/models/thermal_commitment.py']
report=dict(status='PASS_CONDITIONAL_GRID_INTEGRATION_ONLY',number_of_checks=len(checks),checks=checks,
    maximum_reference_error=max(errors),continuous_follower_cost_formula='10 at x=0 or 1; 20 at every 0<x<1',
    source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files},
    scope='Synthetic inputs, fixed capacity, conditional perfect-foresight grid redispatch; no provincial, online, market-equilibrium or empirical forecast claim')
(OUT/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
(OUT/'examples.json').write_text(json.dumps(examples,indent=2)+'\n')
(OUT/'input_snapshot.json').write_text(json.dumps({'main_task':task,'main_grid':grid,'congestion_grid':g2},default=lambda x:asdict(x),indent=2)+'\n')
print(json.dumps(report,indent=2))
