"""Parse MLPerf Training v4.0 AC-power logs (Supermicro 8xH100 nodes, llama2_70b_lora) into idle and active node power.

Evidence tier: published benchmark measurements (MLCommons policy-compliant AC power at node level, ~2 s readings).
Idle = lowest 5% of readings (pre-training baseline); active = readings in the central 60% of the window.
"""
from pathlib import Path
import json,glob,hashlib,numpy as np
ROOT=Path(__file__).resolve().parents[3];SRC=ROOT/'work/research/sources/mlperf_power/llama2_70b_lora_8xH100';OUT=ROOT/'outputs/research/tables'
res={};files=sorted(glob.glob(str(SRC/'*/node_*.txt')))
for f in files:
    vals=[];ts=[]
    for line in open(f):
        if '"power_reading"' in line:
            d=json.loads(line.split(':::MLLOG',1)[1]);vals.append(float(d['value']));ts.append(d['time_ms'])
    v=np.array(vals);n=len(v)
    if n<20:continue
    idle=v[v<=np.percentile(v,5)];active=v[int(n*0.2):int(n*0.8)]  # idle = lowest 5% of readings (pre-training baseline ~2.6 kW); active = central 60%
    res[Path(f).parent.name+'/'+Path(f).name]=dict(readings=n,duration_s=(ts[-1]-ts[0])/1000,idle_w_median=float(np.median(idle)),active_w_median=float(np.median(active)),active_w_p90=float(np.percentile(active,90)),max_w=float(v.max()),sha256=hashlib.sha256(open(f,'rb').read()).hexdigest())
idle=np.array([r['idle_w_median'] for r in res.values()]);act=np.array([r['active_w_median'] for r in res.values()]);mx=np.array([r['max_w'] for r in res.values()])
summary=dict(source='https://github.com/mlcommons/training_results_v4.0/tree/main/smc-ac-power (Supermicro, 8x H100 SXM 80GB per node)',benchmark='llama2_70b_lora',nodes=len(res),node_idle_w_median=float(np.median(idle)),node_active_w_median=float(np.median(act)),node_max_w_median=float(np.median(mx)),idle_over_active=float(np.median(idle)/np.median(act)),idle_over_max=float(np.median(idle)/np.median(mx)),per_gpu_active_w_incl_node=float(np.median(act)/8),
    note='node-level AC power includes CPUs, memory, fans and PSU losses; idle fraction here is node-level, not GPU-level; readings start before training so early samples are idle; benchmark-specific',files=res)
json.dump(summary,open(OUT/'mlperf_v40_power_audit.json','w'),indent=1)
print({k:v for k,v in summary.items() if k!='files'})
