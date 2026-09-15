"""Submission-style main figures for the English core paper (white background, thin lines, vector output).
Fig2: incremental cost per AI MWh by scenario, three provinces, constrained exchange, AI 5/10/20% (price mode).
Fig3: realised share of coordination value under TOU tariff, event mechanism and real-time price.
Fig4: robustness — ten weather years (box) and cost Monte Carlo (box) of the rigid-to-coordinated gap; real-time-price gap.
Captions live in the manuscript; figures carry no evidence-tier watermark, the manuscript text does.
"""
from pathlib import Path
import pandas as pd,numpy as np,matplotlib
matplotlib.use('Agg');import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[3];T=ROOT/'outputs/research/tables';F=ROOT/'outputs/research/figures/submission';F.mkdir(exist_ok=True,parents=True)
plt.rcParams.update({'font.size':8,'axes.spines.top':False,'axes.spines.right':False,'axes.linewidth':0.6,'xtick.major.width':0.6,'ytick.major.width':0.6})
P=['Gansu','Jiangsu','Guizhou'];C={'S0':'#6e6e6e','S1':'#1f77b4','S3':'#d62728','S1rt':'#ff7f0e','S2':'#2ca02c'};L={'S0':'Rigid (S0)','S1':'Firm under TOU tariff (S1)','S3':'Event commitment (S3)','S1rt':'Firm under system real-time price (S1rt)','S2':'System-coordinated (S2)'}
g=pd.read_csv(T/'regional_2030_gaps.csv');g=g[(~g.export)&(g.slack_mult==1.0)]
# Fig 2
fig,ax=plt.subplots(1,3,figsize=(7.2,2.4),sharey=True)
for j,p in enumerate(P):
    s=g[g.province==p].sort_values('ai_share');x=np.arange(3);w=0.16
    for k,c in enumerate(['S0','S1','S3','S1rt','S2']):ax[j].bar(x+(k-2)*w,s[f'cost_{c}'],w,color=C[c],label=L[c] if j==0 else None,linewidth=0)
    ax[j].set_xticks(x);ax[j].set_xticklabels([f'{int(a*100)}%' for a in s.ai_share]);ax[j].set_title(p,fontsize=9);ax[j].set_xlabel('AI load, % of 2030 peak');ax[j].grid(axis='y',alpha=.25,linewidth=.5)
    lo=s[[f'cost_{c}' for c in C]].min().min();ax[j].set_ylim(bottom=max(0,lo*0.85))
ax[0].set_ylabel('Incremental system cost\nper AI MWh (EUR MWh$^{-1}$)');ax[0].legend(fontsize=6,frameon=False,loc='upper left')
fig.tight_layout();[fig.savefig(F/f'fig2_cost_by_scenario.{e}',dpi=300) for e in ['pdf','png','svg']]
# Fig 3: realised share = (cost_S0 - cost_X)/(cost_S0 - cost_S2)
fig,ax=plt.subplots(figsize=(7.2,2.3))
rows=[]
for p in P:
    for _,r in g[g.province==p].sort_values('ai_share').iterrows():
        den=r.cost_S0-r.cost_S2
        rows.append(dict(province=p,ai=r.ai_share,**{c:(r.cost_S0-r[f'cost_{c}'])/den if den>1e-9 else np.nan for c in ['S1','S3','S1rt']}))
d=pd.DataFrame(rows);x=np.arange(len(d));w=0.25
for k,c in enumerate(['S1','S3','S1rt']):ax.bar(x+(k-1)*w,d[c].clip(-0.5,1.2),w,color=C[c],label=L[c],linewidth=0)
ax.axhline(1,color='k',lw=.6,ls='--');ax.axhline(0,color='k',lw=.6);ax.set_xticks(x);ax.set_xticklabels([f"{r.province}\n{int(r.ai*100)}%" for _,r in d.iterrows()],fontsize=7)
ax.set_ylabel('Share of coordination value realised');ax.legend(fontsize=6.5,frameon=False,ncol=3,loc='lower left');ax.grid(axis='y',alpha=.25,linewidth=.5)
fig.tight_layout();[fig.savefig(F/f'fig3_realised_share.{e}',dpi=300) for e in ['pdf','png','svg']]
# Fig 4: robustness
mw=pd.read_csv(T/'regional_2030_multiweather.csv');mw=mw[mw.gap_S0_S2_pct.notna()];mc=pd.read_csv(T/'regional_2030_cost_montecarlo.csv');mc=mc[mc.gap_S0_S2_pct.notna()]
fig,ax=plt.subplots(1,3,figsize=(7.2,2.4))
for i,(df,title,col) in enumerate([(mw[mw.idle==0.25],'Ten weather years (2015–2024)','gap_S0_S2_pct'),(mc,'Cost-parameter Monte Carlo','gap_S0_S2_pct'),(mw[mw.idle==0.25],'Firm under real-time price','gap_S1rt_S2_pct')]):
    data=[df[df.province==p][col].values for p in P];bp=ax[i].boxplot(data,tick_labels=P,widths=0.5,patch_artist=True,medianprops=dict(color='k',lw=.8),whiskerprops=dict(lw=.6),capprops=dict(lw=.6),boxprops=dict(lw=.6,facecolor='#dfe8f3'),flierprops=dict(marker='o',ms=2,lw=.4))
    ax[i].set_title(title,fontsize=8.5);ax[i].grid(axis='y',alpha=.25,linewidth=.5)
ax[0].set_ylabel('Rigid-to-coordinated gap (%)');ax[2].set_ylabel('Gap to coordinated optimum (%)')
fig.tight_layout();[fig.savefig(F/f'fig4_robustness.{e}',dpi=300) for e in ['pdf','png','svg']]
print('submission figures saved')
