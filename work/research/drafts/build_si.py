"""Build supplementary_information_v1.4.md (and Supplementary Data 1 workbook) from tables.

v1.4 = v1.3 content with the wide result tables reshaped for a readable PDF:
S7/S8 split into cost / metric / capacity sub-tables, S9/S10/S12 transposed to metric rows,
a column key added, and full-precision tables written to supplementary_data_1.xlsx.
Numbers are unchanged from v1.3 (same source tables, same rounding)."""
from pathlib import Path
import pandas as pd,json
ROOT=Path(__file__).resolve().parents[3];M=ROOT/'outputs/research/manuscript';T=ROOT/'outputs/research/tables'
VER='v1.4';DATE='17 September 2026'
import math
def fmt(v):
    """plain decimal text: no scientific notation, no negative zero, up to 3 decimals"""
    if isinstance(v,bool) or not isinstance(v,(int,float)): return str(v)
    if isinstance(v,float) and math.isnan(v): return 'n/a'
    if float(v)==0: return '0'
    if isinstance(v,float) and not float(v).is_integer(): return f'{v:,.0f}' if abs(v)>=1e5 else f'{v:.3f}'.rstrip('0').rstrip('.')
    return f'{int(v):,}' if abs(v)>=1e5 else str(int(v))
def md(df):
    d=df.copy();align=[]
    for c in d.columns:
        num=pd.api.types.is_numeric_dtype(d[c]) and not pd.api.types.is_bool_dtype(d[c])
        d[c]=d[c].map(fmt) if num else d[c].astype(str);align.append('right' if num else 'left')
    return d.to_markdown(index=False,disable_numparse=True,colalign=align)
mds=lambda df:df.to_markdown(index=False,disable_numparse=True,colalign=['left']+['right']*(df.shape[1]-1))  # pre-formatted string tables
reg=pd.read_csv(T/'data_registry.csv')[['id','dataset','url','evidence_type','licence','status','limits']]
flat=lambda df:df.set_axis(['_'.join(str(x) for x in c if str(x)!='nan') for c in df.columns],axis=1).reset_index()
mw=flat(pd.read_csv(T/'regional_2030_multiweather_summary.csv',header=[0,1],index_col=[0,1]));gp=pd.read_csv(T/'regional_2030_gaps.csv');gn=pd.read_csv(T/'regional_2030_gaps_neighbours.csv');mc=flat(pd.read_csv(T/'regional_2030_cost_montecarlo_summary.csv',header=[0,1],index_col=0));pk=pd.read_csv(T/'provincial_peak_load_plausibility_check.csv');fl=pd.read_csv(T/'gem_fleet_three_provinces_2020_2030.csv');re=json.load(open(T/'multiyear_re_profiles_audit.json'));v1=json.load(open(T/'coupled_grid_compute_validation.json'));v2=json.load(open(T/'reservoir_coupling_validation.json'));ml=json.load(open(T/'mlperf_v40_power_by_benchmark.json'));pka=pd.read_csv(T/'regional_2030_peak_adjusted_sensitivity.csv')
m2=pd.read_csv(T/'mechanism_v2_summary.csv');m2b=pd.read_csv(T/'mechanism_v2_baseline_manipulation.csv')

# --- readable layouts -------------------------------------------------------
KEY7=['province','export','ai_share','slack_mult'];KEY8=['province','ai_share','slack_mult']
COST=['cost_S0','cost_S0e','cost_S1','cost_S3','cost_S1rt','cost_S2']
MET=['red_S0_S2_pct','red_S0_S0e_pct','gap_S0e_S2_pct','share_S1','timing_share_S1','timing_share_S1rt','gap_S1rt_S2_pct']
CAP=['ai_mwh_S0','ai_mwh_S2','new_ocgt_S0','new_ocgt_S2','new_batt_S0']
s7=gp[KEY7+COST+MET+CAP];s8=gn[gn.export][KEY8+COST+MET]
def transpose(df,keys,label='metric'):
    """metric rows x case columns; case label built from key columns"""
    d=df.copy();d.index=[' / '.join(f'{k} {d.loc[i,k]}' if k!='province' else str(d.loc[i,k]) for k in keys) for i in d.index]
    out=d.drop(columns=keys).T.map(fmt);out.index.name=label;return out.reset_index()
