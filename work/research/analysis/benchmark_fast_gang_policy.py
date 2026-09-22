"""Compare one completed reference case against interval batching, separately."""
from pathlib import Path
import sys,json,hashlib,time
import pandas as pd,numpy as np
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'work/research/analysis'));sys.path.insert(0,str(ROOT/'work/research/models'))
import run_gang_policy_revision as runner
import gang_policy
from gang_policy_fast import best_interval
ORIGINAL=runner.OUT;TARGET=ORIGINAL/'performance/saturn_dolly24_fast'
TARGET.mkdir(exist_ok=False)
spec=json.loads((ORIGINAL/'manifest.json').read_text());spec['cases']=[c for c in spec['cases'] if c['cluster']=='Saturn' and c['workload']=='ft_llama_8b_dolly' and c['slack']==24 and c['tariff']=='Jiangsu'];assert len(spec['cases'])==1
spec['performance_override']='Only gang_policy.best_interval replaced by batched equivalent implementation; this is a numerical equivalence experiment selected from an already completed case, not a new independent research condition.'
snap=json.loads((ORIGINAL/'source_snapshot.json').read_text())
for f in [Path(__file__).resolve(),ROOT/'work/research/models/gang_policy_fast.py']:
    key=str(f.relative_to(ROOT));spec['source_sha256'][key]=hashlib.sha256(f.read_bytes()).hexdigest();snap[key]=f.read_text()
(TARGET/'manifest.json').write_text(json.dumps(spec,indent=2)+'\n');(TARGET/'source_snapshot.json').write_text(json.dumps(snap,indent=2)+'\n')
runner.OUT=TARGET;gang_policy.best_interval=best_interval;runner.run()
name='Saturn_ft_llama_8b_dolly_24_Jiangsu';old=ORIGINAL/'runs'/name;new=TARGET/'runs'/name
oldsm=json.loads((old/'summary.json').read_text());newsm=json.loads((new/'summary.json').read_text());assert newsm['status']!='error',newsm
same={}
for cell in ['C00','C10','C01','C11']:
    a=pd.read_csv(old/f'{cell}.csv.gz',float_precision='round_trip');b=pd.read_csv(new/f'{cell}.csv.gz',float_precision='round_trip')
    same[cell]=bool(np.array_equal(a.to_numpy(),b.to_numpy()));assert same[cell],cell
for key in ['upper_incremental_bill','lower_incremental_bill','global_optimum_mode_share_bracket']:
    assert oldsm[key]==newsm[key],key
report=dict(case=name,reference_runtime_s=oldsm['runtime_s'],batched_runtime_s=newsm['runtime_s'],schedule_arrays_identical=same,all_costs_and_bounds_bitwise_identical=True)
(TARGET/'equivalence.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
