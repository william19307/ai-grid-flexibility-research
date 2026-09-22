"""Independent water/electricity checks and dynamic-programming hydro oracles."""
from pathlib import Path
import sys,json,hashlib,argparse
import numpy as np
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'work/research/models'))
from coupled_grid_compute import Generator,Reservoir,Scenario,ComputePool,Batch,solve
parser=argparse.ArgumentParser();parser.add_argument('--output-dir',type=Path,default=ROOT/'outputs/research/tables');args=parser.parse_args()
OUT=args.output_dir;OUT.mkdir(parents=True,exist_ok=True)
checks=[];water_errors=[];power_errors=[]

def close(x,y):assert np.allclose(x,y,rtol=1e-8,atol=1e-8),(x,y)

def verify(name,nodes,scenarios,generators,reservoirs,pools=(),dt=1,**kwargs):
    r=solve(nodes,scenarios,generators,pools=pools,reservoirs=reservoirs,dt=dt,**kwargs)
    assert r['feasible'],(name,r)
    for s in scenarios:
        out=r['scenarios'][s.name];balance={n:-np.array(s.load_mw[n],float) for n in nodes}
        for n in nodes:balance[n]+=np.array(out['unserved'][n])
        for g in generators:balance[g.node]+=np.array(out['generation'][g.name])
        for p in pools:balance[p.node]-=np.array(out['compute_power_mw'][p.name])
        system_inflow=0.;outlet_release=0.;storage_change=0.
        for h in reservoirs:
            g=np.array(out['hydro_generation'][h.name]);sp=np.array(out['hydro_spillage_hm3_per_hour'][h.name]);v=np.array(out['hydro_volume_hm3'][h.name])
            # Reconstruct in raw m3, independently of the solver's hm3 rows.
            local=np.array(h.inflow_hm3_per_hour[s.name])*1e6;incoming=np.zeros(len(g))
            for u in reservoirs:
                if u.downstream==h.name:
                    incoming+=np.array(out['hydro_generation'][u.name])*u.specific_water_m3_per_mwh
                    incoming+=np.array(out['hydro_spillage_hm3_per_hour'][u.name])*1e6
            release=g*h.specific_water_m3_per_mwh+sp*1e6
            error=float(np.max(np.abs(np.diff(v)*1e6-dt*(local+incoming-release))))
            assert error<1e-6,(name,h.name,error);water_errors.append(error)
            close(v[0],h.initial_volume_hm3);close(v[-1],v[0])
            assert v.min()>=-1e-8 and v.max()<=h.usable_volume_hm3+1e-8
            assert g.min()>=-1e-8 and (g<=h.turbine_mw*np.array(h.availability.get(s.name,np.ones(len(g))))+1e-8).all()
            assert sp.min()>=-1e-8
            balance[h.node]+=g;system_inflow+=local.sum()*dt;storage_change+=(v[-1]-v[0])*1e6
            if h.downstream is None:outlet_release+=release.sum()*dt
        close(system_inflow,outlet_release+storage_change)
        for b in balance.values():
            error=float(np.max(np.abs(b)));assert error<1e-7;power_errors.append(error)
    checks.append(name);return r

s=[Scenario('s',1,{'A':[1],'B':[.25]})]
rs=[Reservoir('upper','A',2,0,0,1000,{'s':[.001]},'lower'),
    Reservoir('lower','B',2,0,0,4000,{'s':[0]})]
r=verify('cascade_conserves_water_not_copied_energy',['A','B'],s,[],rs)
close(r['scenarios']['s']['hydro_generation']['lower'],[.25])
assert not solve(['A','B'],[Scenario('s',1,{'A':[1],'B':[1]})],[],reservoirs=rs)['feasible']
checks.append('reject_energy_copy_that_would_create_water')

# Upstream turbine need not run for spilled water to reach a downstream turbine.
rs=[Reservoir('upper','A',1,0,0,1000,{'s':[.004]},'lower'),Reservoir('lower','B',1,0,0,4000,{'s':[0]})]
r=verify('routed_upstream_spillage',['A','B'],[Scenario('s',1,{'A':[0],'B':[1]})],[],rs)
close(r['scenarios']['s']['hydro_spillage_hm3_per_hour']['upper'],[.004])

r=verify('reservoir_shifts_water_across_hours',['A'],[Scenario('s',1,{'A':[0,1]})],[],
    [Reservoir('h','A',1,.001,0,1000,{'s':[.001,0]})])
close(r['scenarios']['s']['hydro_volume_hm3']['h'],[0,.001,0])
assert not solve(['A'],[Scenario('s',1,{'A':[1]})],[],reservoirs=[Reservoir('h','A',1,.001,.001,1000,{'s':[0]})])['feasible']
checks.append('cannot_spend_initial_reservoir_stock_without_replenishment')

