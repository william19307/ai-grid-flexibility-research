"""Independent physical reconstruction and analytic economic oracles for joint LP.

All cases are mathematical validation cases, not estimates for China's grid.
"""
from pathlib import Path
import sys,json,hashlib,itertools
import numpy as np

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'work/research/models'))
from coupled_grid_compute import Generator,Line,Storage,Batch,ComputePool,Scenario,solve

OUT=ROOT/'outputs/research/tables'
checks=[];results={};max_errors=[]

def equal(a,b):
    assert np.allclose(a,b,atol=1e-7,rtol=1e-8),(a,b)

def checked(label,nodes,scenarios,generators,lines=(),storage=(),pools=(),**kwargs):
    r=solve(nodes,scenarios,generators,lines,storage,pools,**kwargs)
    assert r['feasible'],(label,r)
    dt=kwargs.get('dt',1.);total_co2=0.;total_eens=0.;service=0.;operating=0.
    investment=sum(g.investment_cost*r['new_generator_mw'][g.name] for g in generators)
    investment+=sum(l.investment_cost*r['new_line_mw'][l.name] for l in lines)
    investment+=sum(b.power_investment_cost*r['new_storage_power_mw'][b.name]+b.energy_investment_cost*r['new_storage_energy_mwh'][b.name] for b in storage)
    for s in scenarios:
        rr=r['scenarios'][s.name];T=len(s.load_mw[nodes[0]])
        balance={n:-np.array(s.load_mw[n],float) for n in nodes}
        for n in nodes:
            shed=np.array(rr['unserved'][n]);assert (shed>=-1e-8).all() and (shed<=np.array(s.load_mw[n])+1e-8).all()
            balance[n]+=shed;total_eens+=s.probability*dt*shed.sum()
        for g in generators:
            y=np.array(rr['generation'][g.name]);cap=g.existing_mw+r['new_generator_mw'][g.name]
            av=np.array(g.availability.get(s.name,np.ones(T)))
            assert (y>=-1e-8).all() and (y<=cap*av+1e-7).all()
            balance[g.node]+=y;operating+=s.probability*dt*y.sum()*g.marginal_cost
            total_co2+=s.probability*dt*y.sum()*g.emissions_t_per_mwh
        for l in lines:
            f=np.array(rr['line_forward'][l.name]);v=np.array(rr['line_reverse'][l.name])
            assert (f+v<=l.existing_mw+r['new_line_mw'][l.name]+1e-7).all()
            balance[l.source]+=-f+(1-l.loss_fraction)*v
            balance[l.target]+=-v+(1-l.loss_fraction)*f
            operating+=s.probability*dt*(f+v).sum()*l.flow_cost_per_mwh
        for b in storage:
            c=np.array(rr['charge'][b.name]);d=np.array(rr['discharge'][b.name]);soc=np.array(rr['soc'][b.name])
            assert (c+d<=b.existing_power_mw+r['new_storage_power_mw'][b.name]+1e-7).all()
            assert (soc>=-1e-8).all() and (soc<=b.existing_energy_mwh+r['new_storage_energy_mwh'][b.name]+1e-7).all()
            equal(np.diff(soc),dt*(b.charge_efficiency*c-d/b.discharge_efficiency))
            equal(soc[0],b.initial_soc_fraction*(b.existing_energy_mwh+r['new_storage_energy_mwh'][b.name]))
            equal(soc[-1],soc[0]);balance[b.node]+=d-c
            operating+=s.probability*dt*(c+d).sum()*b.throughput_cost
        for p in pools:
            power=np.full(T,p.idle_power_mw,dtype=float);occupancy=np.zeros(T)
            jobs={j.name:j for j in p.jobs[s.name]};work={j.name:0. for j in p.jobs[s.name]}
            for a in rr['task_allocations'][p.name]:
                j=jobs[a['batch']];t=a['slot'];mode=a['mode'];f=a['pool_fraction']
                assert j.release<=t<j.deadline and f>=0
                occupancy[t]+=f;power[t]+=f*(p.mode_power_mw[mode]-p.idle_power_mw)
                w=f*p.rates[mode]*dt;work[j.name]+=w
                service+=s.probability*j.delay_cost_per_work_hour*(t-j.release)*dt*w
            assert (occupancy<=1+1e-7).all() and (power<=p.connection_limit_mw+1e-7).all()
            for j in jobs.values():equal(work[j.name],j.work)
            equal(power,rr['compute_power_mw'][p.name]);balance[p.node]-=power
        error=max(float(np.max(np.abs(v))) for v in balance.values());assert error<1e-7,(label,error)
        max_errors.append(error)
    equal(total_co2,r['expected_emissions_t']);equal(total_eens,r['expected_unserved_mwh'])
    equal(investment,r['cost_components']['investment']);equal(operating,r['cost_components']['operating'])
    equal(service,r['cost_components']['service_delay'])
    equal(investment+operating+service+total_eens*kwargs.get('unserved_cost',10000),r['total_cost'])
    checks.append(label);return r

