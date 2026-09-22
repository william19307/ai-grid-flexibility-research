"""Standalone scientific diagnostic; all marks read from audited result rows."""
from pathlib import Path
import json,hashlib
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'outputs/research/revision/power_attribution'
source=OUT/'factorial_results.csv'
data=pd.read_csv(source)
central=data[(data.node_idle==.41)&(data.gpu_idle==.1)&(data.active_overhead==0)]
workloads=['ft_llama_8b_dolly','ft_llama_8b_p3','pt_mpt_13b_lg','pt_mpt_13b_sm','pt_mpt_7b_fast','infer_llama_8b','infer_llama_8b_32g','infer_llama_8b_48g']
labels=['Llama fine-tune / Dolly','Llama fine-tune / P3','MPT-13B / large','MPT-13B / small','MPT-7B / fast','Llama inference','Llama inference / 32 GPU*','Llama inference / 48 GPU*']
colors={'legacy':'#b76539','component':'#186c86'}
plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'pdf.fonttype':42,'svg.fonttype':'none'})
fig,axs=plt.subplots(2,2,figsize=(12.5,9),gridspec_kw={'wspace':.48,'hspace':.40})
fig.subplots_adjust(left=.23,right=.97,top=.88,bottom=.16)
fig.suptitle('Power-boundary assumptions change the estimated value of flexible computing',x=.035,y=.976,ha='left',fontsize=15,fontweight='bold')
fig.text(.035,.939,'Conditional model diagnostics | corrected pumped storage | full foresight | four representative weeks',fontsize=10,color='#465560')
js=central[central.province=='Jiangsu'].set_index(['workload','mapping'])
for ax,metric,title,xlabel,limit in [
    (axs[0,0],'total_reduction_pct','a   Jiangsu: cost benefit','Reduction in incremental AI system cost (%)',(0,23)),
    (axs[0,1],'symmetric_mode_share_pct','b   Jiangsu: policy attribution','Mode-policy share of savings, Shapley (%)',(0,100))]:
    for i,w in enumerate(workloads):
        old=js.loc[(w,'legacy'),metric];new=js.loc[(w,'component'),metric]
        ax.plot([old,new],[i,i],color='#c3cbd0',lw=1.7,zorder=1)
        ax.scatter(old,i,c=colors['legacy'],s=37,marker='s',zorder=2)
        ax.scatter(new,i,c=colors['component'],s=38,marker='o',zorder=3)
    ax.set_yticks(range(len(workloads)),labels if ax is axs[0,0] else ['']*len(labels))
    ax.invert_yaxis();ax.set_xlim(*limit);ax.set_xlabel(xlabel);ax.set_title(title,loc='left',fontweight='bold',pad=12)
    ax.grid(axis='x',alpha=.17);ax.set_axisbelow(True)
main=central[central.workload=='ft_llama_8b_dolly'].set_index(['province','mapping'])
ax=axs[1,0];y=np.arange(3)
for mapping,offset in [('legacy',-.18),('component',.18)]:
    vals=[main.loc[(p,mapping),'total_reduction_pct'] for p in ['Gansu','Guizhou','Jiangsu']]
    bars=ax.barh(y+offset,vals,height=.31,color=colors[mapping])
    ax.bar_label(bars,fmt='%.1f',padding=4,fontsize=9)
ax.set_yticks(y,['Gansu / AI 10%','Guizhou / AI 10%','Jiangsu / AI 20%']);ax.invert_yaxis()
ax.set_xlim(0,23);ax.set_xlabel('Reduction in incremental AI system cost (%)')
ax.set_title('c   Fine-tuning / Dolly across regions',loc='left',fontweight='bold',pad=12)
ax.grid(axis='x',alpha=.17);ax.set_axisbelow(True)
ax=axs[1,1];x=np.arange(3)
for mapping,offset in [('legacy',-.18),('component',.18)]:
    vals=[main.loc[('Jiangsu',mapping),k]/1000 for k in ['new_gas_S0_MW','new_gas_S0e_MW','new_gas_S2_MW']]
    bars=ax.bar(x+offset,vals,width=.32,color=colors[mapping])
    ax.bar_label(bars,fmt='%.2f',padding=4,fontsize=9)
ax.set_xticks(x,['Full-speed\nEDF','Energy-oriented\nEDF','Grid-coordinated\nvariable modes'])
ax.set_ylim(0,10.8);ax.set_ylabel('Model-selected new gas capacity (GW)')
ax.set_title('d   Jiangsu / Dolly: capacity sensitivity',loc='left',fontweight='bold',pad=12)
ax.grid(axis='y',alpha=.17);ax.set_axisbelow(True)
from matplotlib.lines import Line2D
fig.legend([Line2D([],[],color=colors['legacy'],marker='s',ls=''),Line2D([],[],color=colors['component'],marker='o',ls='')],
           ['Direct GPU-ratio mapping (historical)','Component mapping (assumed I=0.41, g=0.10, d=0)'],
           loc='lower left',bbox_to_anchor=(.028,.082),ncol=2,frameon=False,fontsize=10)
fig.text(.035,.057,'All values are conditional simulations, not calibrated whole-node estimates or firm-capacity credits. No confidence intervals are available.',fontsize=9,color='#465560')
fig.text(.035,.035,'* The 32- and 48-GPU configurations have identical normalized curves; these are not independent workload replications.',fontsize=9,color='#465560')
folder=OUT/'figures';folder.mkdir(exist_ok=True)
for ext in ['png','pdf','svg']:fig.savefig(folder/f'power_boundary_diagnostic.{ext}',dpi=190)
svg=folder/'power_boundary_diagnostic.svg'
svg.write_text('\n'.join(line.rstrip() for line in svg.read_text().splitlines())+'\n')
plt.close(fig)
(folder/'figure_provenance.json').write_text(json.dumps(dict(source=str(source.relative_to(ROOT)),sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
    panels=dict(a='Jiangsu ai_share=0.2, 8 configurations, central paired mappings, total_reduction_pct',
                b='same rows as a; symmetric_mode_share_pct',c='ft_llama_8b_dolly, 3 provinces, central paired mappings',
                d='Jiangsu ft_llama_8b_dolly, new_gas_S0/S0e/S2_MW divided by 1000'),
    intervals='not estimated; displayed pairs are alternative assumptions, not confidence bounds'),indent=2)+'\n')
print(folder)
