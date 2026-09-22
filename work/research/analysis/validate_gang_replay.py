"""Independent time-line checks and LP validation of separable energy bounds."""
from pathlib import Path
import sys,json
import numpy as np
from scipy.optimize import linprog
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'work/research/models'))
from gang_replay import schedule_gangs,individual_energy_bound
checks=[]
def check(name,value):
    if not value:raise AssertionError(name)
    checks.append(name)
r=schedule_gangs([0],[2],[1],[2],[1],[0,1,2],[1,0],[.5,1],[.4,1])
check('nonpreemptive slow job uses earlier free capacity',abs(r['incremental_energy']-.8)<1e-9 and r['schedule'][0][1:3]==(0.,2.))
r=schedule_gangs([0,0],[2,2],[0,.5],[.5,1],[2,2],[0,.5,1,2],[1,1,3],[.5,1],[.4,1])
check('whole GPU gangs fit without overlap in three-GPU pool',abs(r['incremental_energy']-1.6)<1e-9)
try:schedule_gangs([0,0],[1,1],[0,.75],[.75,1.5],[2,2],[0,.75,1.5],[1,1],[1],[1])
except ValueError:check('infeasible observed completion is rejected',True)
else:raise AssertionError('Invalid baseline accepted')
rng=np.random.default_rng(734)
for case in range(60):
    n=int(rng.integers(1,7));duration=rng.integers(1,5,n)/2;gpus=rng.integers(1,4,n)
    begin=np.r_[0,np.cumsum(duration)[:-1]];end=np.cumsum(duration);release=begin*rng.random(n)
    deadline=end+rng.integers(0,4,n);horizon=float(max(deadline.max(),end[-1]))
    edges=np.unique(np.r_[0,begin,end,release,deadline,horizon]);mid=(edges[1:]+edges[:-1])/2
    free=np.array([4-sum(g for a,b,g in zip(begin,end,gpus) if a<=t<b) for t in mid],float)
    q=np.array([.5,.8,1.]);p=np.array([.32,.6,.9])
    r=schedule_gangs(release,deadline,begin,end,gpus,edges,free,q,p)
    plan=r['schedule'];work=gpus*duration
    check(f'work and gang size unchanged {case}',all(abs((b-a)*gpus[i]*q[m]-work[i])<1e-8 for i,a,b,m in plan))
    check(f'fixed release and deadline {case}',all(a>=release[i]-1e-9 and b<=deadline[i]+1e-9 for i,a,b,m in plan))
    cuts=sorted(set([0.,horizon]+[a for _,a,_,_ in plan]+[b for _,_,b,_ in plan]))
    peak=max(sum(gpus[i] for i,a,b,m in plan if a<=(l+u)/2<b) for l,u in zip(cuts[:-1],cuts[1:]))
    check(f'independent whole-gang capacity {case}',peak<=4)
    lower=0.
    for i in range(n):
        fit=linprog(p,A_eq=[q],b_eq=[work[i]],A_ub=[np.ones(3)],b_ub=[gpus[i]*(deadline[i]-release[i])],bounds=(0,None),method='highs')
        assert fit.success;lower+=fit.fun
    check(f'convex bound matches independent per-job LP {case}',abs(lower-r['individual_lower_bound'])<1e-7)
    check(f'energy bracket contains feasible construction {case}',lower<=r['incremental_energy']+1e-7<=.9*work.sum()+1e-7)
out=ROOT/'outputs/research/revision/replay'
(out/'gang_validation.json').write_text(json.dumps(dict(passed=len(checks),checks=checks,random_cases=60,
    scope='Feasible non-preemptive gang construction in an aggregate pool; no node topology or measured node power'),indent=2)+'\n')
print(f'{len(checks)} gang scheduling and energy-bound checks passed')
