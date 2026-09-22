"""Independent analytic counterexamples for pumped-storage classification."""
from pathlib import Path
import sys,json
import numpy as np
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'work/research/models'))
from coupled_grid_compute import Generator,Scenario,solve
from hydro_fleet import split_hydro,pumped_storage

checks=[]
def check(name,condition):
    if not condition:raise AssertionError(name)
    checks.append(name)

check('Jiangsu has no non-pumped hydro in selected GEM inventory',split_hydro('Jiangsu',3950)['non_pumped_mw']==0)
try:split_hydro('Jiangsu',4000)
except ValueError:check('inconsistent capacity rejected',True)
else:raise AssertionError('mismatch accepted')

for eta in [.6,.75,.9,1.]:
    b=pumped_storage('phs','N',2.,1.,eta)
    # No generation source: a cyclic store cannot supply net positive demand.
    no_source=solve(['N'],[Scenario('x',1.,{'N':[0.,1.]})],[],storage=[b],expected_unserved_limit_mwh=0.)
    check(f'no free energy eta={eta}',not no_source['feasible'])
    # Cheap first-hour source and expensive second-hour fallback. To deliver
    # 1 MWh in hour 2 requires exactly 1/eta MWh purchased in hour 1.
    g=[Generator('cheap','N',2.,0,0,10.,availability={'x':[1.,0.]}),
       Generator('expensive','N',2.,0,0,100.,availability={'x':[0.,1.]})]
    b.initial_soc_fraction=0.
    r=solve(['N'],[Scenario('x',1.,{'N':[0.,1.]})],g,storage=[b],expected_unserved_limit_mwh=0.)
    check(f'feasible transfer eta={eta}',r['feasible'])
    s=r['scenarios']['x']
    check(f'analytic charge eta={eta}',np.allclose(s['charge']['phs'],[1/eta,0],atol=1e-7))
    check(f'analytic discharge eta={eta}',np.allclose(s['discharge']['phs'],[0,1],atol=1e-7))
    check(f'analytic cost eta={eta}',abs(r['total_cost']-(10/eta+.001*(1/eta+1)))<1e-7)
    check(f'no simultaneous operation eta={eta}',s['simultaneous_storage_slots']['phs']==0)

out=ROOT/'outputs/research/revision/hydro/hydro_physics_validation.json'
out.write_text(json.dumps(dict(passed=len(checks),checks=checks,scope='analytic storage tests and inventory consistency; not provincial empirical validation'),indent=2)+'\n')
print(f'{len(checks)} hydro revision checks passed')
