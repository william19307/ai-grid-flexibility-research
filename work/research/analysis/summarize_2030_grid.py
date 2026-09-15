"""Summarise the 2030 provincial grid: increments per AI MWh, gaps, S3 mechanism outcomes; render figure."""
from pathlib import Path
import pandas as pd,numpy as np,matplotlib
matplotlib.use('Agg');import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[3];T=ROOT/'outputs/research/tables';F=ROOT/'outputs/research/figures'
import sys
MODE=sys.argv[1] if len(sys.argv)>1 else 'price'
fn={'price':'regional_2030_grid_summary.csv','neighbours':'regional_2030_grid_summary_neighbours.csv'}[MODE]
d=pd.read_csv(T/fn);d=d[d.total_cost.notna()]
keys=['province','export','ai_share','slack_mult','slack_base_h'];base=d[d.case=='NOAI'].set_index(keys);rows=[]
for k,g in d.groupby(keys):
    b=base.loc[k];r={c:g[g.case==c].iloc[0] for c in ['S0','S1','S2','S3','S1rt'] if (g.case==c).any()}
    if 'S1rt' not in r:r['S1rt']=r['S2']
    inc=lambda c:(r[c].total_cost-b.total_cost)/r[c].ai_mwh;co2=lambda c:(r[c].emissions_t-b.emissions_t)/r[c].ai_mwh
    rows.append(dict(zip(keys,k))|dict(cost_S0=inc('S0'),cost_S1=inc('S1'),cost_S2=inc('S2'),cost_S3=inc('S3'),cost_S1rt=inc('S1rt'),gap_S1rt_S2_pct=(inc('S1rt')/inc('S2')-1)*100,gap_S0_S2_pct=(inc('S0')/inc('S2')-1)*100,gap_S1_S2_pct=(inc('S1')/inc('S2')-1)*100,gap_S3_S2_pct=(inc('S3')/inc('S2')-1)*100,
        co2_S0=co2('S0'),co2_S1=co2('S1'),co2_S1rt=co2('S1rt'),co2_S2=co2('S2'),co2_S3=co2('S3'),curtail_NOAI=b.curtail,curtail_S2=r['S2'].curtail,
        inv_S0=r['S0'].investment-b.investment,inv_S2=r['S2'].investment-b.investment,new_ocgt_S0=r['S0'].new_ocgt-b.new_ocgt,new_ocgt_S2=r['S2'].new_ocgt-b.new_ocgt,new_batt_S0=r['S0'].new_batt_mw-b.new_batt_mw,new_batt_S2=r['S2'].new_batt_mw-b.new_batt_mw,new_solar_S0=r['S0'].new_solar-b.new_solar,new_solar_S2=r['S2'].new_solar-b.new_solar,
        s3_system_saving_vs_S1=r['S1'].total_cost-r['S3'].total_cost,s3_compensation_floor=r['S3'].s3_compensation_floor_expweek,s3_mean_commitment_mw=r['S3'].s3_mean_commitment_mw,peak_2030=b.peak_2030))
x=pd.DataFrame(rows).round(3);x.to_csv(T/('regional_2030_gaps.csv' if MODE=='price' else 'regional_2030_gaps_neighbours.csv'),index=False)
pd.set_option('display.width',300);pd.set_option('display.max_columns',40)
print(x[['province','export','ai_share','slack_mult','cost_S0','cost_S1','cost_S1rt','cost_S2','cost_S3','gap_S0_S2_pct','gap_S1_S2_pct','gap_S1rt_S2_pct','gap_S3_S2_pct','curtail_NOAI','new_ocgt_S0','new_ocgt_S2','new_batt_S0','new_batt_S2','s3_system_saving_vs_S1','s3_compensation_floor','s3_mean_commitment_mw']].to_string(index=False))
# figure: cost per AI MWh by case, W-slack (1,6), three provinces, export on/off, ai 10%
fig,axes=plt.subplots(2,3,figsize=(12,6.2),sharey='row');cases=['S0','S1','S3','S1rt','S2'];cols=['#7f7f7f','#1f77b4','#d62728','#ff7f0e','#2ca02c'];lab={'S0':'S0 rigid','S1':'S1 firm under TOU tariff','S3':'S3 event commitment','S1rt':'S1rt firm under system real-time price','S2':'S2 system-coordinated'}
for j,prov in enumerate(['Gansu','Jiangsu','Guizhou']):
    sub=x[(x.province==prov)&(x.slack_mult==1.0)]
    for i,(metric,yl) in enumerate([('cost','Incremental system cost per AI MWh (EUR/MWh)'),('co2','Incremental emissions per AI MWh (tCO2/MWh)')]):
        ax=axes[i,j];groups=[(e,a) for e in [True,False] for a in [0.05,0.10,0.20]];xt=np.arange(len(groups));w=0.16
        for k_,c in enumerate(cases):
            vals=[sub[(sub.export==e)&(sub.ai_share==a)][f'{metric}_{c}'].values[0] for e,a in groups]
            ax.bar(xt+(k_-2)*w,vals,w,color=cols[k_],label=lab[c] if (i==0 and j==0) else None,linewidth=0)
        ax.set_xticks(xt);ax.set_xticklabels([f"{'exp' if e else 'no exp'}\nAI {int(a*100)}%" for e,a in groups],fontsize=8);ax.grid(axis='y',alpha=.3);ax.spines[['top','right']].set_visible(False)
        if i==0:ax.set_title(prov,fontsize=11)
        if j==0:ax.set_ylabel(yl,fontsize=9)
axes[0,0].legend(fontsize=8,frameon=False)
fig.suptitle(('Exchange: '+('neighbour aggregate node' if MODE=='neighbours' else 'fixed-price external market'))+'. 2030 provincial scenario on public data (GEM 2030 fleet, archive 2030 load ratio and costs, official TOU shapes, Helios-derived batches). Hourly load shape unvalidated; external-market proxy; documented assumptions.',fontsize=8,color='dimgray')
fig.tight_layout(rect=[0,0,1,0.95])
for ext in ['png','svg','pdf']:fig.savefig(F/f'regional_2030_cost_emissions{"_neighbours" if MODE=="neighbours" else ""}.{ext}',dpi=160)
print('figure saved')
