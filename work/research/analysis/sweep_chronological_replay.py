"""Prespecified four-cluster/three-slack pilot; all terminal outcomes retained."""
from pathlib import Path
import json,sys,subprocess,time
ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'outputs/research/revision/replay'
if __name__=='__main__':
    cases=[dict(cluster=c,start='2020-04-06',slack=s) for c in ['Earth','Venus','Saturn','Uranus'] for s in [0,6,24]]
    spec=OUT/'pilot_specification.json'
    if spec.exists():raise FileExistsError('Prespecified pilot already exists')
    spec.write_text(json.dumps(dict(written_unix=time.time(),cases=cases,max_variables=5000000,time_limit_seconds=120,
        inclusion='First complete Monday-start week in public capacity calendar; four clusters; no selection on savings or feasibility.',
        future_scope='Pilot only; other weeks, workload curves and deployable gang scheduling remain required.'),indent=2)+'\n')
    rows=[]
    for case in cases:
        name=f"{case['cluster']}_{case['start']}_slack{case['slack']}_pilot"
        log=OUT/'logs'/f'{name}.txt';log.parent.mkdir(exist_ok=True)
        with log.open('w') as f:
            run=subprocess.run([sys.executable,str(ROOT/'work/research/analysis/run_chronological_replay_revision.py'),
                '--cluster',case['cluster'],'--start',case['start'],'--slack',str(case['slack']),'--run-label','pilot'],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT)
        folder=OUT/'runs'/name
        terminal=json.loads((folder/'terminal.json').read_text()) if (folder/'terminal.json').exists() else dict(status='process_error',feasible=None)
        row=dict(name=name,exit_code=run.returncode,**terminal,log=str(log.relative_to(ROOT)))
        rows.append(row);(OUT/'pilot_process_results.json').write_text(json.dumps(rows,indent=2)+'\n')
        print(json.dumps(row),flush=True)
    if any(r['exit_code'] for r in rows):raise SystemExit(1)
