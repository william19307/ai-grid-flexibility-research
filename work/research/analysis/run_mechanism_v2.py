"""Mechanism v2 experiments (constrained exchange, AI 10% of peak, slack x1+6h, price-mode exchange, 2020 weather):
(a) Baseline manipulation in event-based commitment: compensation floor when the settlement baseline is the firm's own
    tariff-optimal schedule (S1) versus an inflated full-speed baseline (S0). The difference is the manipulation rent.
(b) Continuous signal without baseline: the firm faces the coordinated solution's hourly marginal-cost shape (S1rt) and is
    settled on metered consumption; no baseline exists, so no manipulation rent. Reported: system cost vs S1, firm bill
    change under the real-time shape vs tariff at equal mean price (transfer), and gap to S2.
Evidence tier: public-data scenario; mechanism outcomes are model results under stated assumptions.
"""
import sys;sys.argv=['x']
from pathlib import Path
import numpy as np,pandas as pd,json
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'work/research/analysis'));sys.path.insert(0,str(ROOT/'work/research/models'))
import run_regional_2030_s0_s3 as m
from response_cost import cost_at_max_response
from sequential_tasks import schedule
rows=[]
for prov in ['Gansu','Jiangsu','Guizhou']:
    o=m.run(prov,0.10,slack_mult=1.0,slack_base_h=6.0,export=False,ext_mode='price',tag='_mechv2');r=o['results'];meta=o['meta']
    # re-derive per-week objects by calling internals: we recompute S1 schedule, S0 baseline and events from the JSON meta
    js=json.load(open(m.OUT/f"regional_2030_{m.CODE[prov]}_2030_ai10_noexport_sm1_sb6_mechv2.json"))
    comp_own=sum(v.get('compensation_floor',0) for v in js['meta']['s3'].values())*0.25
    commit_own=np.mean([v.get('commitment_mw',0) for v in js['meta']['s3'].values()])
    rows.append(dict(province=prov,system_cost_S1=r['S1']['total_cost'],system_cost_S3=r['S3']['total_cost'],system_cost_S1rt=r['S1rt']['total_cost'],system_cost_S2=r['S2']['total_cost'],
        s3_saving_vs_S1=r['S1']['total_cost']-r['S3']['total_cost'],s3_compensation_floor_own_baseline=comp_own,s3_mean_commitment_mw=commit_own,
        s1rt_saving_vs_S1=r['S1']['total_cost']-r['S1rt']['total_cost'],gap_S1rt_S2_pct=(r['S1rt']['total_cost']-r['S2']['total_cost'])/max(1e-9,(r['S2']['total_cost']-r['NOAI']['total_cost']))*100,system_cost_S0=r['S0']['total_cost'],system_cost_S0e=r['S0e']['total_cost'],system_cost_NOAI=r['NOAI']['total_cost'],n_events={k:len(v.get('events',[])) for k,v in meta['s3'].items()},
        ai_mwh_S1=r['S1']['ai_mwh'],ai_mwh_S1rt=r['S1rt']['ai_mwh']))
d=pd.DataFrame(rows);d.to_csv(m.OUT/'mechanism_v2_summary.csv',index=False);pd.set_option('display.width',250);print(d.round(1).to_string(index=False))
