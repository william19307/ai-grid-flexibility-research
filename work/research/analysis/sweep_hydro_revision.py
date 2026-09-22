"""Small paired sweep with bounded local concurrency and retained failure logs."""
from pathlib import Path
import sys,subprocess,json
from concurrent.futures import ThreadPoolExecutor

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'outputs/research/revision/hydro'
tasks=[]
for province in ['Gansu','Guizhou']:
    for treatment in ['legacy','split_pumped_storage','remove_pumped_storage']:
        tasks.append(['--province',province,'--ai-share','.1','--treatment',treatment])
for duration in ['4','12']:
    tasks.append(['--treatment','split_pumped_storage','--duration',duration])
for treatment in ['legacy','split_pumped_storage']:
    tasks.append(['--treatment',treatment,'--neighbours'])

def execute(item):
    name='_'.join(item).replace('--','').replace('/','_')
    log=OUT/'logs'/f'{name}.txt';log.parent.mkdir(exist_ok=True)
    with log.open('w') as f:
        r=subprocess.run([sys.executable,str(ROOT/'work/research/analysis/run_hydro_revision.py'),*item],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT)
    row=dict(arguments=item,exit_code=r.returncode,log=str(log.relative_to(ROOT)))
    print(json.dumps(row),flush=True)
    return row

if __name__=='__main__':
    with ThreadPoolExecutor(max_workers=3) as pool:results=list(pool.map(execute,tasks))
    (OUT/'sweep_process_results.json').write_text(json.dumps(results,indent=2)+'\n')
    if any(r['exit_code'] for r in results):raise SystemExit(1)