mw_t=transpose(mw,['province','idle'])
# Monte Carlo: metric x statistic rows, province columns
mcl=mc.set_index('province').T;mcl.index=pd.MultiIndex.from_tuples([tuple(c.rsplit('_',1)) for c in mcl.index],names=['metric','statistic']);mc_l=mcl.round(3).reset_index()
m2_t=transpose(m2,['province']);m2b_t=transpose(m2b,['province','week'])
s3=pd.DataFrame([dict(benchmark=k,nodes=v['nodes'],idle_kW=v['idle_w']/1000,active_kW=v['active_w']/1000,max_kW=v['max_w']/1000,idle_over_max=v['idle_over_max']) for k,v in ml.items()])
s4=fl[['province','type','mw_2020','units_2020','mw_2030_operating_plus_construction','units_2030','mw_2030_preconstruction_announced']]
s5=pk[['province','anchored_2020_peak_MW','official_reference','reference_value_MW','status']]
s6=pd.DataFrame([dict(province_tech=k.replace('|',' / '),level_scale=v['level_scale'],corr_with_archive_2020=v['corr_with_archive_2020'],top_site_capacity_share=re['sites'][k]['top_share'],n_operating_sites=re['sites'][k]['n_sites']) for k,v in re['scaling'].items()])
s11=pka[['province','ext_mode','export','peak_adjusted','ai_share','case','inc_cost','new_ocgt','new_batt','curtail_NOAI','peak_2030']]

# --- Supplementary Data 1 (full precision, original orientation) ------------
with pd.ExcelWriter(M/'supplementary_data_1.xlsx',engine='openpyxl') as xw:
    pd.DataFrame({'sheet':['S1','S3','S4','S5','S6','S7','S8','S9','S10','S11','S12a','S12b'],'content':['Data registry','MLPerf Training v4.0 node power','GEM-based 2020 and 2030 fleets (MW)','Peak-load plausibility check','Multi-year renewable profiles audit','2030 scenario results, islanded and fixed-price exchange proxy (idle 41%)','2030 scenario results, neighbour-aggregate exchange node (idle 41%)','Multi-weather-year summary (2015-2024)','Cost-parameter Monte Carlo summary','Peak-adjusted sensitivity','Mechanism comparison','Baseline manipulation exposure']}).to_excel(xw,sheet_name='README',index=False)
    for name,df in [('S1',reg),('S3',s3),('S4',s4),('S5',s5),('S6',s6),('S7',s7),('S8',s8),('S9',mw),('S10',mc),('S11',s11),('S12a',m2),('S12b',m2b)]:df.to_excel(xw,sheet_name=name,index=False)