r=verify('tributaries_and_half_hour_units',['A','B','C'],[Scenario('s',1,{'A':[1],'B':[1],'C':[1.5]})],[],
    [Reservoir('a','A',1,0,0,1000,{'s':[.001]},'c'),
     Reservoir('b','B',1,0,0,2000,{'s':[.002]},'c'),
     Reservoir('c','C',2,0,0,2000,{'s':[0]})],dt=.5)

rs=[Reservoir('h','A',1,.001,0,1000,{'s':[.001,0]},marginal_cost=2)]
p=[ComputePool('p','A',[1],[1],0,{'s':[Batch('j',0,2,1)]})]
r=verify('task_recovery_and_reservoir_coupling',['A'],[Scenario('s',1,{'A':[0,0]})],[],rs,pools=p,fixed_compute={'s':{'p':[0,1]}})
close(r['total_cost'],2);close(r['scenarios']['s']['completed_work']['p']['j'],1)

r=verify('new_turbine_not_available_before_commissioning',['A'],[Scenario('s',1,{'A':[0,1]})],[],
    [Reservoir('h','A',1,.001,0,1000,{'s':[.001,0]},availability={'s':[0,1]})])
close(r['scenarios']['s']['hydro_generation']['h'],[0,1])

# Dynamic program over integer storage and releases. Its implementation shares
# neither variables nor constraint assembly with the linear program.
rng=np.random.default_rng(20260914)
for case in range(60):
    T=5;inflow=rng.integers(0,3,T);load=rng.integers(0,4,T);price=rng.integers(1,20,T)
    states={1:0.}
    for t in range(T):
        nxt={}
        for level,cost in states.items():
            available=level+int(inflow[t])
            for gen in range(min(2,int(load[t]),available)+1):
                for end in range(min(3,available-gen)+1):
                    candidate=cost+(load[t]-gen)*price[t]
                    nxt[end]=min(nxt.get(end,float('inf')),candidate)
        states=nxt
    generators=[Generator(str(t),'A',4,0,0,float(price[t]),availability={'s':[int(i==t) for i in range(T)]}) for t in range(T)]
    res=[Reservoir('h','A',2,.003,.001,1000,{'s':inflow/1000})]
    if 1 not in states:
        assert not solve(['A'],[Scenario('s',1,{'A':load})],generators,reservoirs=res)['feasible']
        checks.append(f'dynamic_program_infeasible_{case}')
    else:
        r=verify(f'dynamic_program_{case}',['A'],[Scenario('s',1,{'A':load})],generators,res)
        close(r['total_cost'],states[1])

for label,res in [
 ('initial_above_usable',[Reservoir('h','A',1,1,2,1000,{'s':[0]})]),
 ('negative_local_inflow',[Reservoir('h','A',1,1,0,1000,{'s':[-1]})]),
 ('missing_scenario_inflow',[Reservoir('h','A',1,1,0,1000,{})]),
 ('self_cycle',[Reservoir('h','A',1,1,0,1000,{'s':[0]},'h')]),
 ('two_dam_cycle',[Reservoir('h','A',1,1,0,1000,{'s':[0]},'k'),Reservoir('k','A',1,1,0,1000,{'s':[0]},'h')]),
 ('unknown_downstream',[Reservoir('h','A',1,1,0,1000,{'s':[0]},'absent')])]:
    try:solve(['A'],[Scenario('s',1,{'A':[0]})],[],reservoirs=res)
    except ValueError:checks.append('reject_'+label)
    else:raise AssertionError(label)

result={'status':'water_conserving_reservoir_extension_mathematically_verified_NOT_empirical_system_result',
        'checks':checks,'number_of_checks':len(checks),'independent_dynamic_program_cases':60,
        'maximum_independent_water_balance_error_m3':max(water_errors),
        'maximum_independent_electric_balance_error_MW':max(power_errors),
        'model_sha256':hashlib.sha256((ROOT/'work/research/models/coupled_grid_compute.py').read_bytes()).hexdigest(),
        'limitations':['zero travel-time routing','fixed specific-water consumption; no head-dependent efficiency or evaporation',
                       'inflows must be incremental, not catchment totals','fixed cyclic initial usable storage must be justified',
                       'no empirical dam calibration or matched 2020 hydro-meteorology yet']}
(OUT/'reservoir_coupling_validation.json').write_text(json.dumps(result,indent=2))
print(json.dumps({k:v for k,v in result.items() if k!='checks'},indent=2))
