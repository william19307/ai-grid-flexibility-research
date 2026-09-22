"""Bounded paired counterfactual experiment; no output overwrites."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import json,subprocess,sys
ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'outputs/research/revision/counterfactual'
def execute(case):
    province,share,policy=case
    name=f'{province}_ai{share:g}_{policy}'
    log=OUT/'logs'/f'{name}.txt';log.parent.mkdir(parents=True,exist_ok=True)
    folder=OUT/'runs'/name
    if folder.exists():return dict(name=name,exit_code=2,error='Existing output retained; use fresh experiment folder')
    with log.open('w') as f:
        result=subprocess.run([sys.executable,str(ROOT/'work/research/analysis/run_counterfactual_revision.py'),
                               '--province',province,'--ai-share',str(share),'--policy',policy],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT)
    row=dict(name=name,exit_code=result.returncode,log=str(log.relative_to(ROOT)))
    if result.returncode:(folder/'failure.json').write_text(json.dumps(row,indent=2)+'\n')
    print(json.dumps(row),flush=True);return row
if __name__=='__main__':
    cases=[(p,a,c) for p in ['Gansu','Guizhou','Jiangsu'] for a in [.01,.1,.2]
           for c in ['legacy','independent_reference','dispatch_relaxation']]
    with ThreadPoolExecutor(max_workers=3) as pool:results=list(pool.map(execute,cases))
    (OUT/'sweep_process_results.json').write_text(json.dumps(results,indent=2)+'\n')
    if any(r['exit_code'] for r in results):raise SystemExit(1)
