"""Standalone source-backed pilot figure; bounds are not confidence intervals."""
from pathlib import Path
import json,hashlib
import numpy as np,pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'outputs/research/revision/replay'
source=OUT/'gang/certified_results.csv';d=pd.read_csv(source)
plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'pdf.fonttype':42,'svg.fonttype':'none'})
fig,axs=plt.subplots(1,2,figsize=(12,5.5),gridspec_kw={'wspace':.40})
fig.subplots_adjust(left=.07,right=.97,top=.78,bottom=.27)
fig.suptitle('Service constraints shape the usable energy opportunity',x=.035,y=.97,ha='left',fontweight='bold',fontsize=16)
fig.text(.035,.90,'Four production cohorts | non-preemptive fixed-size GPU gangs | retrospective completion benchmarks',fontsize=10,color='#425466')
clusters=['Earth','Venus','Saturn','Uranus'];colors=['#7a8995','#177b8c','#bd762e'];ax=axs[0];x=np.arange(4)
for offset,slack,color in zip([-.25,0,.25],[0,6,24],colors):
    rows=d[d.slack==slack].set_index('cluster').loc[clusters]
    ax.bar(x+offset,rows.all_gpu_energy_saving_pct,width=.22,color=color,label=f'+{slack} h')
ax.set_xticks(x,clusters);ax.set_ylim(0,12);ax.set_ylabel('All-GPU normalized energy saving (%)')
ax.set_title('a   Includes fixed background and GPU idle',loc='left',fontsize=11,fontweight='bold',pad=15)
ax.grid(axis='y',alpha=.16);ax.set_axisbelow(True);ax.legend(title='Extra completion allowance',frameon=False,fontsize=9,title_fontsize=9,loc='upper left')
ax=axs[1];rows=d[d.slack==24].set_index('cluster').loc[clusters]
for y,c in enumerate(clusters):
    lo=rows.loc[c,'cohort_incremental_gpu_energy_saving_pct'];hi=rows.loc[c,'upper_bound_on_cohort_saving_pct']
    ax.plot([lo,hi],[y,y],color='#becbd2',lw=3)
    ax.scatter(lo,y,s=45,color='#177b8c',zorder=3)
    ax.scatter(hi,y,s=45,facecolors='white',edgecolors='#bd762e',lw=1.6,zorder=4)
ax.set_yticks(range(4),clusters);ax.invert_yaxis();ax.set_xlim(0,40)
ax.set_xlabel('Cohort above-idle GPU energy saving (%)');ax.set_title('b   Constructed schedule and upper bound (+24 h)',loc='left',fontsize=11,fontweight='bold',pad=15)
ax.grid(axis='x',alpha=.16);ax.set_axisbelow(True)
from matplotlib.lines import Line2D
ax.legend([Line2D([],[],marker='o',ls='',color='#177b8c'),Line2D([],[],marker='o',ls='',markerfacecolor='white',markeredgecolor='#bd762e')],
          ['Feasible schedule','Per-job energy bound'],loc='lower left',frameon=False,fontsize=9)
fig.text(.035,.16,'Conditional GPU-only model: one common DVFS curve, assumed GPU idle ratio 0.10. No whole-node or grid benefit is measured.',fontsize=9,color='#425466')
fig.text(.035,.115,'Cohort: completed jobs submitted and finished during 6–13 April 2020; 192 h domain retains all other allocations as background.',fontsize=9,color='#425466')
fig.text(.035,.070,'Panel b brackets achievable and upper-bounded opportunity in this model; it is not a confidence interval or proof of global optimality.',fontsize=9,color='#425466')
folder=OUT/'figures';folder.mkdir(exist_ok=True)
for ext in ['png','pdf','svg']:fig.savefig(folder/f'fixed_service_replay.{ext}',dpi=190)
svg=folder/'fixed_service_replay.svg';svg.write_text('\n'.join(line.rstrip() for line in svg.read_text().splitlines())+'\n')
(folder/'provenance.json').write_text(json.dumps(dict(source=str(source.relative_to(ROOT)),sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
    panel_a='all_gpu_energy_saving_pct, 4 clusters x 3 slack scenarios',
    panel_b='24h slack, cohort_incremental_gpu_energy_saving_pct and upper_bound_on_cohort_saving_pct',
    scope='Single prespecified week; modeled GPU-only energy; distinct denominators labelled per panel'),indent=2)+'\n')
