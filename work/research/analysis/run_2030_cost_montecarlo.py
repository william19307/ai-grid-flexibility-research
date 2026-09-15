"""Cost-parameter Monte Carlo for the 2030 provincial scenario (constrained exchange, AI 10% of peak, slack x1+6h).

Draws: coal fuel price U[0.7,1.5]x, gas fuel U[0.7,1.5]x, OCGT/battery/solar/wind investment U[0.7,1.3]x, idle power fraction U[0.15,0.35],
utilisation U[0.5,0.8]. 20 draws per province, 150 s per draw; reports distribution of rigid-to-coordinated and firm-to-coordinated gaps.
Evidence tier: robustness of a public-data scenario, not calibration.
"""
import sys,json;sys.argv=['x']
from pathlib import Path
import numpy as np,pandas as pd,signal
class Timeout(Exception):pass
def _alarm(sig,frm):raise Timeout()
signal.signal(signal.SIGALRM,_alarm)
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'work/research/analysis'))
import run_regional_2030_s0_s3 as m
rng=np.random.default_rng(7);rows=[]
orig=m.costs_2030
for prov in ['Gansu','Jiangsu','Guizhou']:
    for k in range(20):
        f=dict(coal=rng.uniform(0.7,1.5),gas=rng.uniform(0.7,1.5),inv=rng.uniform(0.7,1.3));idle=rng.uniform(0.15,0.35);u=rng.uniform(0.5,0.8)
        def costs():
            c=orig();c['coal_mc']*=f['coal'];c['gas_mc']*=f['gas']
            for key in ['ocgt_inv_yr','onwind_inv_yr','solar_inv_yr','batt_power_inv_yr','batt_energy_inv_yr']:c[key]*=f['inv']
            return c
        m.costs_2030=costs
        signal.alarm(150)
        try:
            o=m.run(prov,0.10,u=u,idle_frac=idle,slack_mult=1.0,slack_base_h=6.0,export=False,ext_mode='price',rt_price=True,tag=f'_mc{k}')
        except Timeout:print('timeout',prov,k);rows.append(dict(province=prov,draw=k,**f,idle=idle,u=u,infeasible=True,timeout=True));continue
        except Exception as ex:print('fail',prov,k,ex);continue
        finally:signal.alarm(0)
        r=o['results']
        if not all(r[c]['feasible'] for c in ['NOAI','S0','S1','S1rt','S2']):rows.append(dict(province=prov,draw=k,**f,idle=idle,u=u,infeasible=True));continue
        b=r['NOAI'];inc=lambda c:(r[c]['total_cost']-b['total_cost'])/r[c]['ai_mwh']
        rows.append(dict(province=prov,draw=k,**f,idle=idle,u=u,gap_S0_S2_pct=(inc('S0')/inc('S2')-1)*100,gap_S1_S2_pct=(inc('S1')/inc('S2')-1)*100,gap_S1rt_S2_pct=(inc('S1rt')/inc('S2')-1)*100,new_ocgt_S0=r['S0']['new_mw']['ocgt']-b['new_mw']['ocgt'],new_ocgt_S2=r['S2']['new_mw']['ocgt']-b['new_mw']['ocgt']))
m.costs_2030=orig
import glob,os
for fpath in glob.glob(str(ROOT/'outputs/research/tables/regional_2030_*_mc*')):os.remove(fpath)
d=pd.DataFrame(rows);d.to_csv(ROOT/'outputs/research/tables/regional_2030_cost_montecarlo.csv',index=False)
print('infeasible draws:',d.get('infeasible',pd.Series(dtype=bool)).fillna(False).groupby(d.province).sum().to_dict());d=d[d.get('infeasible',pd.Series(False,index=d.index)).fillna(False)==False]
q=d.groupby('province')[['gap_S0_S2_pct','gap_S1_S2_pct','gap_S1rt_S2_pct','new_ocgt_S0','new_ocgt_S2']].describe(percentiles=[.1,.5,.9]).round(2)
q.to_csv(ROOT/'outputs/research/tables/regional_2030_cost_montecarlo_summary.csv');pd.set_option('display.width',300);print(q.to_string());print('MC_DONE')
