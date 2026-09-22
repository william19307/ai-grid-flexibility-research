"""Analytical synthetic checks of full-year fixed-capacity evaluation.

These fixtures are mathematical validation, not observed provincial results.
"""
from pathlib import Path
from dataclasses import replace
import copy,hashlib,json,sys
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'work/research/models'))
from coupled_grid_compute import Generator,Line,Storage,Scenario,solve
from thermal_commitment import ThermalCommitment
from fixed_fleet_validation import freeze_investments,evaluate_year,annual_clock
OUT=ROOT/'outputs/research/revision/fixed_fleet_annual';OUT.mkdir(parents=True,exist_ok=True)
checks=[];examples={}


def rejects(name,fn):
    try:fn()
    except (ValueError,KeyError):checks.append(name)
    else:raise AssertionError('Invalid input accepted: '+name)


g=Generator('g','A',2,10,10,20000)
planning=solve(['A'],[Scenario('train',1,{'A':[4.]})],[g])
fleet=freeze_investments(planning,[g])
assert fleet.generators[0].existing_mw==4 and fleet.generators[0].max_new_mw==0
assert g.existing_mw==2 and g.max_new_mw==10
checks.append('freeze_existing_plus_new_without_mutating_planning_asset')
clock=pd.date_range('2021-01-01','2022-01-01',freq='h',inclusive='left',tz='Asia/Shanghai')
load=np.full(len(clock),2.);load[[123,8000]]=7
availability=np.ones(len(clock));availability[100:110]=0;availability[500:510]=.25
expected=float(np.maximum(load-4*availability,0).sum())
r=evaluate_year(fleet,['A'],Scenario('test',1,{'A':load}),clock,{'g':availability},eue_tolerance_mwh=0)
assert r['accepted'] and abs(r['minimum_eue_mwh']-expected)<1e-7
assert abs(r['reported_eue_mwh']-expected)<1e-7
assert r['shortage_hours_in_reported_dispatch']==22
assert r['dispatch_result']['cost_components']['investment']==0
checks+=['8760_hour_deficit_equals_independent_capacity_formula','high_operating_cost_does_not_create_economic_shedding','no_test_year_investment']
examples['annual_capacity_formula']=dict(hours=len(clock),expected_eue_mwh=expected,actual_eue_mwh=r['minimum_eue_mwh'],shortage_hours=r['shortage_hours_in_reported_dispatch'])

# A one-hour scarcity event requires new capacity if investment is wrongly reopened.
plain=evaluate_year(fleet,['A'],Scenario('plain',1,{'A':load}),clock,{'g':np.ones(len(clock))},eue_tolerance_mwh=0)
refit=solve(['A'],[Scenario('refit',1,{'A':load})],[g])
assert plain['minimum_eue_mwh']==6 and refit['expected_unserved_mwh']==0 and refit['new_generator_mw']['g']==5
checks.append('reoptimizing_capacity_masks_six_MWh_test_deficit')
examples['forbidden_refit_comparison']=dict(frozen_total_capacity_mw=4,frozen_eue_mwh=6,refitted_total_capacity_mw=7,refitted_eue_mwh=0)

emitter=replace(g,emissions_t_per_mwh=1.)
ep=solve(['A'],[Scenario('train',1,{'A':[4.]})],[emitter])
ef=freeze_investments(ep,[emitter])
ec=evaluate_year(ef,['A'],Scenario('carbon',1,{'A':np.full(8760,2.)}),clock,{'g':np.ones(8760)},emissions_limit_t=17510.,eue_tolerance_mwh=0)
assert ec['accepted'] and abs(ec['minimum_eue_mwh']-10)<1e-7
assert abs(ec['dispatch_result']['expected_emissions_t']-17510)<1e-7
checks.append('explicit_annual_carbon_constraint_retained_in_both_phases')

for label,stamps in [('missing_hour',clock.delete(13)),('duplicate_hour',clock.insert(10,clock[10])),('naive_time',clock.tz_localize(None)),('padded_nonleap',clock.append(clock[-24:]))]:
    rejects(label,lambda stamps=stamps:annual_clock(stamps))
rejects('missing_availability',lambda:evaluate_year(fleet,['A'],Scenario('test',1,{'A':load}),clock,{}))
bad_availability=availability.copy();bad_availability[2]=np.nan
rejects('nonfinite_availability',lambda:evaluate_year(fleet,['A'],Scenario('test',1,{'A':load}),clock,{'g':bad_availability}))
hard_ai=evaluate_year(fleet,['A'],Scenario('AI',1,{'A':np.zeros(8760)}),clock,{'g':np.ones(8760)},
    external_fixed_load={'AI':{'A':np.full(8760,5.)}})
