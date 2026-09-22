"""Independent enumeration validates interval optima and factorial bounds."""
from pathlib import Path
import sys,json,itertools
import numpy as np
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'work/research/models'))
from gang_policy import best_interval,coordinate_policy,independent_job_bound
rng=np.random.default_rng(20260923);checks=0;gaps=[]

def bill(a,b,prices):
    return sum(max(0.,min(b,t+1)-max(a,t))*v for t,v in enumerate(prices))

for _ in range(120):
    prices=rng.integers(1,6,8).astype(float);a=rng.integers(0,12)/2;b=rng.integers(int(2*a)+1,17)/2;dur=rng.integers(1,7)/2
    fixed=None if rng.random()<.5 else rng.integers(0,17)/2
    options=[(bill(s,s+dur,prices),s) for s in np.arange(a,b-dur+1e-10,.5) if fixed is None or s==fixed]
    actual=best_interval([(a,b)],dur,np.arange(9),prices,fixed)
    if not options:assert actual is None
    else:
        expected=min(options);assert abs(actual[0]-expected[0])<1e-10 and abs(actual[1]-expected[1])<1e-10
    checks+=1
for _ in range(30):
    prices=rng.integers(1,6,5).astype(float);q=np.array([.5,1]);p=np.array([.3,.9]);start=np.arange(3.);plan=np.c_[start,start+1,np.ones(3)];work=np.ones(3);gpu=np.ones(3)
    for am,at in itertools.product([False,True],repeat=2):
        choices=[]
        for i in range(3):
            choices.append([(s,s+1/q[m],m) for m in ([0,1] if am else [1]) for s in (np.arange(0,5-1/q[m]+.1) if at else [start[i]]) if s+1/q[m]<=5])
        opt=float('inf')
        for combo in itertools.product(*choices):
            if any(sum(a<=t<b for a,b,m in combo)>1 for t in np.arange(.5,5,1)):continue
            opt=min(opt,sum(p[m]*bill(a,b,prices) for a,b,m in combo))
        result=coordinate_policy(np.zeros(3),np.full(3,5.),work,gpu,start,plan,np.arange(6.),np.array([0,0,0,1,1.]),q,p,np.arange(6.),prices,am,at)
        x=result['plan'];cost=sum(p[int(m)]*bill(a,b,prices) for a,b,m in x)
        events=sorted(set([0.,5.]+list(x[:,:2].ravel())))
        assert all(sum(a<=(a0+b0)/2<b for a,b,m in x)<=1 for a0,b0 in zip(events[:-1],events[1:]))
        assert all(abs((b-a)*q[int(m)]-1)<1e-10 for a,b,m in x)
        if not at:assert np.array_equal(x[:,0],start)
        if not am:assert (x[:,2]==1).all()
        lb=independent_job_bound(np.zeros(3),np.full(3,5.),work,gpu,start,q,p,np.arange(6.),prices,am,at).sum()
        assert lb<=opt+1e-9<=cost+1e-9
        assert abs(cost-result['incremental_bill'])<1e-9 and cost<=sum(.9*bill(i,i+1,prices) for i in range(3))+1e-9
        gaps.append(cost-opt);checks+=1
# Splitting a low-price block must not change an interval minimum.
a=best_interval([(0,6)],2.5,np.array([0,2,4,6]),np.array([3,1,2]))
b=best_interval([(0,6)],2.5,np.array([0,1,2,3,4,5,6]),np.array([3,3,1,1,2,2]))
assert np.allclose(a,b);checks+=1
report=dict(checks=checks,random_interval_oracles=120,exact_three_job_factorial_oracles=120,max_constructive_gap_to_brute_optimum=max(gaps),
    limitation='Positive gaps are retained and prove that feasible coordinate policies must not be labelled globally optimal.')
out=ROOT/'outputs/research/revision/policy/validation';out.mkdir(parents=True,exist_ok=True);(out/'model_checks.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
