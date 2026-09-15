"""Fig. 1 (submission style): a measured GPU modes; b production-trace wait/run CDFs; c MLPerf node idle vs active power."""
from pathlib import Path
import json,numpy as np,pandas as pd,matplotlib
matplotlib.use('Agg');import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[3];T=ROOT/'outputs/research/tables';F=ROOT/'outputs/research/figures/submission'
plt.rcParams.update({'font.size':8,'axes.spines.top':False,'axes.spines.right':False,'axes.linewidth':0.6})
fig,ax=plt.subplots(1,3,figsize=(7.2,2.4))
m=pd.read_csv(T/'dvfs_measured_and_derived.csv')
for w,g in m.groupby('Workload'):
    g=g.sort_values('GPU power cap');ax[0].plot(g['measured_power_ratio'],g['normalized throughput'],'-o',ms=2.5,lw=.8,label=w if 'llama' in w or 'infer' in w else None)
ax[0].plot([0,1],[0,1],'k:',lw=.6);ax[0].set_xlabel('Measured GPU power, share of 400 W cap');ax[0].set_ylabel('Normalised throughput');ax[0].set_title('a  Measured power–throughput modes',fontsize=8.5,loc='left');ax[0].legend(fontsize=5.5,frameon=False,loc='lower right')
hel=[]
for c in ['Venus','Saturn','Earth','Uranus']:
    d=pd.read_csv(ROOT/f'work/research/sources/helios_sensetime/data/{c}/cluster_log.csv');d=d[d.gpu_num>0];d['gh']=d.gpu_num*d.duration/3600;hel.append(d[['queue','duration','gh']])
hel=pd.concat(hel);ali=pd.read_csv(ROOT/'work/research/prepared/alibaba_pai_2020_terminated_gpu_jobs_wait_run.csv.gz');phi=pd.read_csv(T/'philly_gpu_jobs_wait_run.csv.gz')
def wcdf(x,w):o=np.argsort(x);return np.asarray(x)[o],np.cumsum(np.asarray(w)[o])/np.sum(w)
for name,x,w,col in [('Helios wait',hel.queue/3600,hel.gh,'#1f77b4'),('Alibaba wait',ali.wait_h,ali.gpu_hours,'#d62728'),('Philly wait',phi.wait_h,phi.gpu_hours,'#2ca02c')]:
    xx,cc=wcdf(np.maximum(x.values,1e-3),w.values);ax[1].plot(xx,cc,color=col,lw=.9,label=name)
for name,x,w,col in [('Helios run',hel.duration/3600,hel.gh,'#1f77b4'),('Alibaba run',ali.run_h,ali.gpu_hours,'#d62728'),('Philly run',phi.run_h,phi.gpu_hours,'#2ca02c')]:
    xx,cc=wcdf(np.maximum(x.values,1e-3),w.values);ax[1].plot(xx,cc,color=col,lw=.9,ls='--',label=name)
ax[1].set_xscale('log');ax[1].set_xlabel('Hours');ax[1].set_ylabel('GPU-hour-weighted CDF');ax[1].set_title('b  Production traces: wait (solid), run (dashed)',fontsize=8.5,loc='left');ax[1].legend(fontsize=5.5,frameon=False,ncol=2,loc='upper left');ax[1].axvline(24,color='gray',lw=.5,ls=':')
ml=json.load(open(T/'mlperf_v40_power_by_benchmark.json'));bm=list(ml);x=np.arange(len(bm))
ax[2].bar(x-0.18,[ml[b]['idle_w']/1000 for b in bm],0.36,color='#9ecae1',label='Idle (lowest 5% of readings)');ax[2].bar(x+0.18,[ml[b]['active_w']/1000 for b in bm],0.36,color='#3182bd',label='Active (central 60%)')
ax[2].set_xticks(x);ax[2].set_xticklabels(['Llama2-70B LoRA','ResNet-50','SSD'],fontsize=7);ax[2].set_ylabel('Node AC power (kW), 8×H100');ax[2].set_title('c  MLPerf Training v4.0 node power',fontsize=8.5,loc='left');ax[2].legend(fontsize=5.5,frameon=False,loc='lower right')
fig.tight_layout();[fig.savefig(F/f'fig1_constraints_and_power.{e}',dpi=300) for e in ['pdf','png','svg']];print('fig1 saved')
