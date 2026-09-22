"""Retry only confirmed terminal clock-conversion errors; keep original attempts."""
from pathlib import Path
import sys,json,subprocess
ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'outputs/research/revision/replay'
if __name__=='__main__':
    source=OUT/'pilot_process_results.json';prior=json.loads(source.read_text())
    if len(prior)!=12:raise RuntimeError('Original pilot not terminal')
    corrected=[]
    for row in prior:
        if row['exit_code']==0:corrected.append(row);continue
        log=(ROOT/row['log']).read_text()
        if "ValueError: Invalid time data" not in log:raise RuntimeError('Unexpected error requires separate diagnosis')
        a=json.loads((OUT/'runs'/row['name']/'run_manifest.json').read_text())['parameters']
        name=f"{a['cluster']}_{a['start']}_slack{a['slack']:g}_clockfixed";newlog=OUT/'logs'/f'{name}.txt'
        with newlog.open('w') as f:
            r=subprocess.run([sys.executable,str(ROOT/'work/research/analysis/run_chronological_replay_revision.py'),
                '--cluster',a['cluster'],'--start',a['start'],'--slack',str(a['slack']),'--run-label','clockfixed'],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT)
        folder=OUT/'runs'/name;terminal=json.loads((folder/'terminal.json').read_text())
        new=dict(name=name,case_id=row['name'],exit_code=r.returncode,**terminal,log=str(newlog.relative_to(ROOT)),
                 previous_terminal_error=row['name'],repair='canonical event coordinates in seconds; no deadline changes')
        corrected.append(new);print(json.dumps(new),flush=True)
    (OUT/'pilot_process_results_corrected.json').write_text(json.dumps(corrected,indent=2)+'\n')
    if any(row['exit_code'] for row in corrected):raise SystemExit(1)
