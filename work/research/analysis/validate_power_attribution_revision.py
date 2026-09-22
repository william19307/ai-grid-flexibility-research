"""Analytic component identities and independent small scheduling oracles."""
from pathlib import Path
import sys,json
import numpy as np
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'work/research/models'))
from node_power_mapping import map_gpu_to_node
from sequential_tasks import Job,schedule
from energy_dispatch import energy_earliest_edf

checks=[]
def check(name,value):
    if not value:raise AssertionError(name)
    checks.append(name)

for I in [.25,.41]:
    for g in [0.,.1,.2]:
        for d in [0.,.1]:
            p,m=map_gpu_to_node([.3,.5,1],I,g,d)
            a=m['gpu_share_of_full_node_power']
            check(f'full active identity {I,g,d}',abs(p[-1]-1)<1e-12)
            check(f'idle decomposition identity {I,g,d}',abs(m['non_gpu_idle_share']+a*g-I)<1e-12)
            check(f'mode energy decomposition {I,g,d}',np.allclose(p,[m['non_gpu_active_share']+a*x for x in [.3,.5,1]]))
            check(f'nonnegative increments {I,g,d}',np.min(p)>=I and m['non_gpu_idle_share']>=0)
for params in [([.3,1],.1,.5,0),([.3,1],.4,.1,.6),([.05,1],.4,.1,0)]:
    try:map_gpu_to_node(*params)
    except ValueError:check(f'reject incoherent {params}',True)
    else:raise AssertionError(params)

q=[.5,1.];p=[.45,1.];I=.2
r=energy_earliest_edf([Job('one',0,2,1.)],q,p,2,I)
check('two-hour slow-mode analytic energy',abs(r['energy']-.9)<1e-7)
check('two-hour slow-mode no idle',np.allclose(r['slot_average_power'],[.45,.45],atol=1e-7))
r=energy_earliest_edf([Job('early',0,4,.5),Job('late',2,4,.5)],q,p,4,I)
check('release-gap analytic profile',np.allclose(r['slot_average_power'],[.45,.2,.45,.2],atol=1e-7))
check('release-gap analytic energy',abs(r['energy']-1.3)<1e-7)
r=energy_earliest_edf([Job('tight',0,1,.75)],q,p,1,I)
check('convex mixed-mode analytic energy',abs(r['energy']-.725)<1e-7)
r=energy_earliest_edf([Job('long',0,4,1),Job('urgent',0,2,.5)],q,p,4,I)
check('EDF ordering independent of input list',r['allocations'][0]['job']=='urgent')
check('EDF work conservation',r['baseline_audit']['max_overdue_work']<1e-7)
check('infeasible workload not silently extended',not energy_earliest_edf([Job('bad',0,1,1.5)],q,p,1,I)['feasible'])
r=schedule([Job('x',0,1,1.)],[1.],[1.],1,.2,energy_limit=.9)
check('energy cap does not drop work',not r['feasible'])

OUT=ROOT/'outputs/research/revision/power_attribution';OUT.mkdir(parents=True,exist_ok=True)
(OUT/'analytic_validation.json').write_text(json.dumps(dict(passed=len(checks),checks=checks,scope='mathematical identities and scheduling oracles; no empirical node calibration'),indent=2)+'\n')
print(f'{len(checks)} power and attribution checks passed')