assert not hard_ai['accepted'] and hard_ai['phase']=='minimum_eue' and hard_ai['solver_result']['proven_infeasible']
checks.append('mandatory_AI_infeasibility_preserved_not_relabelled_as_zero_EUE')
changed=copy.deepcopy(fleet);changed.generators[0].existing_mw=7
rejects('changed_frozen_capacity',lambda:evaluate_year(changed,['A'],Scenario('test',1,{'A':load}),clock,{'g':availability}))
for name,mut in [('unresolved_solution',{'feasible':None}),('nonoptimal_solution',{'solver_status':1}),('excess_investment',{'new_generator_mw':{'g':11}}),('unknown_asset',{'new_generator_mw':{'other':2}}),('bad_residual',{'max_equality_residual':.1})]:
    rejects(name,lambda mut=mut:freeze_investments(dict(planning,**mut),[g]))

# Investment units and storage carry across midnight, in an actual leap-year clock.
gg=Generator('source','A',8,0,0,0,availability={'train':[1,0]})
ll=Line('link','A','B',1,3,1)
bb=Storage('battery','B',max_new_power_mw=4,max_new_energy_mwh=4,power_investment_cost=1,energy_investment_cost=1)
rr=solve(['A','B'],[Scenario('train',1,{'A':[0,0],'B':[0,4]})],[gg],[ll],[bb])
ff=freeze_investments(rr,[gg],[ll],[bb])
assert ff.lines[0].existing_mw==4 and ff.storage[0].existing_power_mw==4 and ff.storage[0].existing_energy_mwh==4
leap=pd.date_range('2020-01-01','2021-01-01',freq='h',inclusive='left',tz='Asia/Shanghai')
zero=np.zeros(len(leap));bload=zero.copy();bload[25]=4;av=zero.copy();av[23]=1
sr=evaluate_year(ff,['A','B'],Scenario('leap',1,{'A':zero,'B':bload}),leap,{'source':av},eue_tolerance_mwh=0)
assert sr['accepted'] and sr['minimum_eue_mwh']==0
soc=sr['dispatch_result']['scenarios']['leap']['soc']['battery']
assert len(soc)==8785 and abs(soc[24]-4)<1e-7 and abs(soc[25]-4)<1e-7 and abs(soc[26])<1e-7
assert soc[0]==0 and soc[-1]==0
checks+=['line_and_storage_power_energy_investments_frozen','8784_hour_leap_calendar','energy_carries_across_midnight_without_daily_reset']
examples['leap_storage']=dict(hours=8784,eue_mwh=sr['minimum_eue_mwh'],soc_h24=soc[24],soc_h25=soc[25],soc_h26=soc[26])

# Full-year optional UC remains active; no relaxation to continuous commitment.
thermal=Generator('thermal','A',4,0,0,2,min_output_fraction=.25)
control=ThermalCommitment('thermal',min_up_steps=2,min_down_steps=2,startup_cost=10,no_load_cost_per_hour=1,
    initial_on=True,initial_dispatch_mw=2,initial_duration_steps=3)
tp=solve(['A'],[Scenario('train',1,{'A':[2,2]})],[thermal],commitments=[control])
tf=freeze_investments(tp,[thermal])
ur=evaluate_year(tf,['A'],Scenario('year',1,{'A':np.full(8760,2.)}),clock,{'thermal':np.ones(8760)},commitments=[control],eue_tolerance_mwh=0,milp_time_limit_s=60)
assert ur['accepted'],ur
dispatch=ur['dispatch_result'];units=dispatch['scenarios']['year']['unit_commitment']['thermal']
assert dispatch['solver_type']=='MILP' and sum(units['on'])==8760 and sum(units['startup'])==0
assert abs(dispatch['total_cost']-5*8760)<1e-6
checks.append('full_year_binary_commitment_and_costs_preserved')
examples['annual_commitment']=dict(hours=8760,minimum_eue_mwh=ur['minimum_eue_mwh'],cost=dispatch['total_cost'],solver_type=dispatch['solver_type'])

source_files=[Path(__file__),ROOT/'work/research/models/fixed_fleet_validation.py',ROOT/'work/research/models/coupled_grid_compute.py',ROOT/'work/research/models/thermal_commitment.py']
summary=dict(checks=checks,count=len(checks),examples=examples,scope='Synthetic analytical checks only; no provincial empirical adequacy claim',
    source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in source_files})
(OUT/'validation.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary,indent=2),flush=True)
