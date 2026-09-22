"""Independent two-slot reference oracle and no-mutation checks."""
from pathlib import Path
import sys,json
import numpy as np
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'work/research/models'))
from coupled_grid_compute import Generator,Scenario,solve
from counterfactual_coal import coal_boundary

checks=[]
def check(name,value):
    if not value:raise AssertionError(name)
    checks.append(name)

scenario=[Scenario('test',1.,{'P':[50.,60.]})]
for ai_dependent_cap in [60.,90.,100.]:
    coal=Generator('coal','P',100.,0.,0.,1.,availability={'test':[ai_dependent_cap/100]*2},min_output_fraction=.4)
    nuclear=Generator('nuclear','P',20.,0.,0.,0.,availability={'test':[.5,.5]})
    gens=[coal,nuclear]
    fixed,audit=coal_boundary(gens,scenario,'P','independent_reference',False)
    # Max native residual = 60 - 20*0.5 = 50; 50 / 0.85 committed.
    check(f'native-only analytic commitment {ai_dependent_cap}',np.allclose(fixed[0].availability['test'],50/.85/100))
    r=solve(['P'],scenario,fixed)
    check(f'analytic independent operating cost {ai_dependent_cap}',r['feasible'] and abs(r['total_cost']-90.)<1e-8)
    check(f'no mutation of input {ai_dependent_cap}',coal.availability['test']==[ai_dependent_cap/100]*2 and coal.min_output_fraction==.4)
    with_ai,_=coal_boundary(gens,scenario,'P','independent_reference',True)
    check(f'AI-side unchanged {ai_dependent_cap}',with_ai[0] is coal)
    relaxed,_=coal_boundary(gens,scenario,'P','dispatch_relaxation',True)
    check(f'full available dispatch relaxation {ai_dependent_cap}',np.allclose(relaxed[0].availability['test'],1) and relaxed[0].min_output_fraction==0)
    check(f'other assets unchanged {ai_dependent_cap}',relaxed[1] is nuclear)
    legacy,_=coal_boundary(gens,scenario,'P','legacy',False)
    check(f'legacy reference unchanged {ai_dependent_cap}',legacy[0] is coal)
zero=[Generator('coal','P',0.,0.,0.,1.,availability={'test':[0.,0.]})]
result,audit=coal_boundary(zero,scenario,'P','independent_reference',False)
check('zero coal does not divide by zero',np.allclose(result[0].availability['test'],0.))
try:coal_boundary(zero,scenario,'P','unknown',False)
except ValueError:check('invalid policy rejected',True)
else:raise AssertionError('invalid policy accepted')
out=ROOT/'outputs/research/revision/counterfactual';out.mkdir(parents=True,exist_ok=True)
(out/'analytic_validation.json').write_text(json.dumps(dict(passed=len(checks),checks=checks,scope='Reference independence and dispatch-boundary identities; not thermal commitment validation'),indent=2)+'\n')
print(f'{len(checks)} counterfactual checks passed')
