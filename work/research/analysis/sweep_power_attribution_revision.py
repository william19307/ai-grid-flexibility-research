"""Paired workload/province diagnostics; preserve failures and verify resumed runs."""
from pathlib import Path
import sys, subprocess, json, hashlib, csv
from concurrent.futures import ThreadPoolExecutor

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'outputs/research/revision/power_attribution'


def tasks():
    with (ROOT/'outputs/research/tables/dvfs_measured_and_derived.csv').open() as f:
        workloads=sorted({row['Workload'] for row in csv.DictReader(f)})
    cases=[]
    for province,share in [('Jiangsu',.2),('Gansu',.1),('Guizhou',.1)]:
        for workload in workloads:
            for mapping in ['legacy','component']:
                cases.append((province,share,workload,mapping,.41,.1,0.))
        for idle,gpu,overhead in [(.41,0.,0.),(.41,.2,0.),(.41,.1,.1),(.25,.1,0.)]:
            cases.append((province,share,'ft_llama_8b_dolly','component',idle,gpu,overhead))
    return cases


def execute(case):
    province,share,workload,mapping,idle,gpu,overhead=case
    name=f'{province}_ai{share:g}_{workload}_{mapping}_I{idle:g}_g{gpu:g}_d{overhead:g}'
    folder=OUT/'runs'/name
    row=dict(name=name,case=case)
    if folder.exists():
        try:
            manifest=json.loads((folder/'run_manifest.json').read_text())
            assert json.loads((folder/'complete.json').read_text())['all_scenarios_feasible']
            for group in ['source_sha256','input_sha256']:
                for path,digest in manifest[group].items():
                    assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==digest,path
            row.update(exit_code=0,resumed_verified=True)
        except Exception as exc:
            row.update(exit_code=2,resumed_verified=False,error=repr(exc))
        return row
    args=['--province',province,'--ai-share',str(share),'--workload',workload,
          '--mapping',mapping,'--node-idle',str(idle),'--gpu-idle',str(gpu),
          '--active-overhead',str(overhead)]
    log=OUT/'logs'/f'{name}.txt';log.parent.mkdir(exist_ok=True)
    with log.open('w') as f:
        result=subprocess.run([sys.executable,str(ROOT/'work/research/analysis/run_power_attribution_revision.py'),*args],
                              cwd=ROOT,stdout=f,stderr=subprocess.STDOUT)
    row.update(exit_code=result.returncode,log=str(log.relative_to(ROOT)))
    if result.returncode:
        (folder/'failure.json').write_text(json.dumps(row,indent=2)+'\n')
    print(json.dumps(row),flush=True)
    return row


if __name__=='__main__':
    OUT.mkdir(exist_ok=True)
    with ThreadPoolExecutor(max_workers=3) as pool:results=list(pool.map(execute,tasks()))
    (OUT/'sweep_process_results.json').write_text(json.dumps(results,indent=2)+'\n')
    if any(row['exit_code'] for row in results):raise SystemExit(1)