# Capacity is MW and operation is MWh: one period and half-hour variants.
for dt,expected in [(1.,13.),(.5,11.5)]:
    r=checked(f'capacity_vs_energy_dt_{dt}',['A'],[Scenario('s',1,{'A':[1]})],[Generator('g','A',0,2,10,3)],dt=dt)
    equal(r['new_generator_mw']['g'],1);equal(r['total_cost'],expected)

# A single investment must accommodate both scenarios; it is not probability-averaged capacity.
r=checked('shared_investment',['A'],[Scenario('low',.75,{'A':[1]}),Scenario('high',.25,{'A':[2]})],[Generator('g','A',0,3,10,3)])
equal(r['new_generator_mw']['g'],2);equal(r['total_cost'],23.75)

# Sending end capacity, delivered power, and monetary losses have separate units.
r=checked('lossy_line',['A','B'],[Scenario('s',1,{'A':[0],'B':[1]})],
    [Generator('g','A',2,0,0,10)],[Line('ab','A','B',0,2,4,.1,0)])
equal(r['new_line_mw']['ab'],1/.9);equal(r['total_cost'],14/.9)

# Storage must pay conversion losses and return to initial SOC, including nonzero initial SOC.
r=checked('storage_investment_losses',['A'],[Scenario('s',1,{'A':[0,1]})],
    [Generator('solar','A',2,0,0,0,availability={'s':[1,0]})],
    storage=[Storage('b','A',max_new_power_mw=3,max_new_energy_mwh=3,power_investment_cost=2,
                     energy_investment_cost=3,charge_efficiency=.8,throughput_cost=.01)])
equal(r['new_storage_power_mw']['b'],1.25);equal(r['new_storage_energy_mwh']['b'],1)
equal(r['total_cost'],5.5225);equal(r['scenarios']['s']['soc']['b'],[0,1,0])
no_energy=solve(['A'],[Scenario('s',1,{'A':[1]})],[],storage=[Storage('b','A',2,2,initial_soc_fraction=1)])
assert not no_energy['feasible'];checks.append('cyclic_storage_cannot_supply_free_initial_energy')

# A complete batch may be shifted, but cannot be dropped or moved before arrival.
s=[Scenario('s',1,{'A':[0,0]})]
g=[Generator('solar','A',1,0,0,0,availability={'s':[1,0]}),Generator('firm','A',0,2,10,3,1)]
p=[ComputePool('p','A',[1],[1],0,{'s':[Batch('j',0,2,1)]})]
joint=checked('flexible_task_investment',['A'],s,g,pools=p)
rigid=checked('fixed_task_investment',['A'],s,g,pools=p,fixed_compute={'s':{'p':[0,1]}})
equal(joint['total_cost'],0);equal(rigid['total_cost'],13)
late=[ComputePool('p','A',[1],[1],0,{'s':[Batch('j',1,2,1)]})]
assert not solve(['A'],s,g,pools=late,fixed_compute={'s':{'p':[1,0]}})['feasible']
assert not solve(['A'],s,g,pools=p,fixed_compute={'s':{'p':[0,0]}})['feasible']
checks+=['reject_prearrival_compute','reject_incomplete_work']
results['two_hour_task_case']={'rigid':rigid,'coordinated':joint,'status':'analytic_example_not_empirical_result'}

# Explicit response has later recovery and a positive cost, even at equal task work.
recovery=checked('recovery_with_delay_cost',['A'],s,[Generator('g','A',2,0,0,3)],
    pools=[ComputePool('p','A',[1],[1],0,{'s':[Batch('j',0,2,1,2)]})],fixed_compute={'s':{'p':[0,1]}})
equal(recovery['total_cost'],5);equal(recovery['cost_components']['service_delay'],2)

# Slower mode is chosen only when enough time is available; idle power is always supplied.
r=checked('mode_performance_and_idle',['A'],s,[Generator('g','A',2,0,0,1)],
    pools=[ComputePool('p','A',[.5,1],[.4,1],.1,{'s':[Batch('j',0,2,1)]})])
equal(r['total_cost'],.8)
r=checked('deadline_requires_fast_mode',['A'],s,[Generator('g','A',2,0,0,1)],
    pools=[ComputePool('p','A',[.5,1],[.4,1],.1,{'s':[Batch('j',0,1,1)]})])
equal(r['total_cost'],1.1)

# Expected non-AI shortfall constraint; AI cannot be shed through that variable.
r=checked('weighted_unserved_constraint',['A'],[Scenario('low',.75,{'A':[0]}),Scenario('high',.25,{'A':[2]})],
    [Generator('g','A',1,0,0,0)],expected_unserved_limit_mwh=.25)
