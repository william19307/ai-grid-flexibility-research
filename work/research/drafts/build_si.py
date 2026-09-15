"""Build supplementary_information_v1.2.md from tables (authors included)."""
from pathlib import Path
import pandas as pd,json
ROOT=Path(__file__).resolve().parents[3];M=ROOT/'outputs/research/manuscript';T=ROOT/'outputs/research/tables'
md=lambda df:df.round(3).to_markdown(index=False)
reg=pd.read_csv(T/'data_registry.csv')[['id','dataset','url','evidence_type','license','status','limits']]
mw=pd.read_csv(T/'regional_2030_multiweather_summary.csv');gp=pd.read_csv(T/'regional_2030_gaps.csv');gn=pd.read_csv(T/'regional_2030_gaps_neighbours.csv');mc=pd.read_csv(T/'regional_2030_cost_montecarlo_summary.csv');pk=pd.read_csv(T/'provincial_peak_load_plausibility_check.csv');fl=pd.read_csv(T/'gem_fleet_three_provinces_2020_2030.csv');re=json.load(open(T/'multiyear_re_profiles_audit.json'));v1=json.load(open(T/'coupled_grid_compute_validation.json'));v2=json.load(open(T/'reservoir_coupling_validation.json'));ml=json.load(open(T/'mlperf_v40_power_by_benchmark.json'));pka=pd.read_csv(T/'regional_2030_peak_adjusted_sensitivity.csv')
si=f"""# Supplementary Information

**Realising the power-system value of flexible AI computing: service constraints and price signals in China**

William Wei^1,\\*^, Lanlan Liu (刘岚岚)^1^ — ^1^ [Affiliation, City, China]; \\* weihong_william@icloud.com

Supplementary Information v1.2, 15 September 2026. Base case: idle power 41% of nameplate; 25% is a sensitivity.

## S1. Data registry
{md(reg)}

## S2. Model verification records
Joint planning–operation LP: {v1.get('n_checks',118)} checks in total, of which 100 are independent oracle cases (60 screening-curve capacity cases, 40 enumerated task-assignment cases); reservoir-cascade extension: {v2.get('n_checks',74)} checks, of which 60 are independent dynamic-programming cases; task model: 120 exhaustive assignment oracles and 256 diagnostic cases; commitment-cost model: 72 frontiers, 360 points, dual and finite-difference checks.

## S3. MLPerf Training v4.0 node power (8×H100 nodes)
{md(pd.DataFrame([dict(benchmark=k,nodes=v['nodes'],idle_kW=v['idle_w']/1000,active_kW=v['active_w']/1000,max_kW=v['max_w']/1000,idle_over_max=v['idle_over_max']) for k,v in ml.items()]))}

## S4. GEM-based 2020 and 2030 fleets, three provinces (MW)
{md(fl[['province','type','mw_2020','units_2020','mw_2030_operating_plus_construction','units_2030','mw_2030_preconstruction_announced']])}

## S5. Peak-load plausibility check
{md(pk[['province','anchored_2020_peak_MW','official_reference','reference_value_MW','status']])}

## S6. Multi-year renewable profiles: site coverage and agreement with archive 2020 profiles
{md(pd.DataFrame([dict(province_tech=k,level_scale=v['level_scale'],corr_with_archive_2020=v['corr_with_archive_2020'],top_site_capacity_share=re['sites'][k]['top_share'],n_operating_sites=re['sites'][k]['n_sites']) for k,v in re['scaling'].items()]))}

## S7. 2030 scenario gaps, fixed-price exchange proxy (idle 41%)
{md(gp[['province','export','ai_share','slack_mult','cost_S0','cost_S1','cost_S1rt','cost_S2','cost_S3','gap_S0_S2_pct','gap_S1_S2_pct','gap_S1rt_S2_pct','new_ocgt_S0','new_ocgt_S2','new_batt_S0']])}

## S8. 2030 scenario gaps, neighbour-aggregate exchange node (idle 41%)
{md(gn[['province','export','ai_share','slack_mult','cost_S0','cost_S1','cost_S1rt','cost_S2','gap_S0_S2_pct','gap_S1_S2_pct','gap_S1rt_S2_pct']])}

## S9. Multi-weather-year summary (constrained exchange, AI 10%)
{md(mw)}

## S10. Cost-parameter Monte Carlo summary (20 draws per province; infeasible or timed-out draws excluded)
{md(mc)}

## S11. Peak-adjusted sensitivity
{md(pka)}

## S12. Mechanism comparison
{md(pd.read_csv(T/'mechanism_v2_summary.csv'))}

{md(pd.read_csv(T/'mechanism_v2_baseline_manipulation.csv'))}
"""
open(M/'supplementary_information_v1.2.md','w',encoding='utf-8').write(si);print('SI v1.2 written')
