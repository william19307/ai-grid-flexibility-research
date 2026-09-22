"""Independent integer-dispatch enumeration and physical audits of optional UC.

Integer data with one thermal unit plus unrestricted backup have an integral
continuous-dispatch polytope for each status path (bounded difference constraints).
Enumerating integer dispatch therefore gives an exact small-case oracle, without
using the MILP's matrix construction. These are mathematical tests, not fleet data.
"""
from pathlib import Path
from dataclasses import replace
import itertools, json, hashlib, sys
import numpy as np
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'work/research/models'))
from coupled_grid_compute import Generator, Scenario, Storage, ComputePool, Batch, Reservoir, Line, solve
from thermal_commitment import ThermalCommitment
OUT=ROOT/'outputs/research/revision/commitment/validation'
OUT.mkdir(parents=True,exist_ok=True)
checks=[]; errors=[]


def inspect_power(path, control, generator, availability, dt):
    old_on=control.initial_on; age=control.initial_duration_steps; old_p=control.initial_dispatch_mw
    starts=[];stops=[]
    for t,p in enumerate(path):
        on=p>1e-7
        if on and (p<generator.min_output_fraction*generator.existing_mw-1e-7 or p>generator.existing_mw*availability[t]+1e-7):return None
        if on!=old_on:
            required=control.min_up_steps if old_on else control.min_down_steps
            if age<required:return None
        if on and not old_on and p>control.startup_limit_mw+1e-7:return None
        if old_on and not on and old_p>control.shutdown_limit_mw+1e-7:return None
        if on and old_on and (p-old_p>dt*control.ramp_up_mw_per_hour+1e-7 or old_p-p>dt*control.ramp_down_mw_per_hour+1e-7):return None
        starts.append(int(on and not old_on));stops.append(int(old_on and not on))
        age=age+1 if on==old_on else 1
        old_on=on;old_p=p
    return np.array(starts),np.array(stops),age


def build(load,backup_prices,availability,control,dt=1,prob=1,scenario='s'):
    g=Generator('thermal','A',4,0,0,2,1,availability={scenario:availability},min_output_fraction=.25)
    generators=[g]+[Generator(f'backup{t}','A',20,0,0,float(v),0,availability={scenario:[int(k==t) for k in range(len(load))]}) for t,v in enumerate(backup_prices)]
    return g,generators,[Scenario(scenario,prob,{'A':load})]

rng=np.random.default_rng(22092026)
for k in range(64):
    T=5; dt=float(rng.choice([.5,1,2]));load=rng.integers(0,7,T);backup=rng.integers(5,18,T)
    initial=bool(rng.integers(0,2));initial_p=int(rng.integers(1,5)) if initial else 0
    c=ThermalCommitment('thermal',min_up_steps=int(rng.integers(1,4)),min_down_steps=int(rng.integers(1,4)),
         startup_cost=float(rng.integers(0,16)),shutdown_cost=float(rng.integers(0,6)),no_load_cost_per_hour=float(rng.integers(0,5)),
         ramp_up_mw_per_hour=float(rng.integers(1,5))/dt,ramp_down_mw_per_hour=float(rng.integers(1,5))/dt,
         startup_limit_mw=float(rng.integers(1,5)),shutdown_limit_mw=float(rng.integers(1,5)),
         initial_on=initial,initial_dispatch_mw=initial_p,initial_duration_steps=int(rng.integers(1,4)))
    availability=rng.choice([0.,.5,1.],T,p=[.1,.1,.8]);g,gens,sc=build(load,backup,availability,c,dt)
    best=np.inf
    for path in itertools.product(*[range(min(int(v),4)+1) for v in load]):
        audit=inspect_power(path,c,g,availability,dt)
        if audit is None:continue
        start,stop,age=audit;p=np.array(path)
        cost=dt*(2*p+backup*(load-p)+c.no_load_cost_per_hour*(p>0)).sum()+c.startup_cost*start.sum()+c.shutdown_cost*stop.sum()
        best=min(best,float(cost))
    result=solve(['A'],sc,gens,dt=dt,commitments=[c])
    if not np.isfinite(best):
        assert not result['feasible'] and result['proven_infeasible'],(k,best,result)
    else:
        assert result['feasible'],(k,result)
        err=abs(result['total_cost']-best);errors.append(err);assert err<1e-6,(k,best,result['total_cost'])
        rr=result['scenarios']['s'];p=np.array(rr['generation']['thermal']);unit=rr['unit_commitment']['thermal']
        audit=inspect_power(p,c,g,availability,dt);assert audit is not None
        start,stop,age=audit
        assert np.allclose(unit['startup'],start) and np.allclose(unit['shutdown'],stop)
        assert np.allclose(unit['on'],p>1e-7)
        assert rr['terminal_unit_state']['thermal']['duration_steps']==age
        total=np.sum(list(rr['generation'].values()),axis=0);assert np.allclose(total,load)
        assert rr['nodal_balance_marginal_cost'] is None and result['mip_gap']<=1e-8
    checks.append(f'exact_enumerated_commitment_{k}')

# Startup cost is per event, not per hour; no-load cost is per online hour.
c=ThermalCommitment('thermal',startup_cost=8,no_load_cost_per_hour=2)
for dt in [.25,1,2]:
    g,gs,sc=build([1],[100],[1],c,dt)
    r=solve(['A'],sc,gs,dt=dt,commitments=[c]);expected=8+4*dt
    assert abs(r['total_cost']-expected)<1e-8,(r,expected)
    checks.append(f'event_and_hourly_cost_units_{dt}')

