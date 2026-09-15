"""Summarise smoke grids (with and without coal minimum output) as rigid-to-coordinated gaps per AI MWh."""
from pathlib import Path
import pandas as pd,numpy as np,json
ROOT=Path(__file__).resolve().parents[3];T=ROOT/'outputs/research/tables'
out={}
for tag,f in [('coal_min_0',T/'regional_smoke_grid_summary.csv'),('coal_min_0.4',T/'regional_smoke_grid_summary_coalmin40.csv'),('helios_arrivals_official_tou',T/'regional_smoke_grid_summary_helios_offtou.csv')]:
    if not f.exists():continue
    d=pd.read_csv(f);d=d[d.W==24];d=d[d.total_cost.notna()];base=d[d.case=='NOAI'].set_index(['province','export','ai_share']);rows=[]
    for (p,e,a),g in d.groupby(['province','export','ai_share']):
        b=base.loc[(p,e,a)];r={c:g[g.case==c].iloc[0] for c in ['S0','S0b','S1','S2'] if (g.case==c).any()}
        if 'S0b' not in r:r['S0b']=r['S0']
        inc=lambda c:(r[c].total_cost-b.total_cost)/r[c].ai_mwh;co2=lambda c:(r[c].emissions_t-b.emissions_t)/r[c].ai_mwh
        rows.append(dict(province=p,export=bool(e),ai_share=a,cost_S0=inc('S0'),cost_S0b=inc('S0b'),cost_S1=inc('S1'),cost_S2=inc('S2'),gap_S0_S2_pct=(inc('S0')/inc('S2')-1)*100,gap_S1_S2_pct=(inc('S1')/inc('S2')-1)*100,co2_S0=co2('S0'),co2_S2=co2('S2'),curtail_NOAI=b.curtail_rate,curtail_S2=r['S2'].curtail_rate,new_ocgt_S0=r['S0'].new_ocgt,new_ocgt_S2=r['S2'].new_ocgt,new_batt_S0=r['S0'].new_batt_mw,new_batt_S2=r['S2'].new_batt_mw))
    df=pd.DataFrame(rows).round(3);df.to_csv(T/f'regional_smoke_gaps_{tag.replace(".","")}.csv',index=False);out[tag]=df
    print('==',tag);pd.set_option('display.width',250);print(df.to_string(index=False))
