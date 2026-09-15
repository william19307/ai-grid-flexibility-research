"""Figure: observed scheduling wait, job duration and GPU utilisation in three public production traces."""
from pathlib import Path
import json,numpy as np,pandas as pd,matplotlib
matplotlib.use('Agg');import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[3];T=ROOT/'outputs/research/tables';OUT=ROOT/'outputs/research/figures'
ali=pd.read_csv(ROOT/'work/research/prepared/alibaba_pai_2020_terminated_gpu_jobs_wait_run.csv.gz')
hel=[]
for c in ['Venus','Saturn','Earth','Uranus']:
    d=pd.read_csv(ROOT/f'work/research/sources/helios_sensetime/data/{c}/cluster_log.csv');d=d[d.gpu_num>0];d['gpu_hours']=d.gpu_num*d.duration/3600;d['wait_h']=d.queue/3600;d['run_h']=d.duration/3600;hel.append(d)
hel=pd.concat(hel)
phi=None
try:phi=pd.read_csv(T/'philly_gpu_jobs_wait_run.csv.gz')
except Exception:pass
def wcdf(x,w):
    o=np.argsort(x);x=np.asarray(x)[o];w=np.asarray(w)[o];return x,np.cumsum(w)/w.sum()
fig,ax=plt.subplots(1,3,figsize=(12,3.6))
for name,df,col in [('Helios (SenseTime, 2020)',hel,'#1f77b4'),('Alibaba PAI (2020)',ali,'#d62728')]+([('Philly (Microsoft, 2017)',phi,'#2ca02c')] if phi is not None else []):
    x,c=wcdf(np.maximum(df.wait_h.values,1e-3),df.gpu_hours.values);ax[0].plot(x,c,color=col,label=name)
    x,c=wcdf(np.maximum(df.run_h.values,1e-3),df.gpu_hours.values);ax[1].plot(x,c,color=col,label=name)
for a,t in zip(ax[:2],['Observed scheduling wait (h)','Job run time (h)']):
    a.set_xscale('log');a.set_xlabel(t);a.set_ylabel('GPU-hour-weighted CDF');a.grid(alpha=.3);a.spines[['top','right']].set_visible(False)
ax[0].axvline(1,color='gray',ls=':',lw=.8);ax[0].axvline(24,color='gray',ls=':',lw=.8);ax[1].axvline(24,color='gray',ls=':',lw=.8)
ax[0].legend(fontsize=8,frameon=False)
# utilisation: Alibaba per-instance average GPU util (share of one GPU)
a=json.load(open(T/'alibaba_pai_2020_trace_audit.json'))['statistics']['instance_avg_gpu_util_percent_of_one_gpu']
ps=[10,25,50,75,90,95,99];ax[2].plot(ps,[a[f'p{p}'] for p in ps],'o-',color='#d62728',label='Alibaba PAI: per-instance mean GPU util')
try:
    ph=json.load(open(T/'philly_trace_audit.json'))['statistics']['machine_gpu_util_percent'];ax[2].plot(ps,[ph[f'p{p}'] for p in ps],'s-',color='#2ca02c',label='Philly: per-GPU per-minute util')
except Exception:pass
ax[2].set_xlabel('Percentile');ax[2].set_ylabel('GPU utilisation (%)');ax[2].grid(alpha=.3);ax[2].spines[['top','right']].set_visible(False);ax[2].legend(fontsize=8,frameon=False)
fig.suptitle('Public production GPU-cluster traces: waits are a lower bound on tolerated delay, not deadlines; no power telemetry in any trace',fontsize=8.5,color='dimgray')
fig.tight_layout(rect=[0,0,1,0.94])
for ext in ['png','svg','pdf']:fig.savefig(OUT/f'production_traces_wait_duration_util.{ext}',dpi=160)
print('saved')