# Initial obligation cannot disappear at the left boundary; end obligations are explicit.
c=ThermalCommitment('thermal',min_up_steps=3,initial_on=True,initial_dispatch_mw=1,initial_duration_steps=1)
g,gs,sc=build([1,1],[100,100],[1,1],c)
r=solve(['A'],sc,gs,commitments=[c]);assert r['scenarios']['s']['unit_commitment']['thermal']['on']==[1.,1.]
c=replace(c,initial_on=False,initial_dispatch_mw=0,initial_duration_steps=3)
r=solve(['A'],sc,gs,commitments=[c]);assert r['scenarios']['s']['terminal_unit_state']['thermal']['remaining_minimum_time_steps']==1
checks+=['initial_duration_carried','unfinished_terminal_obligation_reported']

# Commitment participates in the same storage/compute balances, rather than being
# an ex-post filter. Shift a fixed batch to avoid an otherwise additional startup.
c=ThermalCommitment('thermal',startup_cost=10,min_up_steps=1)
g=Generator('thermal','A',2,0,0,1,min_output_fraction=.5)
sc=[Scenario('s',1,{'A':[1,0,0]})]
p=ComputePool('ai','A',[1],[1],0,{'s':[Batch('job',0,3,1)]})
r=solve(['A'],sc,[g],pools=[p],commitments=[c]);assert abs(r['total_cost']-12)<1e-7
assert np.allclose(r['scenarios']['s']['compute_power_mw']['ai'],[1,0,0])
checks.append('endogenous_commitment_and_compute_joint_balance')

# Shared scenario probabilities weight costs, not physical unit capacities.
g=Generator('thermal','A',4,0,0,2,min_output_fraction=.25)
c=ThermalCommitment('thermal',startup_cost=7)
r=solve(['A'],[Scenario('a',.25,{'A':[1]}),Scenario('b',.75,{'A':[3]})],[g],commitments=[c])
assert abs(r['total_cost']-(7+2*(.25+2.25)))<1e-7
checks.append('scenario_weighted_costs_and_fixed_physical_capacity')

# Storage is inside the same MILP; an extra generated MWh can avoid a second start.
c=ThermalCommitment('thermal',startup_cost=10)
g=Generator('thermal','A',2,0,0,1,min_output_fraction=.5)
r=solve(['A'],[Scenario('s',1,{'A':[1,0,1]})],[g],
        storage=[Storage('b','A',1,1,throughput_cost=.001)],commitments=[c])
assert abs(r['total_cost']-12.002)<1e-7
rr=r['scenarios']['s'];assert np.allclose(np.diff(rr['soc']['b']),np.array(rr['charge']['b'])-rr['discharge']['b'])
checks.append('storage_balance_and_startup_cost_joint_optimization')

# Lossless transmission and an exact one-hour river inflow remain conserved.
r=solve(['A','B'],[Scenario('s',1,{'A':[0,0],'B':[1,1]})],[g],
        lines=[Line('link','A','B',1,flow_cost_per_mwh=0)],
        reservoirs=[Reservoir('river','B',1,0,0,1000,{'s':[0,.001]})],commitments=[c])
assert abs(r['total_cost']-11)<1e-7
assert np.allclose(r['scenarios']['s']['hydro_generation']['river'],[0,1])
checks.append('transmission_and_water_balance_with_commitment')

# Two independently committable machines choose the cheaper total commitment.
g2=Generator('peaker','A',1,0,0,5,min_output_fraction=1)
r=solve(['A'],[Scenario('s',1,{'A':[1,1]})],[g,g2],
        commitments=[c,ThermalCommitment('peaker')])
assert abs(r['total_cost']-10)<1e-7 and np.allclose(r['scenarios']['s']['unit_commitment']['thermal']['on'],[0,0])
checks.append('multiple_units_endogenous_selection')

for c,bad_g in [(ThermalCommitment('typo'),g),(replace(c,min_up_steps=0),g),
                (replace(c,initial_dispatch_mw=1),g),(replace(c,initial_on=1),g),
                (replace(c,ramp_up_mw_per_hour=float('nan')),g),(c,replace(g,max_new_mw=1))]:
    try:solve(['A'],[Scenario('s',1,{'A':[1]})],[bad_g],commitments=[c])
    except ValueError:pass
    else:raise AssertionError('Accepted invalid commitment input')
checks.append('invalid_control_and_extendable_unit_inputs_rejected')

files=[Path(__file__),ROOT/'work/research/models/coupled_grid_compute.py',ROOT/'work/research/models/thermal_commitment.py']
report=dict(number_of_checks=len(checks),checks=checks,exact_dispatch_enumeration_cases=64,
            maximum_objective_error=max(errors),scope='Mathematical validation, not calibrated provincial unit commitment or full-year reliability',
            source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files})
(OUT/'thermal_commitment_validation.json').write_text(json.dumps(report,indent=2)+'\n')
(OUT/'source_snapshot.json').write_text(json.dumps({str(p.relative_to(ROOT)):p.read_text() for p in files},indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in ['checks','source_sha256']},indent=2))
