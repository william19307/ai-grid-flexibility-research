"""Analytic parallelism bounds and independent half-GPU-hour assignment oracle."""
from pathlib import Path
from functools import lru_cache
import sys,json
import numpy as np
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'work/research/models'))
from chronological_replay import ReplayJob,replay

checks=[]
def check(name,value):
    if not value:raise AssertionError(name)
    checks.append(name)

r=replay([ReplayJob('slow',0,2,2,2)],[0,1,2],[2,2],[.5,1],[.4,1])
check('analytic slow mode with parallelism limit',r['feasible'] and abs(r['incremental_energy']-1.6)<1e-7)
r=replay([ReplayJob('short',0,1,3,2)],[0,1],[100],[1],[1])
check('extra pool capacity cannot violate job GPU cap',r['feasible'] is False)
r=replay([ReplayJob('mixed',0,1,.75,1)],[0,1],[1],[.5,1],[.4,1])
check('analytic time sharing at fixed job cap',r['feasible'] and abs(r['incremental_energy']-.7)<1e-7)
r=replay([ReplayJob('blocked',0,2,2,2)],[0,1,2],[0,2],[.5,1],[.4,1])
check('background capacity forces fast last interval',r['feasible'] and abs(r['incremental_energy']-2)<1e-7)
r=replay([ReplayJob('partial',.25,.75,.5,1)],[0,.25,.75,1],[1,1,1],[.5,1],[.4,1])
check('subhour release deadline exact, not rounded',r['feasible'] and abs(r['incremental_energy']-.5)<1e-7)
check('tight job eliminated exactly',r.get('forced_full_speed_jobs')==1 and r['variables']==0)
r=replay([ReplayJob('a',0,1,1,1),ReplayJob('b',0,1,1,1)],[0,1],[1],[1],[1])
check('forced jobs still share pool capacity',r['feasible'] is False)
# This known gap must remain visible: two 2-GPU gangs each need 0.75h;
# a 3-GPU machine cannot overlap them, but the fractional relaxation can.
r=replay([ReplayJob('a',0,1,1.5,2),ReplayJob('b',0,1,1.5,2)],[0,1],[3],[1],[1])
check('documented gang scheduling relaxation gap',r['feasible'] and 1.5/2+1.5/2>1)


def oracle(jobs,capacity):
    units=[];T=len(capacity)
    for i,j in enumerate(jobs):units.extend([(i,int(j.release_h),int(j.deadline_h))]*int(round(j.work_gpu_h*2)))
    @lru_cache(None)
    def visit(index,remaining,job_slots):
        if index==len(units):return True
        i,r,d=units[index]
        for t in range(r,d):
            if remaining[t]>0 and job_slots[i*T+t]>0:
                cap=list(remaining);cap[t]-=1;own=list(job_slots);own[i*T+t]-=1
                if visit(index+1,tuple(cap),tuple(own)):return True
        return False
    return visit(0,tuple(int(c*2) for c in capacity),tuple(int(j.max_gpus*2) for j in jobs for _ in range(T)))

rng=np.random.default_rng(722)
for case in range(50):
    jobs=[];T=3;cap=rng.integers(0,4,T)
    for i in range(int(rng.integers(1,4))):
        left=int(rng.integers(0,T));right=int(rng.integers(left+1,T+1))
        jobs.append(ReplayJob(str(i),left,right,float(rng.integers(1,6))*.5,float(rng.integers(1,3))))
    expected=oracle(jobs,cap)
    r=replay(jobs,np.arange(T+1),cap,[1.],[1.])
    check(f'independent half-unit exhaustive case {case}',r['feasible']==expected)
    if expected:check(f'full work retained {case}',abs(r['incremental_energy']-sum(j.work_gpu_h for j in jobs))<1e-7)

out=ROOT/'outputs/research/revision/replay';out.mkdir(parents=True,exist_ok=True)
(out/'analytic_validation.json').write_text(json.dumps(dict(passed=len(checks),checks=checks,exhaustive_cases=50,
    gang_scheduling_gap_explicit=True,scope='Exact fractional relaxation only, not deployed gang scheduler'),indent=2)+'\n')
print(f'{len(checks)} replay checks passed; gang gap retained explicitly')
