"""Multi-weather-year 2030 runs: ERA5-derived wind/solar profiles 2015-2024 for the three provinces, constrained exchange,
AI 10% of peak, slack x1+6h, idle fraction 0.41 (MLPerf node-level idle/max, base case) and 0.25 (sensitivity). Hydro and load
shapes remain the archive/anchored 2020 series (limitation: only wind and solar vary by weather year)."""
import sys;sys.argv=['x']
from pathlib import Path
import numpy as np,pandas as pd,signal
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'work/research/analysis'))
import run_regional_2030_s0_s3 as m
class TO(Exception):pass
signal.signal(signal.SIGALRM,lambda s,f:(_ for _ in ()).throw(TO()))
rows=[]
for prov in ['Gansu','Jiangsu','Guizhou']:
    for idle in [0.25,0.41]:
        for wy in range(2015,2025):
            signal.alarm(200)
            try:o=m.run(prov,0.10,idle_frac=idle,slack_mult=1.0,slack_base_h=6.0,export=False,ext_mode='price',weather_year=wy,tag=f'_idle{int(idle*100)}')
            except TO:print('timeout',prov,idle,wy);continue
            except Exception as ex:print('fail',prov,idle,wy,ex);continue
            finally:signal.alarm(0)
            r=o['results']
            if not all(r[c]['feasible'] for c in ['NOAI','S0','S1','S1rt','S2']):rows.append(dict(province=prov,idle=idle,weather_year=wy,infeasible=True));continue
            b=r['NOAI'];inc=lambda c:(r[c]['total_cost']-b['total_cost'])/r[c]['ai_mwh'];co2=lambda c:(r[c]['emissions_t']-b['emissions_t'])/r[c]['ai_mwh']
            rows.append(dict(province=prov,idle=idle,weather_year=wy,cost_S0=inc('S0'),cost_S1=inc('S1'),cost_S1rt=inc('S1rt'),cost_S2=inc('S2'),gap_S0_S2_pct=(inc('S0')/inc('S2')-1)*100,gap_S1_S2_pct=(inc('S1')/inc('S2')-1)*100,gap_S1rt_S2_pct=(inc('S1rt')/inc('S2')-1)*100,co2_S0=co2('S0'),co2_S2=co2('S2'),curtail_NOAI=b['curtail_rate'],curtail_S2=r['S2']['curtail_rate'],new_ocgt_S0=r['S0']['new_mw']['ocgt']-b['new_mw']['ocgt'],new_ocgt_S2=r['S2']['new_mw']['ocgt']-b['new_mw']['ocgt'],new_batt_S0=r['S0']['new_batt_mw']-b['new_batt_mw']))
import glob,os
for f in glob.glob(str(ROOT/'outputs/research/tables/regional_2030_*_wy20*')):os.remove(f)
d=pd.DataFrame(rows);d.to_csv(ROOT/'outputs/research/tables/regional_2030_multiweather.csv',index=False)
ok=d[d.get('infeasible',pd.Series(False,index=d.index)).fillna(False)==False]
q=ok.groupby(['province','idle'])[['gap_S0_S2_pct','gap_S1_S2_pct','gap_S1rt_S2_pct','curtail_NOAI','new_ocgt_S0','new_ocgt_S2']].agg(['min','median','max']).round(2)
q.to_csv(ROOT/'outputs/research/tables/regional_2030_multiweather_summary.csv');pd.set_option('display.width',300);print(q.to_string());print('MW_DONE')
