"""Baseline-manipulation rent for the event-based commitment (uses the same mode rule and inputs as run_regional_2030_s0_s3)."""
import sys;sys.argv=['x']
from pathlib import Path
import numpy as np,pandas as pd,json
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'work/research/analysis'));sys.path.insert(0,str(ROOT/'work/research/models'))
import run_regional_2030_s0_s3 as m, run_regional_smoke_s0_s1_s2 as base
from sequential_tasks import Job,schedule,baseline_asap
from response_cost import cost_at_max_response
rows=[]
for prov in ['Guizhou','Jiangsu','Gansu']:
    js=json.load(open(m.OUT/f"regional_2030_{m.CODE[prov]}_2030_ai10_noexport_sm1_sb6_mechv2.json"));meta=js['meta']
    P_full=meta['assumptions']['ai_nameplate_mw'];idle_frac=meta['assumptions']['idle_fraction'];idle=idle_frac*P_full
    q,pr,_=base.dvfs_modes();keep=pr>idle_frac+0.02;q,pr=q[keep],pr[keep];mode_power=P_full*pr;c=m.costs_2030()
    for name,start in m.WEEK_STARTS.items():
        ev=meta['s3'][name].get('events',[])
        if not ev:continue
        bb,_=m.helios_queue_jobs(168,0.7,start%24,1.0,6.0,seed=start);jobs=[Job(b.name,b.release,b.deadline,b.work) for b in bb]
        prices=base.tariff_shape(np.arange(start,start+168)%24,'official',prov)*c['coal_mc']*1.5
        s1=np.array(schedule(jobs,q,mode_power,168,idle,prices=prices)['slot_average_power']);s0=baseline_asap(jobs,1.0,float(mode_power[-1]),168,idle)
        own=cost_at_max_response(jobs,q,mode_power,168,idle,s1,ev,prices);inf=cost_at_max_response(jobs,q,mode_power,168,idle,s0,ev,prices)
        rows.append(dict(province=prov,week=name,n_events=len(ev),commit_own_mw=own.get('commitment',np.nan),comp_own=own.get('minimum_total_compensation_for_weak_participation',np.nan),commit_inflated_mw=inf.get('commitment',np.nan),comp_inflated=inf.get('minimum_total_compensation_for_weak_participation',np.nan),inflated_minus_own_event_power_mw=float((s0[ev]-s1[ev]).mean())))
d=pd.DataFrame(rows);d.to_csv(m.OUT/'mechanism_v2_baseline_manipulation.csv',index=False);pd.set_option('display.width',250);print(d.round(1).to_string(index=False))