si=f"""# Supplementary Information

**Efficient modes, not load shifting, deliver most of the grid value of flexible AI computing**

William Wei^1,2,\\*^, Lanlan Liu (刘岚岚)^3^ — ^1^ School of Computer Science, Faculty of Engineering and Physical Sciences, University of Leeds, Leeds, UK; ^2^ Spatial Computing (Fujian) Technology Co., Ltd., Fuzhou, China; ^3^ School of Public Administration, Fujian Normal University, Fuzhou, China; \\* qkfp0742@leeds.ac.uk

Supplementary Information {VER}, {DATE}. Base case: idle power 41% of nameplate; 25% is a sensitivity. Metric: total incremental system cost for the same computing work (EUR per representative week, expected over four weeks); reductions are relative to rigid full-speed operation (S0); shifting value is (cost S0e − cost S2)/cost S2. Full-precision, machine-readable versions of every table are provided as Supplementary Data 1 (spreadsheet, one sheet per table) and in the code repository under `outputs/research/tables/`.

**Column key (Tables S7–S12).** `cost_X`: incremental system cost under scenario X, i.e. total expected system cost with the AI pool minus that without it (EUR per representative week). `red_A_B_pct` = (1 − cost B / cost A) × 100. `gap_A_B_pct` = (cost A / cost B − 1) × 100. `share_S1` = (cost S0 − cost S1)/(cost S0 − cost S2), the share of total coordination value captured by the tariff-driven firm. `timing_share_X` = (cost S0e − cost X)/(cost S0e − cost S2), the share of shifting value realised by scenario X (negative when shifting raises cost above no-shifting operation). `ai_mwh_X`: AI pool energy under scenario X (MWh per representative week). `new_ocgt_X`, `new_batt_X`: new open-cycle gas-turbine and battery capacity (MW) relative to the reference without AI. `curtail_NOAI`: curtailment share in the reference without AI. `idle`: idle power as a fraction of nameplate. `ai_share`: AI pool as a share of the 2030 provincial peak; `slack_mult`: multiplier on observed queueing wait in the deadline (1 or 3); `export`: interprovincial exchange allowed. In Table S12, `system_cost_X` is the total system cost and savings are in EUR per representative week.

## S1. Data registry
{md(reg)}

## S2. Model verification records
Joint planning–operation LP: {v1.get('n_checks',118)} checks in total, of which 100 are independent oracle cases (60 screening-curve capacity cases, 40 enumerated task-assignment cases); reservoir-cascade extension: {v2.get('n_checks',74)} checks, of which 60 are independent dynamic-programming cases; task model: 120 exhaustive assignment oracles and 256 diagnostic cases; commitment-cost model: 72 frontiers, 360 points, dual and finite-difference checks.

## S3. MLPerf Training v4.0 node power (8×H100 nodes)
{md(s3)}

## S4. GEM-based 2020 and 2030 fleets, three provinces (MW)
{md(s4)}

## S5. Peak-load plausibility check
{md(s5)}

## S6. Multi-year renewable profiles: site coverage and agreement with archive 2020 profiles
{md(s6)}

## S7. 2030 scenario results, islanded (export = False) and fixed-price exchange proxy (export = True), idle 41%

### S7a. Incremental system cost by scenario (EUR per representative week)
{md(gp[KEY7+COST])}

### S7b. Reductions, gaps and realised shares
{md(gp[KEY7+MET])}

### S7c. AI energy and new capacity
{md(gp[KEY7+CAP])}

## S8. 2030 scenario results, neighbour-aggregate exchange node (export = True rows), idle 41%

### S8a. Incremental system cost by scenario (EUR per representative week)
{md(gn[gn.export][KEY8+COST])}

### S8b. Reductions, gaps and realised shares
{md(gn[gn.export][KEY8+MET])}

## S9. Multi-weather-year summary (islanded, export = False, AI 10%; min/median/max across ten weather years, 2015–2024)
Rows are metric_statistic; columns are province / idle-power fraction.

{mds(mw_t)}

## S10. Cost-parameter Monte Carlo summary (islanded, export = False, AI 10%; 20 feasible draws per province, infeasible or timed-out draws excluded)
Rows are metric and statistic (count, mean, standard deviation, minimum, 10th/50th/90th percentile, maximum); columns are provinces.

{md(mc_l)}

## S11. Peak-adjusted sensitivity (incremental cost, EUR per representative week)
{md(s11)}

## S12. Mechanism comparison

### S12a. Settlement designs under identical tasks and reliability (rows are metrics; columns are provinces)
{mds(m2_t)}

### S12b. Baseline-manipulation exposure of the event contract (rows are metrics; columns are province / week)
{mds(m2b_t)}
"""
open(M/f'supplementary_information_{VER}.md','w',encoding='utf-8').write(si);print(f'SI {VER} written; supplementary_data_1.xlsx written')
