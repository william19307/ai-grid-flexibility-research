"""Figure: uncalibrated regional smoke grid — incremental system cost and emissions per AI MWh by scenario."""
from pathlib import Path
import pandas as pd,numpy as np,matplotlib
matplotlib.use('Agg');import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'outputs/research/figures';OUT.mkdir(exist_ok=True,parents=True)
d=pd.read_csv(ROOT/'outputs/research/tables/regional_smoke_grid_summary.csv');d=d[d.W==24]
base=d[d.case=='NOAI'].set_index(['province','export','ai_share'])
rows=[]
for (p,e,a),g in d.groupby(['province','export','ai_share']):
    b=base.loc[(p,e,a)]
    for _,r in g[g.case!='NOAI'].iterrows():rows.append(dict(province=p,export=e,ai=a,case=r.case,cost=(r.total_cost-b.total_cost)/r.ai_mwh,co2=(r.emissions_t-b.emissions_t)/r.ai_mwh,ocgt=r.new_ocgt))
x=pd.DataFrame(rows);cases=['S0','S0b','S1','S2'];labels={'S0':'S0 rigid, full speed','S0b':'S0b rigid, efficient mode','S1':'S1 firm-autonomous','S2':'S2 system-coordinated'}
cols=['#7f7f7f','#bcbd22','#1f77b4','#2ca02c']
fig,axes=plt.subplots(2,3,figsize=(12,6.2),sharey='row')
for j,prov in enumerate(['Gansu','Jiangsu','Guizhou']):
    for i,metric in enumerate(['cost','co2']):
        ax=axes[i,j];sub=x[x.province==prov]
        groups=[(e,a) for e in [True,False] for a in [0.05,0.2]];xt=np.arange(len(groups));w=0.2
        for k,c in enumerate(cases):
            vals=[sub[(sub.export==e)&(sub.ai==a)&(sub.case==c)][metric].values[0] for e,a in groups]
            ax.bar(xt+(k-1.5)*w,vals,w,color=cols[k],label=labels[c] if (i==0 and j==0) else None,linewidth=0)
        ax.set_xticks(xt);ax.set_xticklabels([f"{'export' if e else 'no export'}\nAI {int(a*100)}% of peak" for e,a in groups],fontsize=8)
        ax.grid(axis='y',alpha=.3);ax.spines[['top','right']].set_visible(False)
        if i==0:ax.set_title(prov,fontsize=11)
    axes[0,j].set_ylim(bottom=0);axes[1,j].set_ylim(bottom=0)
axes[0,0].set_ylabel('Incremental system cost\nper AI MWh (EUR/MWh, archive costs)');axes[1,0].set_ylabel('Incremental emissions\nper AI MWh (tCO2/MWh)')
axes[0,0].legend(fontsize=8,frameon=False,loc='lower left')
fig.suptitle('Uncalibrated regional smoke grid, four 2020 representative weeks, W = 24 h. NOT an empirical result: unvalidated hourly load, unverified archive capacities, placeholder tariff and external market.',fontsize=8.5,color='dimgray')
fig.tight_layout(rect=[0,0,1,0.95])
for ext in ['png','svg','pdf']:fig.savefig(OUT/f'regional_smoke_grid_W24.{ext}',dpi=160)
print('saved')
