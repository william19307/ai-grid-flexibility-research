"""Independent exhaustive schedules, interval integrals and legacy input match."""
from pathlib import Path
from functools import lru_cache
import sys,ast,json,hashlib
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'work/research/models'))
from sequential_tasks import Job,schedule
from strict_workload import demand_bound,edf_replay,sample_fixed_windows
from trace_occupancy import integrate_occupancy

checks=[]
def check(name,value):
    if not value:raise AssertionError(name)
    checks.append(name)

def exhaustive(jobs,T):
    units=[]
    for j in sorted(jobs,key=lambda j:(j.deadline-j.release,j.deadline)):
        units.extend([(j.release,j.deadline)]*int(round(j.work*2)))
    @lru_cache(None)
    def place(i,capacities):
        if i==len(units):return True
        r,d=units[i]
        for t in range(r,d):
            if capacities[t]:
                left=list(capacities);left[t]-=1
                if place(i+1,tuple(left)):return True
        return False
    return place(0,(2,)*T)

rng=np.random.default_rng(20260922)
for case in range(100):
    jobs=[];T=4
    for i in range(int(rng.integers(1,5))):
        r=int(rng.integers(0,T));d=int(rng.integers(r+1,T+1))
        jobs.append(Job(str(i),r,d,float(rng.integers(1,5))*.5))
    truth=exhaustive(jobs,T)
    check(f'interval against exhaustive {case}',demand_bound(jobs)['feasible']==truth)
    check(f'EDF against exhaustive {case}',edf_replay(jobs,T)['feasible']==truth)
    check(f'LP against exhaustive {case}',schedule(jobs,[1.],[1.],T,0.)['feasible']==truth)

for case in range(30):
    starts=rng.uniform(-2,6,12);ends=starts+rng.uniform(0,4,12);weights=rng.integers(0,9,12)
    edges=np.array([0.,.25,1.5,3.,5.]);actual=integrate_occupancy(starts,ends,weights,edges)
    expected=[];peaks=[]
    for a,b in zip(edges[:-1],edges[1:]):
        expected.append(sum(max(0,min(e,b)-max(s,a))*w for s,e,w in zip(starts,ends,weights)))
        cuts=sorted(set([a,b]+[float(v) for v in np.r_[starts,ends] if a<v<b]))
        peaks.append(max(sum(w for s,e,w in zip(starts,ends,weights) if s<=(l+r)/2<e) for l,r in zip(cuts[:-1],cuts[1:])))
    check(f'exact integral pairwise oracle {case}',np.allclose(actual['resource_seconds'],expected,atol=1e-12))
    check(f'exact peaks midpoint oracle {case}',np.allclose(actual['peak_resources'],peaks,atol=1e-12))
actual=integrate_occupancy([0,1,1],[1,2,1],[5,7,99],[0,1,2])
check('half-open simultaneous boundary no false peak',np.array_equal(actual['peak_resources'],[5,7]))
check('zero-length interval carries no work',np.array_equal(actual['resource_seconds'],[5,7]))

# Extract the unchanged historical function only up to its feasibility guard.
# This compares with the authoritative input construction, not a copied oracle.
path=ROOT/'work/research/analysis/run_regional_2030_s0_s3.py'
tree=ast.parse(path.read_text());fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='helios_queue_jobs')
cut=next(i for i,n in enumerate(fn.body) if isinstance(n,ast.For) and isinstance(n.target,ast.Name) and n.target.id=='it')
fn.body=fn.body[:cut]+[ast.Return(value=ast.Name(id='items',ctx=ast.Load()))]
module=ast.fix_missing_locations(ast.Module(body=[fn],type_ignores=[]))
namespace=dict(ROOT=ROOT,np=np,pd=pd)
exec(compile(module,str(path),'exec'),namespace)
for start in [288,2472,4656,6840]:
    for slack in [6.,24.]:
        old=sorted(namespace['helios_queue_jobs'](168,.7,start%24,1.,slack,start))
        jobs,T,meta=sample_fixed_windows(168,.7,start%24,1.,slack,start,'historical_clip')
        new=[(j.release,j.deadline,j.work) for j in jobs]
        check(f'original pre-guard tasks exactly matched {start}/{slack}',np.allclose(old,new,atol=1e-12,rtol=1e-12))
        full,_,full_meta=sample_fixed_windows(168,.7,start%24,1.,slack,start,'full_tail')
        check(f'full tail conserves ex ante target {start}/{slack}',abs(sum(j.work for j in full)-117.6)<1e-10)
        check(f'boundary variants use same sampled jobs {start}/{slack}',full_meta['sampled_jobs']==meta['sampled_jobs'] and full_meta['raw_sampled_gpu_hours']==meta['raw_sampled_gpu_hours'])
out=ROOT/'outputs/research/revision/service';out.mkdir(parents=True,exist_ok=True)
report=dict(passed=len(checks),checks=checks,exhaustive_random_cases=100,independent_interval_integration_cases=30,
            legacy_source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
            limitations='Mathematical and input-construction verification; not observed deadlines or energy calibration.')
(out/'analytic_validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(f'{len(checks)} strict service and chronological integration checks passed')
