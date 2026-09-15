#!/bin/zsh
cd "$(dirname "$0")/../../.."; P=work/figure-env/bin/python; A=work/research/analysis
F='^(case|NOAI|  S|S1rt|S3:|== )'
$P $A/run_regional_2030_s0_s3.py --grid --ext_mode price 2>&1 | grep -E "GRID2030_DONE|Traceback"
$P $A/run_regional_2030_s0_s3.py --grid --ext_mode neighbours 2>&1 | grep -E "GRID2030_DONE|Traceback"
$P $A/summarize_2030_grid.py price | tail -1; $P $A/summarize_2030_grid.py neighbours | tail -1
$P $A/run_mechanism_v2.py 2>&1 | grep -vE "$F" | tail -4
$P $A/run_mechanism_v2_manipulation.py 2>&1 | grep -vE "$F" | tail -5
$P $A/run_2030_multiweather.py 2>&1 | grep -E "MW_DONE|Traceback|fail|timeout"
$P $A/run_2030_cost_montecarlo.py 2>&1 | grep -E "MC_DONE|Traceback|infeasible draws|timeout"
$P - <<'PY' 2>&1 | grep -vE "$F" | tail -30
import sys;sys.argv=['x'];sys.path.insert(0,'work/research/analysis');import pandas as pd,numpy as np
import run_regional_2030_s0_s3 as m
rows=[]
for prov,pk in [('Gansu',17660.),('Guizhou',29000.)]:
    for ext_mode,export in [('price',False),('neighbours',True)]:
        for pkt in [None,pk]:
            for ai in [0.10,0.20]:
                o=m.run(prov,ai,slack_mult=1.0,slack_base_h=6.0,export=export,ext_mode=ext_mode,peak_target_2020=pkt);r=o['results'];b=r['NOAI']
                for c in ['S0','S1','S1rt','S2','S3']:
                    d=r[c]
                    if not d['feasible']:continue
                    rows.append(dict(province=prov,ext_mode=ext_mode,export=export,peak_adjusted=pkt is not None,ai_share=ai,case=c,cost_per_ai_mwh=(d['total_cost']-b['total_cost'])/d['ai_mwh'],co2_per_ai_mwh=(d['emissions_t']-b['emissions_t'])/d['ai_mwh'],new_ocgt=d['new_mw']['ocgt']-b['new_mw']['ocgt'],new_batt=d['new_batt_mw']-b['new_batt_mw'],curtail_NOAI=b['curtail_rate'],peak_2030=o['meta']['peak_2030_mw']))
x=pd.DataFrame(rows);x.to_csv('outputs/research/tables/regional_2030_peak_adjusted_sensitivity.csv',index=False);print('PEAKADJ_DONE')
PY
$P $A/plot_submission_figures.py
echo RERUN_ALL_DONE
