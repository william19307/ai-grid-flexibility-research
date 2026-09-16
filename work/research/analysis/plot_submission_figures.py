"""Submission figures 2–4 (v1.4 metric: total incremental system cost for the same computing work).
Fig2: cost reduction relative to rigid operation (%) by scenario; islanded; AI 5/10/20%; slack x1.
Fig3: share of the timing component realised, (S0e - X)/(S0e - S2), for S1, S3, S1rt.
Fig4: robustness — (a) total reduction S0->S2 across weather years, (b) across Monte Carlo draws, (c) S1rt gap to optimum across weather years.
"""
from pathlib import Path
import pandas as pd,numpy as np,matplotlib
matplotlib.use('Agg');import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[3];T=ROOT/'outputs/research/tables';F=ROOT/'outputs/research/figures/submission';F.mkdir(exist_ok=True,parents=True)
plt.rcParams.update({'font.size':8,'axes.spines.top':False,'axes.spines.right':False,'axes.linewidth':0.6,'xtick.major.width':0.6,'ytick.major.width':0.6})
P=['Gansu','Jiangsu','Guizhou'];IDLE=0.41
C={'S0e':'#bcbd22','S1':'#1f77b4','S3':'#d62728','S1rt':'#ff7f0e','S2':'#2ca02c'}
L={'S0e':'S0e efficient modes, no shifting','S1':'S1 firm, tariff shape','S3':'S3 event contract','S1rt':'S1rt firm, marginal-cost-shaped price','S2':'S2 system-coordinated'}
g=pd.read_csv(T/'regional_2030_gaps.csv');g=g[(~g.export)&(g.slack_mult==1.0)]
# Fig 2: reduction vs rigid
fig,ax=plt.subplots(1,3,figsize=(7.2,2.9),sharey=True)
for j,p in enumerate(P):
    s=g[g.province==p].sort_values('ai_share');x=np.arange(3);w=0.16
    for k,c in enumerate(['S0e','S1','S3','S1rt','S2']):
        vals=(1-s[f'cost_{c}']/s['cost_S0'])*100
        ax[j].bar(x+(k-2)*w,vals,w,color=C[c],label=L[c] if j==0 else None,linewidth=0)
    ax[j].set_xticks(x);ax[j].set_xticklabels([f'{int(a*100)}%' for a in s.ai_share]);ax[j].set_title(p,fontsize=9);ax[j].set_xlabel('AI load, % of 2030 peak');ax[j].grid(axis='y',alpha=.25,linewidth=.5);ax[j].axhline(0,color='k',lw=.5)
ax[0].set_ylabel('Reduction of incremental system cost\nrelative to rigid operation (%)')
h,l=ax[0].get_legend_handles_labels();fig.legend(h,l,loc='upper center',ncol=3,fontsize=6.5,frameon=False,bbox_to_anchor=(0.5,1.0))
fig.tight_layout(rect=[0,0,1,0.88]);[fig.savefig(F/f'fig2_cost_by_scenario.{e}',dpi=300) for e in ['pdf','png','svg']]
# Fig 3: timing share realised
fig,ax=plt.subplots(figsize=(7.2,2.8))
rows=[]
for p in P:
    for _,r in g[g.province==p].sort_values('ai_share').iterrows():
        den=r.cost_S0e-r.cost_S2
        rows.append(dict(province=p,ai=r.ai_share,**{c:((r.cost_S0e-r[f'cost_{c}'])/den if den>1 else np.nan) for c in ['S1','S3','S1rt']}))
d=pd.DataFrame(rows);x=np.arange(len(d));w=0.25
for k,c in enumerate(['S1','S3','S1rt']):
    ax.bar(x+(k-1)*w,d[c].clip(-0.6,1.2),w,color=C[c],label=L[c],linewidth=0)
    for xi,v in zip(x+(k-1)*w,d[c]):
        if v<-0.6:ax.text(xi,-0.63,f'{v:.1f}',ha='center',va='top',fontsize=5,rotation=90)
ax.axhline(1,color='k',lw=.6,ls='--');ax.axhline(0,color='k',lw=.6);ax.set_xticks(x);ax.set_xticklabels([f"{r.province}\n{int(r.ai*100)}%" for _,r in d.iterrows()],fontsize=7)
ax.set_ylabel('Share of shifting value realised\n(S0e − X)/(S0e − S2)');ax.grid(axis='y',alpha=.25,linewidth=.5);ax.set_ylim(-0.95,1.25)
h,l=ax.get_legend_handles_labels();fig.legend(h,l,loc='upper center',ncol=3,fontsize=6.5,frameon=False,bbox_to_anchor=(0.5,1.0))
fig.tight_layout(rect=[0,0,1,0.9]);[fig.savefig(F/f'fig3_realised_share.{e}',dpi=300) for e in ['pdf','png','svg']]
# Fig 4
mw=pd.read_csv(T/'regional_2030_multiweather.csv');mw=mw[mw.red_S0_S2_pct.notna()];mc=pd.read_csv(T/'regional_2030_cost_montecarlo.csv');mc=mc[mc.red_S0_S2_pct.notna()]
fig,ax=plt.subplots(1,3,figsize=(7.2,2.5))
for i,(df,title,col,yl) in enumerate([(mw[mw.idle==IDLE],'a  Ten weather years','red_S0_S2_pct','Cost reduction, rigid to\ncoordinated (%)'),(mc,'b  Cost-parameter Monte Carlo','red_S0_S2_pct','Cost reduction, rigid to\ncoordinated (%)'),(mw[mw.idle==IDLE],'c  S1rt gap to optimum','gap_S1rt_S2_pct','Gap to coordinated\noptimum (%)')]):
    data=[df[df.province==p][col].values for p in P]
    ax[i].boxplot(data,tick_labels=P,widths=0.5,patch_artist=True,medianprops=dict(color='k',lw=.8),whiskerprops=dict(lw=.6),capprops=dict(lw=.6),boxprops=dict(lw=.6,facecolor='#dfe8f3'),flierprops=dict(marker='o',ms=2,lw=.4))
    ax[i].set_title(title,fontsize=8.5,loc='left');ax[i].grid(axis='y',alpha=.25,linewidth=.5);ax[i].set_ylabel(yl,fontsize=7.5)
fig.tight_layout();[fig.savefig(F/f'fig4_robustness.{e}',dpi=300) for e in ['pdf','png','svg']]
print('submission figures saved')