equal(r['expected_unserved_mwh'],.25);equal(r['total_cost'],2500)
assert not solve(['A'],[Scenario('s',1,{'A':[2]})],[Generator('g','A',1,0,0,0)])['feasible']
assert not solve(['A'],s,[],pools=p,expected_unserved_limit_mwh=100)['feasible']
checks+=['zero_shortfall_bound_enforced','AI_work_cannot_use_nonAI_shortfall']
r=checked('emissions_cap',['A'],[Scenario('s',1,{'A':[1]})],
    [Generator('dirty','A',1,0,0,1,1),Generator('clean','A',1,0,0,4,0)],emissions_limit_t=.25)
equal(r['total_cost'],3.25);equal(r['expected_emissions_t'],.25)

# Independent scalar capacity oracle: enumerate every breakpoint of a convex
# piecewise-linear screening-curve objective, with shared capacity in two scenarios.
rng=np.random.default_rng(14092026)
for k in range(60):
    loads=rng.uniform(.1,4,(2,4));prob=rng.dirichlet([2,2]);dt=float(rng.choice([.25,.5,1]))
    base_price=float(rng.uniform(1,3));peak_price=float(rng.uniform(5,12));capital=float(rng.uniform(.1,12))
    scenarios=[Scenario(str(i),float(prob[i]),{'A':loads[i]}) for i in range(2)]
    r=checked(f'screening_curve_oracle_{k}',['A'],scenarios,
        [Generator('base','A',0,4,capital,base_price),Generator('peak','A',4,0,0,peak_price)],dt=dt)
    candidates=np.r_[0,loads.ravel(),4]
    oracle=min(capital*x+sum(prob[i]*dt*np.sum(base_price*np.minimum(loads[i],x)+peak_price*np.maximum(loads[i]-x,0)) for i in range(2)) for x in candidates)
    equal(r['total_cost'],oracle)

# Exact unit-job assignment oracle under fixed capacities. Unlike the solver,
# this enumerates feasible schedules and does not assemble a linear program.
for k in range(40):
    T=4;prices=rng.integers(1,20,T);jobs=[]
    for j in range(3):
        start=int(rng.integers(0,T));end=int(rng.integers(start+1,T+1));jobs.append(Batch(str(j),start,end,1))
    options=[range(j.release,j.deadline) for j in jobs]
    costs=[sum(prices[t] for t in a) for a in itertools.product(*options) if len(set(a))==len(a)]
    generators=[Generator(str(t),'A',1,0,0,float(prices[t]),availability={'s':[int(z==t) for z in range(T)]}) for t in range(T)]
    pools=[ComputePool('p','A',[1],[1],0,{'s':jobs})];scenarios=[Scenario('s',1,{'A':[0]*T})]
    if costs:
        r=checked(f'enumerated_task_oracle_{k}',['A'],scenarios,generators,pools=pools);equal(r['total_cost'],min(costs))
    else:
        assert not solve(['A'],scenarios,generators,pools=pools)['feasible'];checks.append(f'enumerated_infeasible_task_oracle_{k}')

# Silent malformed inputs must never become a seemingly valid research result.
invalids=[dict(dt=float('nan')),dict(expected_unserved_limit_mwh=float('inf')),
          dict(emissions_limit_t=-1),dict(fixed_compute={'typo':{'p':[0,0]}})]
for kwargs in invalids:
    try:solve(['A'],s,g,pools=p,**kwargs)
    except ValueError:pass
    else:raise AssertionError(('accepted invalid input',kwargs))
try:solve(['A'],[Scenario('a',.5,{'A':[1]}),Scenario('b',.5,{'A':[1]})],
          [Generator('g','A',1,0,0,0,availability={'a':[1]})])
except ValueError:pass
else:raise AssertionError('incomplete availability silently defaulted')
checks.append('nonfinite_unknown_and_missing_scenario_inputs_rejected')

summary={'status':'joint_LP_mathematical_validation_passed_NOT_calibrated_regional_result',
         'checks':checks,'number_of_checks':len(checks),'independent_capacity_oracle_cases':60,
         'independent_task_assignment_oracle_cases':40,'maximum_independently_reconstructed_power_balance_error_MW':max(max_errors),
         'model_sha256':hashlib.sha256((ROOT/'work/research/models/coupled_grid_compute.py').read_bytes()).hexdigest(),
         'limitations':['transport network rather than AC security constraints','perfect foresight scenario dispatch',
                        'continuous time-sharing rather than validated subhour service execution',
                        'no task migration, checkpoint overhead, unit commitment, outage chronology or calibrated base year',
                        'expected unserved bound is not a complete equal-reliability validation']}
(OUT/'coupled_grid_compute_validation.json').write_text(json.dumps(summary,indent=2))
(OUT/'coupled_grid_compute_analytic_examples.json').write_text(json.dumps(results,indent=2))
print(json.dumps({k:v for k,v in summary.items() if k!='checks'},indent=2))
