from pathlib import Path
import sys,json,time
import numpy as np
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'work/research/models'))
from gang_policy import best_interval as slow
from gang_policy_fast import best_interval as fast
rng=np.random.default_rng(98211);checks=0;maxerr=0
for _ in range(1000):
    price=rng.integers(0,8,48).astype(float)/3;edges=np.arange(49.)
    # Include fragmented blocks, exact ties, fractional lengths and block endpoints.
    es=np.sort(rng.uniform(0,48,30));blocks=list(zip(es[::2],es[1::2]));duration=rng.uniform(.001,4)
    fixed=None if rng.random()<.7 else float(rng.choice(es))
    a=slow(blocks,duration,edges,price,fixed);b=fast(blocks,duration,edges,price,fixed)
    assert (a is None)==(b is None)
    if a is not None:
        err=float(np.max(abs(np.array(a)-b)));maxerr=max(maxerr,err);assert np.array_equal(a,b),(a,b)
    checks+=1
for eps in [0.,1e-13,1e-12,1e-11]:
    blocks=[(0.,1.),(2.,3.)];price=np.array([1.,7.,1.+eps,7.])
    for d in [.5,1.,1.+eps]:
        a=slow(blocks,d,np.arange(5.),price);b=fast(blocks,d,np.arange(5.),price);assert a==b,(a,b);checks+=1
out=ROOT/'outputs/research/revision/policy/performance';out.mkdir(exist_ok=True)
r=dict(interval_equivalence_checks=checks,maximum_difference=maxerr,bitwise_identical_on_all_nonempty_checks=True)
(out/'fast_interval_checks.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
