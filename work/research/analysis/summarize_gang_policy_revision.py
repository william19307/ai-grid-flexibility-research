"""Policy-specific feasible allocations and deterministic optimality bounds."""
from pathlib import Path
import json,hashlib
import numpy as np,pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'outputs/research/revision/policy'
f=OUT/'certified_factorials.csv';d=pd.read_csv(f);cells=pd.read_csv(OUT/'certified_cells.csv');audit=json.loads((OUT/'independent_verification.json').read_text());assert audit['all_declared_cases_accounted_for']
d['identified']=np.where(d.optimal_mode_share_lower_pct>50+1e-6,'mode_majority',np.where(d.optimal_mode_share_upper_pct<50-1e-6,'start_majority','not_identified'))
summary=d.groupby('slack').agg(cases=('run','count'),constructed_mode_share_min_pct=('mode_share_pct','min'),constructed_mode_share_max_pct=('mode_share_pct','max'),bill_saving_min_pct=('constructed_total_bill_saving_pct','min'),bill_saving_max_pct=('constructed_total_bill_saving_pct','max'),energy_saving_min_pct=('constructed_all_gpu_energy_saving_pct','min'),energy_saving_max_pct=('constructed_all_gpu_energy_saving_pct','max'),optimal_share_lower_min_pct=('optimal_mode_share_lower_pct','min'),optimal_share_upper_max_pct=('optimal_mode_share_upper_pct','max')).reset_index()
summary.to_csv(OUT/'summary_by_allowance.csv',index=False);counts=d.groupby(['slack','identified']).size().unstack(fill_value=0).reindex(columns=['mode_majority','start_majority','not_identified'],fill_value=0);counts.to_csv(OUT/'majority_identification.csv')
peak=cells.pivot(index='run',columns='cell',values='peak_normalized_gpu_power');growth=100*(peak.C11-peak.C00)/peak.C00
bill=cells.pivot(index='run',columns='cell',values='all_gpu_bill');energy=cells.pivot(index='run',columns='cell',values='all_gpu_energy')
report=dict(verified_factorials=len(d),verified_schedules=len(cells),failed_factorials=audit['failed_factorials'],
    zero_allowance_fixed_start_value_max_abs=float(abs(d[d.slack==0].mode_first).max()),
    zero_allowance_mode_share_ceiling_pct=50.,
    majority_identification=counts.reset_index().to_dict(orient='records'),
    peak_increase_cases=int((growth>1e-8).sum()),max_hourly_gpu_peak_increase_pct=float(growth.max()),
    energy_increase_cases=int((energy.C11>energy.C00+1e-7).sum()),
    scope='Conditional GPU-bill factorial over chosen operational rights. Constructed-policy Shapley shares and intervals for optimal capability shares are different estimands; neither is a physical universal split or system-capacity value.')
(OUT/'analysis.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2));print(summary.to_string(index=False))
plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'pdf.fonttype':42,'svg.fonttype':'none'})
fig,axs=plt.subplots(1,2,figsize=(13,6));fig.subplots_adjust(left=.07,right=.98,top=.76,bottom=.27,wspace=.32)
colors=['#177b8c','#a766ad','#bc762b'];workloads=['ft_llama_8b_dolly','infer_llama_8b_32g','pt_mpt_13b_lg'];labels=['Fine-tuning','Inference','Pretraining']
ax=axs[0]
for j,(w,col,label) in enumerate(zip(workloads,colors,labels)):
    for i,slack in enumerate([0,6,24]):
        g=d[(d.workload==w)&(d.slack==slack)].sort_values(['cluster','tariff'])
        jitter=np.linspace(-.05,.05,len(g))
        ax.scatter(i+(j-1)*.18+jitter,g.mode_share_pct,color=col,s=28,alpha=.8,label=label if i==0 else None)
ax.axhline(50,color='#566573',lw=1,ls='--');ax.set_xticks([0,1,2],['0 h','6 h','24 h']);ax.set_ylim(0,100);ax.set_xlabel('Extra completion allowance');ax.set_ylabel('Mode share of constructed bill savings (%)');ax.set_title('a   Feasible policy allocation',loc='left',fontweight='bold',pad=15);ax.legend(frameon=False,fontsize=9,loc='upper left');ax.grid(axis='y',alpha=.15)
ax=axs[1];bottom=np.zeros(3)
for cat,color,label in [('start_majority','#437696','Start majority established'),('mode_majority','#a766ad','Mode majority established'),('not_identified','#cbd4da','Majority not identified')]:
    vals=counts.reindex([0,6,24])[cat].to_numpy();ax.bar(np.arange(3),vals,bottom=bottom,color=color,width=.6,label=label)
    for i,v in enumerate(vals):
        if v:ax.text(i,bottom[i]+v/2,str(v),ha='center',va='center',color='white' if cat!='not_identified' else '#263747',fontweight='bold')
    bottom+=vals
ax.set_xticks([0,1,2],['0 h','6 h','24 h']);ax.set_xlabel('Extra completion allowance');ax.set_ylabel('Factorial conditions (36 per allowance)');ax.set_ylim(0,44);ax.set_title('b   What optimal-cost bounds identify',loc='left',fontweight='bold',pad=15);ax.legend(frameon=False,fontsize=9,loc='upper left',bbox_to_anchor=(0,1.04));ax.grid(axis='y',alpha=.1);ax.set_axisbelow(True)
fig.suptitle('The attribution changes when service decision rights are explicit',x=.035,y=.97,ha='left',fontweight='bold',fontsize=16)
fig.text(.035,.90,'Same real jobs and background | fixed-start vs flexible-start × full-speed vs variable-mode | retrospective information',fontsize=10)
fig.text(.035,.17,'Panel a: allocations over feasible heuristic policies. Panel b: whether deterministic bounds prove an optimal share above/below 50%.',fontsize=9,color='#425466')
fig.text(.035,.12,'These are different quantities. Neither is a confidence interval or a universal physical split of efficiency and flexibility.',fontsize=9,color='#425466')
fig.text(.035,.07,'GPU-only assumed power boundary; historical relative tariffs on an assumed trace clock. No whole-node, system-cost or capacity claim.',fontsize=9,color='#425466')
folder=OUT/'figures';folder.mkdir(exist_ok=True)
for ext in ['png','pdf','svg']:fig.savefig(folder/f'policy_attribution_bounds.{ext}',dpi=180)
svg=folder/'policy_attribution_bounds.svg';svg.write_text('\n'.join(l.rstrip() for l in svg.read_text().splitlines())+'\n')
(folder/'provenance.json').write_text(json.dumps(dict(sources={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [f,OUT/'certified_cells.csv']},scope=report['scope']),indent=2)+'\n')
