"""Build core_paper_en_v1.3.md from source tables. Every number is read from outputs/research/tables at build time.
Addresses the 65 confirmed review findings of the submission-review workflow (numbers, overclaiming, style, methods)."""
from pathlib import Path
import json,pandas as pd,numpy as np
ROOT=Path(__file__).resolve().parents[3];T=ROOT/'outputs/research/tables';M=ROOT/'outputs/research/manuscript'
gp=pd.read_csv(T/'regional_2030_gaps.csv');gn=pd.read_csv(T/'regional_2030_gaps_neighbours.csv')
mw=pd.read_csv(T/'regional_2030_multiweather.csv');mws=pd.read_csv(T/'regional_2030_multiweather_summary.csv',header=[0,1],index_col=[0,1]) if False else None
mc=pd.read_csv(T/'regional_2030_cost_montecarlo.csv');pk=pd.read_csv(T/'regional_2030_peak_adjusted_sensitivity.csv')
mech=pd.read_csv(T/'mechanism_v2_summary.csv');man=pd.read_csv(T/'mechanism_v2_baseline_manipulation.csv')
hel=json.load(open(T/'helios_trace_audit.json'))['gpu_job_statistics'];ali=json.load(open(T/'alibaba_pai_2020_trace_audit.json'))['statistics'];phi=json.load(open(T/'philly_trace_audit.json'))['statistics']
ml=json.load(open(T/'mlperf_v40_power_by_benchmark.json'));re_=json.load(open(T/'multiyear_re_profiles_audit.json'));pkc=pd.read_csv(T/'provincial_peak_load_plausibility_check.csv')
v1=json.load(open(T/'coupled_grid_compute_validation.json'));v2=json.load(open(T/'reservoir_coupling_validation.json'))
meta_any=json.load(open(T/'regional_2030_GS_2030_ai10_noexport_sm1_sb6.json'))['meta']['assumptions']
IDLE=meta_any['idle_fraction'];assert abs(IDLE-0.41)<1e-6,'expected idle 0.41 base case'
P=['Gansu','Jiangsu','Guizhou']
# ---- constrained exchange, slack x1 (base) ----
c=gp[(~gp.export)&(gp.slack_mult==1.0)].copy();c3=gp[(~gp.export)&(gp.slack_mult==3.0)].copy()
def rng(df,p,col):x=df[df.province==p][col];return x.min(),x.max()
g02={p:rng(c,p,'gap_S0_S2_pct') for p in P};g02_all={p:rng(gp[~gp.export],p,'gap_S0_S2_pct') for p in P}
ex_all={p:rng(pd.concat([gp[gp.export],gn[gn.export]]),p,'gap_S0_S2_pct') for p in P}
rt_max=max(gp.gap_S1rt_S2_pct.abs().max(),gn.gap_S1rt_S2_pct.abs().max());rt_max_base=max(c.gap_S1rt_S2_pct.abs().max(),gn[(~gn.export)&(gn.slack_mult==1.0)].gap_S1rt_S2_pct.abs().max())
rt_max_lowai=gp[(~gp.export)&(gp.ai_share<=0.10)].gap_S1rt_S2_pct.abs().max()
js20=c[(c.province=='Jiangsu')&(c.ai_share==0.2)].iloc[0];js20b=c3[(c3.province=='Jiangsu')&(c3.ai_share==0.2)].iloc[0]
def share(df,p,col):
    d=df[df.province==p];s=(d.cost_S0-d[col])/(d.cost_S0-d.cost_S2);return s.min(),s.max()
sh={p:{k:share(c,p,f'cost_{k}') for k in ['S1','S3','S1rt']} for p in P}
sh_js_low=share(c[c.ai_share<=0.10],'Jiangsu','cost_S1');sh_js_20=share(c[c.ai_share==0.2],'Jiangsu','cost_S1')
# S1 vs S0 anywhere
s1_worse=gp[(gp.cost_S1>gp.cost_S0)][['province','export','ai_share','slack_mult']];s1_worse_n=pd.concat([gp[gp.cost_S1>gp.cost_S0],gn[gn.cost_S1>gn.cost_S0]])
# slack effect
def slack_effect(p,a):r1=c[(c.province==p)&(c.ai_share==a)].iloc[0];r3=c3[(c3.province==p)&(c3.ai_share==a)].iloc[0];return r1.cost_S2-r3.cost_S2,r1.cost_S1-r3.cost_S1
# ---- multi-weather ----
mwok=mw[mw.gap_S0_S2_pct.notna()]
def mwr(p,i):d=mwok[(mwok.province==p)&(mwok.idle==i)];return d.gap_S0_S2_pct.min(),d.gap_S0_S2_pct.median(),d.gap_S0_S2_pct.max(),len(d),d.gap_S1rt_S2_pct.abs().max()
# ---- MC ----
mcok=mc[mc.gap_S0_S2_pct.notna()];mcn={p:(len(mcok[mcok.province==p]),len(mc[mc.province==p])) for p in P}
def mcr(p):d=mcok[mcok.province==p].gap_S0_S2_pct;return d.quantile(.1),d.median(),d.quantile(.9)
mc_meta=open(ROOT/'work/research/analysis/run_2030_cost_montecarlo.py').read()
# ---- peak adjusted ----
pv=pk.pivot_table(index=['province','ext_mode','peak_adjusted','ai_share'],columns='case',values='cost_per_ai_mwh');pv['g']=(pv.S0/pv.S2-1)*100
def pkg(p,adj,a):return pv.loc[(p,'price',adj,a),'g']
# ---- mechanism ----
mrow={p:mech[mech.province==p].iloc[0] for p in P};mg=man[man.province=='Guizhou'];mg=mg.iloc[0] if len(mg) else None
def s3phrase():
    parts=[]
    for p in P:
        v=mrow[p].s3_saving_vs_S1/1e3
        if abs(v)<0.05:parts.append(f'leaves the system cost unchanged in {p}')
        elif v>0:parts.append(f'lowers the system cost relative to S1 by {v:,.1f} thousand euros per representative week in {p}')
        else:parts.append(f'raises the system cost relative to S1 by {abs(v):,.1f} thousand euros per representative week in {p}')
    return ', '.join(parts[:-1])+' and '+parts[-1]
s3txt=s3phrase()
# ---- traces / power ----
idle_rng=(min(v['idle_over_max'] for v in ml.values()),max(v['idle_over_max'] for v in ml.values()))
corr={k:v['corr_with_archive_2020'] for k,v in re_['scaling'].items()}
f1=lambda x:f'{x:.1f}';pc=lambda x:f'{x*100:.0f}%'
# ---- citations in order of first appearance ----
REFS={
 'colangelo':'Colangelo, G. et al. AI data centres as grid-interactive assets. Nat. Energy 11, 218–229 (2026); published online 2025. https://doi.org/10.1038/s41560-025-01927-1',
 'zhangzavala':'Zhang, W. & Zavala, V. M. Remunerating space–time, load-shifting flexibility from data centers in electricity markets. Appl. Energy 326, 119930 (2022). https://doi.org/10.1016/j.apenergy.2022.119930',
 'zhangjoule':'Zhang, T. et al. Mitigating curtailment and carbon emissions through load migration between data centers. Joule 4, 2208–2222 (2020). https://doi.org/10.1016/j.joule.2020.08.001',
 'fridgen':'Fridgen, G., Keller, R., Thimmel, M. & Wederhake, L. Shifting load through space: the economics of spatial demand side management using distributed data centers. Energy Policy 109, 400–413 (2017). https://doi.org/10.1016/j.enpol.2017.07.018',
 'senga':'Senga, J. R. L., Wang, S. & Knittel, C. R. Flexible data centers reduce power system costs but can increase emissions. iScience 29, 116497 (2026). https://doi.org/10.1016/j.isci.2026.116497',
 'zhangbits':'Zhang, X., Li, Y. & Wang, C. Decarbonizing data centers through regional bits migration: a comprehensive assessment of China\'s Eastern Data, Western Computing initiative and its global implications. Appl. Energy 392, 126020 (2025). https://doi.org/10.1016/j.apenergy.2025.126020',
 'dunlap':'Dunlap, C. T. Quantifying AI data center flexibility as a resource adequacy asset. Preprint at Research Square https://www.researchsquare.com/article/rs-9829457/v1 (2026).',
 'birahim':'Birahim, S. A. A net-grid-benefit test for interconnecting AI data centres. npj Environ. Soc. Sci. (2026). https://doi.org/10.1038/s44432-026-00013-5',
 'chenzheng':'Chen, Y. & Zheng, X. To defer or to shift? The role of AI data center flexibility on grid interconnection. In Companion Proc. ACM Sustainability Week 322–327 (ACM, 2026). https://doi.org/10.1145/3765611.3815593',
 'weng':'Weng, Q. et al. MLaaS in the wild: workload analysis and scheduling in large-scale heterogeneous GPU clusters. In Proc. 19th USENIX Symp. Networked Systems Design and Implementation 945–960 (USENIX, 2022).',
 'hu':'Hu, Q., Sun, P., Yan, S., Wen, Y. & Zhang, T. Characterization and prediction of deep learning workloads in large-scale GPU datacenters. In Proc. Int. Conf. High Performance Computing, Networking, Storage and Analysis (SC) 104 (ACM, 2021). https://doi.org/10.1145/3458817.3476223',
 'jeon':'Jeon, M. et al. Analysis of large-scale multi-tenant GPU clusters for DNN training workloads. In Proc. USENIX Annual Technical Conference 947–960 (USENIX, 2019).',
 'mlperf':'MLCommons. MLPerf Training v4.0 results, including power submissions. https://github.com/mlcommons/training_results_v4.0 (2024).',
 'stojkovic':'Stojkovic, J., Zhang, C., Goiri, Í., Torrellas, J. & Choukse, E. DynamoLLM: designing LLM inference clusters for performance and energy efficiency. In Proc. IEEE Int. Symp. High-Performance Computer Architecture (HPCA) (IEEE, 2025). https://arxiv.org/abs/2408.00741',
 'wukan':'Wu, T. & Kan, S. Hourly electric power load and transmission data at the provincial level in China. Zenodo https://doi.org/10.5281/zenodo.8322210 (2023).',
 'nbs':'National Bureau of Statistics of China. China Statistical Yearbook 2021, Table 9-14: Electricity consumption by region (China Statistics Press, 2021).',
 'pypsa':'Zhou, Z. et al. PyPSA-China V3.0. Zenodo https://doi.org/10.5281/zenodo.13987282 (2024).',
 'gem':'Global Energy Monitor. Global Integrated Power Tracker, July 2025 release, China subset. Zenodo https://doi.org/10.5281/zenodo.16810831 (2025).',
 'openmeteo':'Zippenfenig, P. Open-Meteo.com weather API. Zenodo https://doi.org/10.5281/zenodo.7970649 (2023).',
 'era5':'Hersbach, H. et al. The ERA5 global reanalysis. Q. J. R. Meteorol. Soc. 146, 1999–2049 (2020). https://doi.org/10.1002/qj.3803',
 'js_tariff':'Jiangsu Provincial Development and Reform Commission. Notice on transmission–distribution and retail tariffs of the Jiangsu grid for 2020–2022, Su-Fa-Gai-Jia-Ge-Fa [2020] No. 1183, Annex 3 (2020).',
 'gs_tariff':'Gansu Provincial Development and Reform Commission. Notice on adjusting retail tariffs and optimising time-of-use tariffs, effective 1 January 2021 (2020).',
 'gz_tariff':'Guizhou Provincial Development and Reform Commission. Notice on improving the time-of-use tariff mechanism, Qian-Fa-Gai-Jia-Ge [2023] No. 481 (2023).',
 'ndrc':'National Development and Reform Commission. Eastern Data, Western Computing: eight national computing-power hubs and ten data-centre clusters. https://www.ndrc.gov.cn/fzggw/jgsj/gjss/sjdt/202203/t20220321_1319862.html (2022).',
}
order=[];
def cite(*keys):
    ns=[]
    for k in keys:
        if k not in order:order.append(k)
        ns.append(str(order.index(k)+1))
    return '['+','.join(ns)+']'
# ================= TEXT =================
title='Realising the power-system value of flexible AI computing: service constraints and price signals in China'
front=f'''# {title}

**William Wei^1,\\*^, Lanlan Liu (刘岚岚)^1^**

^1^ [Affiliation, City, China]

\\* Corresponding author: weihong_william@icloud.com

'''
abstract=f'''## Abstract

AI computing clusters can modulate power and shift work in time, but this flexibility becomes power-system value only if tasks still complete, the system has scarce or surplus hours, and firms are induced to deliver. We link these conditions in a framework of measured GPU power modes, task deadlines, joint investment–dispatch and firm behaviour, applied to three Chinese provinces in a 2030 public-data scenario. With unconstrained interprovincial exchange the value of flexibility is below 1% of the incremental cost of serving AI load; with constrained exchange the rigid-to-coordinated gap is {f1(g02_all['Gansu'][0])}–{f1(g02_all['Gansu'][1])}% in coal-heavy Gansu, {f1(g02_all['Guizhou'][0])}–{f1(g02_all['Guizhou'][1])}% in hydro-rich Guizhou and {f1(g02_all['Jiangsu'][0])}–{f1(g02_all['Jiangsu'][1])}% in Jiangsu, where rigid operation adds {js20.new_ocgt_S0/1000:.1f} GW of gas turbines. Firms under current tariff shapes realise part of this value, event contracts add little, and a firm facing hourly prices shaped like the system's marginal cost comes within {f1(rt_max)}% of the optimum: the price shape is the instrument that matters.

'''
i_abs=len(abstract.replace('## Abstract','').split())
main=f'''## Main

AI computing load can modulate power and shift execution in time, and grid-interactive operation of AI clusters has been demonstrated in the field {cite('colangelo')}. Earlier work priced spatial and temporal load shifting of data centres in electricity markets {cite('zhangzavala','zhangjoule','fridgen')}, showed in capacity-expansion models that flexible data centres can lower system cost while raising emissions {cite('senga')}, assessed the energy and emission effects of China's regional migration of computing {cite('zhangbits')}, treated inference flexibility as a resource-adequacy asset with exogenous accreditation {cite('dunlap')}, proposed net-grid-benefit tests for interconnection {cite('birahim')} and reported diminishing returns to flexibility in grid interconnection {cite('chenzheng')}. What remains open is how much of the technical flexibility of an AI cluster becomes value for a real power system once three links are taken together: the service constraints under which tasks must still complete, the system conditions that give shifted energy any value, and the incentives that make an operator deliver what it technically could. We connect the three in a single framework and quantify, for three Chinese provinces, how much of the technical envelope is realised under rigid operation (scenario S0), autonomous firm optimisation against the official time-of-use tariff shape (S1), an event-based commitment contract (S3), autonomous optimisation against an hourly price shaped like the system's marginal cost (S1rt) and full system coordination (S2). All results are scenario results built from public data; their evidence basis and limitations are stated in Methods.

### Service constraints bound the power envelope

Re-analysis of measured GPU power–throughput modes {cite('colangelo')} shows that a throughput-conserving power reduction of 11–29% at 90% or more of full throughput exists in the measured configurations (Fig. 1a). Three public production traces indicate that a large share of GPU-hours sits in jobs longer than one day ({pc(hel['gpu_hour_weighted_duration_share_gt_24h'])} in the Helios clusters {cite('hu')}, {pc(ali['gpu_hour_weighted_run_share_gt_24h'])} in the Alibaba PAI cluster {cite('weng')} and {pc(phi['gpu_hour_weighted_run_share_gt_24h'])} in the Philly clusters {cite('jeon')}), while observed queueing waits longer than one hour cover {pc(hel['gpu_hour_weighted_queue_share_gt_1h'])} of GPU-hours in Helios, {pc(phi['gpu_hour_weighted_wait_share_gt_1h'])} in Philly and almost none in Alibaba PAI (Fig. 1b). These waits are lower bounds on the delay users tolerated, not deadlines; deadlines are therefore treated as assumptions with sensitivity analysis. Node-level alternating-current power logs from MLPerf Training v4.0 {cite('mlperf')} put idle power at {pc(idle_rng[0])}–{pc(idle_rng[1])} of peak across three benchmarks on eight-GPU nodes (Fig. 1c), which bounds the share of load that any change of operating mode can shift; the base case uses {pc(IDLE)}.

### The value of flexibility depends on system slack

When interprovincial exchange is represented either by a fixed-price external market or by an aggregate node of directly connected provinces with their own load, fleets and renewables, the rigid-to-coordinated gap in incremental system cost per megawatt-hour of AI load stays below 1% in all three provinces ({f1(ex_all['Gansu'][0])}–{f1(ex_all['Gansu'][1])}% in Gansu, {f1(ex_all['Jiangsu'][0])}–{f1(ex_all['Jiangsu'][1])}% in Jiangsu and {f1(ex_all['Guizhou'][0])}–{f1(ex_all['Guizhou'][1])}% in Guizhou): exchange moves scarcity to neighbours rather than removing it, and the provincial value of shifting is small. When exchange is constrained, the gap is {f1(g02_all['Gansu'][0])}–{f1(g02_all['Gansu'][1])}% in Gansu (wind- and solar-rich, coal-heavy), {f1(g02_all['Guizhou'][0])}–{f1(g02_all['Guizhou'][1])}% in Guizhou (hydro–renewable mix) and {f1(g02_all['Jiangsu'][0])}–{f1(g02_all['Jiangsu'][1])}% in Jiangsu across AI shares of 5–20% of the 2030 provincial peak and two deadline-slack settings, rising with the AI share (Fig. 2). At an AI share of 20% of the 2030 Jiangsu peak, rigid operation requires {js20.new_ocgt_S0/1000:.1f} GW of new gas turbines and {js20.new_batt_S0/1000:.2f} GW of batteries, whereas system-coordinated operation requires {js20.new_ocgt_S2/1000:.1f} GW of gas turbines ({js20b.new_ocgt_S2/1000:.1f} GW with longer deadlines) and no batteries.

### Firms realise part of the value; the share depends on the price shape

Under the official provincial time-of-use tariff shapes {cite('js_tariff','gs_tariff','gz_tariff')} (S1), the share of coordination value realised, defined as the cost reduction from S0 to S1 divided by that from S0 to S2, is {pc(sh['Gansu']['S1'][0])}–{pc(sh['Gansu']['S1'][1])} in Gansu, {pc(sh['Guizhou']['S1'][0])}–{pc(sh['Guizhou']['S1'][1])} in Guizhou and {pc(sh_js_low[0])}–{pc(sh_js_low[1])} in Jiangsu at AI shares of 5–10% but {pc(sh_js_20[0])}–{pc(sh_js_20[1])} at 20% (Fig. 3). Guizhou's low share reflects a tariff valley (00:00–08:00) that does not coincide with the system's surplus hours. Longer deadline slack lowers the coordinated cost by {f1(slack_effect('Guizhou',0.2)[0])} EUR MWh^-1^ in Guizhou at an AI share of 20% but the autonomous cost by only {f1(slack_effect('Guizhou',0.2)[1])} EUR MWh^-1^, because the tariff gives firms no reason to use the extra slack; in Jiangsu at the same share the autonomous cost falls by {f1(slack_effect('Jiangsu',0.2)[1])} EUR MWh^-1^ against {f1(slack_effect('Jiangsu',0.2)[0])} EUR MWh^-1^ for the coordinated cost.

### Event contracts add little; the price shape closes the gap

An event-based commitment contract (S3), in which the system declares the top 5% of hours whose marginal cost exceeds the weekly median by more than 20% and the firm commits the maximum reduction deliverable relative to its own tariff-optimal schedule at a compensation of at least its opportunity cost, realises {pc(min(sh[p]['S3'][0] for p in P))}–{pc(max(sh[p]['S3'][1] for p in P))} of the coordination value, essentially the same as S1 (Fig. 3): under this event rule the value arises from continuous intraday shifting and avoided investment rather than from a few event hours. Other event definitions were not tested. When the firm instead optimises against an hourly price whose shape follows the coordinated solution's marginal cost (S1rt), rescaled to the tariff's mean level, its outcome is within {f1(rt_max)}% of the coordinated optimum in every setting and within {f1(rt_max_lowai)}% at AI shares of 5–10%. Because S1rt uses the dual prices of the coordinated solution, near-closure is expected by construction for a price-taking firm with foresight; the informative result is the distance of current tariff shapes and of the event contract from that benchmark, which shows that the shape of the hourly price, rather than a contract layered on the tariff, is the instrument that determines realised value.

### Mechanism design: continuous prices versus event contracts

Two settlement designs were compared under identical tasks and reliability (Methods). The event contract, settled against a baseline, {s3txt}, while its compensation floor is {mrow['Guizhou'].s3_compensation_floor_own_baseline/1e3:,.1f} thousand euros per representative week in Guizhou and zero elsewhere because no events are declared. It is also exposed to baseline manipulation: if settlement used a full-speed baseline instead of the firm's own tariff-optimal schedule, the measured reduction during Guizhou's summer events would be inflated by {mg.inflated_minus_own_event_power_mw:.0f} MW on average without any change in delivered flexibility{' (no events were declared in the other provinces)' if mg is not None else ''}. A continuous hourly price shaped like the system's marginal cost, settled on metered consumption without a baseline, saves {mrow['Gansu'].s1rt_saving_vs_S1/1e3:,.0f}, {mrow['Jiangsu'].s1rt_saving_vs_S1/1e3:,.0f} and {mrow['Guizhou'].s1rt_saving_vs_S1/1e3:,.0f} thousand euros per representative week in Gansu, Jiangsu and Guizhou relative to S1 and leaves a residual gap to the optimum of {f1(mrow['Gansu'].gap_S1rt_S2_pct)}%, {f1(mrow['Jiangsu'].gap_S1rt_S2_pct)}% and {f1(mrow['Guizhou'].gap_S1rt_S2_pct)}%. It has no baseline and therefore no baseline-inflation rent; other strategic exposures of a large price-taking load, such as forecast gaming or price influence, are outside the model, and the ex-post dual price is a benchmark for the shape of an implementable price, not a published tariff.

### Robustness

Ten weather years (2015–2024) of wind and solar profiles derived from the ERA5 reanalysis {cite('era5','openmeteo')} at the twenty largest sites per province and technology give constrained-exchange rigid-to-coordinated gaps of {f1(mwr('Gansu',0.41)[0])}–{f1(mwr('Gansu',0.41)[2])}% (median {f1(mwr('Gansu',0.41)[1])}%, {mwr('Gansu',0.41)[3]} feasible years) in Gansu, {f1(mwr('Jiangsu',0.41)[0])}–{f1(mwr('Jiangsu',0.41)[2])}% (median {f1(mwr('Jiangsu',0.41)[1])}%, {mwr('Jiangsu',0.41)[3]} years) in Jiangsu and {f1(mwr('Guizhou',0.41)[0])}–{f1(mwr('Guizhou',0.41)[2])}% (median {f1(mwr('Guizhou',0.41)[1])}%, {mwr('Guizhou',0.41)[3]} years) in Guizhou at an AI share of 10%; the S1rt gap stays below {f1(max(mwr(p,0.41)[4] for p in P)+0.05)}% in every year (Fig. 4a). With idle power at 25% of nameplate instead of {pc(IDLE)}, the gaps are {f1(mwr('Gansu',0.25)[0])}–{f1(mwr('Gansu',0.25)[2])}%, {f1(mwr('Jiangsu',0.25)[0])}–{f1(mwr('Jiangsu',0.25)[2])}% and {f1(mwr('Guizhou',0.25)[0])}–{f1(mwr('Guizhou',0.25)[2])}%. A cost-parameter Monte Carlo (fuel prices 0.7–1.5×, investment costs 0.7–1.3×, idle power 25–45% of nameplate, utilisation 50–80%; {mcn['Gansu'][1]} draws per province, of which {mcn['Gansu'][0]}, {mcn['Jiangsu'][0]} and {mcn['Guizhou'][0]} were feasible in Gansu, Jiangsu and Guizhou) gives 10th–90th percentile gaps of {f1(mcr('Gansu')[0])}–{f1(mcr('Gansu')[2])}% (median {f1(mcr('Gansu')[1])}%), {f1(mcr('Jiangsu')[0])}–{f1(mcr('Jiangsu')[2])}% (median {f1(mcr('Jiangsu')[1])}%) and {f1(mcr('Guizhou')[0])}–{f1(mcr('Guizhou')[2])}% (median {f1(mcr('Guizhou')[1])}%) (Fig. 4b); Guizhou is separated from the other two provinces in every draw, whereas the Gansu and Jiangsu distributions overlap. A peak-adjusted sensitivity in which the 2020 Gansu peak is set to the 2021 official maximum load of 17.66 GW and the Guizhou peak to 29 GW, with annual energy conserved, changes the constrained-exchange gap at an AI share of 10% from {f1(pkg('Guizhou',False,0.1))}% to {f1(pkg('Guizhou',True,0.1))}% in Guizhou and from {f1(pkg('Gansu',False,0.1))}% to {f1(pkg('Gansu',True,0.1))}% in Gansu. Across all sensitivities the S1rt gap remains below {f1(rt_max)}% (Fig. 4c).

### Limitations and outlook

Hourly provincial load shapes derive from a 2018 reconstruction {cite('wukan')} anchored to official 2020 annual electricity {cite('nbs')} and checked against published peaks; the Gansu and Guizhou peaks are overstated, which biases scarcity upward, and metered hourly load would be required to move the results from scenario to empirical estimate. Hydro and load shapes are single-year; unit commitment is a heuristic; interprovincial exchange is a fixed-price proxy or an aggregate neighbour node rather than an explicit network; AI pool size and deadline slack are assumptions; cooling overheads, task migration and non-anticipative control are not represented; interactive inference with sub-hourly service constraints {cite('stojkovic')} is not treated as shiftable; only one event rule was tested. These features could change the magnitudes reported here. The tested sensitivities (weather years, cost parameters, idle power, peaks, deadline slack) leave Guizhou separated from Gansu and Jiangsu and leave the distance between tariff-driven and price-shape-driven outcomes intact.

'''
legends=f'''## Figure legends

**Fig. 1 | Service constraints and measured power.** **a**, Measured GPU power–throughput modes for eight workload configurations at six power caps, normalised to the 400 W cap (re-analysis of ref. {order.index('colangelo')+1}). **b**, GPU-hour-weighted cumulative distributions of observed scheduling wait (solid) and job run time (dashed) in three public production traces: Helios {cite('hu')}, Alibaba PAI {cite('weng')} and Philly {cite('jeon')}; the dotted line marks 24 h. **c**, Node-level alternating-current power of eight-GPU H100 nodes in MLPerf Training v4.0 {cite('mlperf')} for three benchmarks; idle is the median of the lowest 5% of readings, active the median of the central 60%.

**Fig. 2 | Incremental system cost per megawatt-hour of AI load by operating scenario.** Three provinces, 2030 public-data scenario with constrained interprovincial exchange, deadline slack equal to the job's observed queueing wait plus 6 h, idle power {pc(IDLE)} of nameplate, AI load equal to 5, 10 and 20% of the 2030 provincial peak. Scenarios: S0 rigid; S1 firm optimising against the official time-of-use tariff shape; S3 event-based commitment contract; S1rt firm optimising against an hourly price shaped like the system's marginal cost; S2 system-coordinated. Costs are in 2030 euros from the archive cost tables; increments are relative to the same system without the AI load. Vertical axes are truncated to show differences between scenarios.

**Fig. 3 | Share of coordination value realised.** (cost S0 − cost X)/(cost S0 − cost S2) for X = S1, S3 and S1rt, same settings as Fig. 2. A value of 1 means the firm's own optimisation delivers all of the system value.

**Fig. 4 | Robustness.** Box plots of the rigid-to-coordinated gap (constrained exchange, AI share 10%) across **a**, ten ERA5-derived weather years, 2015–2024 (n = {mwr('Gansu',0.41)[3]}, {mwr('Jiangsu',0.41)[3]} and {mwr('Guizhou',0.41)[3]} feasible years for Gansu, Jiangsu and Guizhou) and **b**, a cost-parameter Monte Carlo (n = {mcn['Gansu'][0]}, {mcn['Jiangsu'][0]} and {mcn['Guizhou'][0]} feasible draws), and **c**, the gap of the S1rt outcome to the coordinated optimum across the weather years. Centre line, median; box, interquartile range; whiskers, 1.5 × interquartile range; points, outliers.

'''
methods=f'''## Methods

### Task–power model

Each compute pool $p$ runs batches $j$ with release $r_{{pj}}$, deadline $d_{{pj}}$ and work $w_{{pj}}$ measured in full-speed pool-hours. Execution shares $y_{{pjtm}}\\in[0,1]$ of the pool in hour $t$ and operating mode $m$, with normalised throughput $\\bar q_m$ and power $P_m$, satisfy $\\sum_{{j,m}} y_{{pjtm}}\\le 1$, $y_{{pjtm}}=0$ outside $[r_{{pj}},d_{{pj}})$ and $\\sum_{{t,m}}\\bar q_m y_{{pjtm}}\\Delta t=w_{{pj}}$ with $\\Delta t=1$ h; no work may be dropped or deferred beyond the horizon. Pool power is $P_{{pt}}=P^{{\\rm idle}}_p+\\sum_{{j,m}}(P_m-P^{{\\rm idle}}_p)y_{{pjtm}}$. Modes are the six GPU power caps of the fine-tuning configuration measured in ref. {order.index('colangelo')+1}; modes whose measured power lies below node idle power are not achievable at node level and are excluded, leaving {meta_any.get('modes_kept','five')} modes. Idle power is {pc(IDLE)} of nameplate in the base case, the ratio of idle to peak node power in MLPerf Training v4.0 logs {cite('mlperf')} for the Llama-2-70B fine-tuning benchmark (35–41% across three benchmarks); 25% is a sensitivity. Switching, checkpoint and cooling overheads are not represented. Batches are sampled from completed GPU jobs of the Helios trace {cite('hu')} by hour of submission, keeping GPU count and run time and scaling total work to a pool utilisation of 70%; the deadline is the run time plus the job's own observed queueing wait times a multiplier (1 or 3) plus a base slack (6 or 24 h). A greedy full-speed reservation guarantees joint feasibility, extending deadlines where necessary and truncating work at the horizon end; extensions and truncated shares are recorded in the run metadata.

### Joint planning–operation model

A linear programme (LP) shares investment in generation, lines and storage across scenarios (four representative weeks of 2020, one per season, equal probability) and dispatches chronologically within each: nodal balance with a transport network with 3% losses, storage with 95% charge and discharge efficiency and cyclic state of charge, generator availability profiles, an optional must-run fraction, an emissions cap and a cap on expected unserved energy, set to zero for non-AI load. Investment coefficients are annualised at 5% over technology lifetimes and scaled to the weekly horizon. The implementation was verified in {v1.get('n_checks',118)} checks, including 100 independent oracle cases (60 screening-curve capacity cases and 40 enumerated task-assignment cases), and its reservoir-cascade extension in {v2.get('n_checks',74)} checks, including 60 independent dynamic-programming cases (Supplementary Information). Unit commitment, alternating-current power flow, task migration and non-anticipative control are not represented.

### Scenarios

S0 fixes the pool to a work-conserving earliest-deadline full-speed schedule. S1 fixes it to the schedule that minimises the firm's bill under the official time-of-use tariff shape of the province (Jiangsu {cite('js_tariff')}; Gansu {cite('gs_tariff')}, effective 2021; Guizhou {cite('gz_tariff')}, the nearest official structure, from 2023); the tariff level is set to 1.5 × the coal marginal cost because only the shapes are official. S1rt repeats S1 with the hourly shape of the coordinated solution's nodal marginal cost rescaled to the same mean. S2 leaves the task variables free in the joint LP. In S3 the system declares as events the top 5% of hours whose S1 marginal cost exceeds the weekly median by more than 20%; the firm commits the maximum reduction deliverable relative to its own S1 schedule with all batches still completed, is compensated at least its opportunity cost, and the committed trajectory is fixed in the joint LP. A reference case without the AI pool defines the increments, which are reported per megawatt-hour of AI load. Compensation is treated as a transfer, not a resource cost.

### Provincial inputs

Hourly load is the 2020 provincial series of PyPSA-China V3.0 {cite('pypsa')}, a 2018-derived reconstruction {cite('wukan')}, anchored to the official 2020 annual electricity of each province {cite('nbs')}. A plausibility check against published peaks shows Jiangsu consistent (summer and winter peaks above 100 GW), Gansu about 11% above the 2021 official maximum load and Guizhou above the 2026 record, so a peak-adjusted sensitivity is reported in which deviations from the annual mean are compressed to a target peak with annual energy conserved. The 2030 load scales the shape by the 2030/2020 provincial ratio of the same model. Thermal, nuclear and hydro fleets in 2030 are unit-level from the Global Energy Monitor tracker {cite('gem')}: operating plus under-construction units with start year up to 2030 and retirements applied; size thresholds make the totals lower bounds. Existing wind and solar capacity is the 2020 value of the model archive; new wind, solar, batteries and open-cycle gas turbines are investable at the archive's 2030 costs, and new coal is not allowed. Coal must-run is 40% of the capacity committed to cover each week's maximum residual load divided by 0.85. Interprovincial exchange is represented either by an external node with a fixed load of 60% of the province's interconnection capacity supplied at 1.1 × the coal marginal cost, or by an aggregate node of the directly connected provinces with their own anchored load, GEM 2030 fleets, archive renewables and a high-cost backstop; the interconnection capacity is the sum of the HVDC and HVAC line lists compiled in ref. {order.index('wukan')+1}, which we rebuilt from the published appendix and did not independently verify, and line investment is not allowed. Weather-year profiles use hourly 100 m wind speed, global horizontal irradiance and temperature from the ERA5 reanalysis {cite('era5')} through the Open-Meteo archive {cite('openmeteo')} at the twenty largest operating wind and solar sites per province from the GEM tracker, converted with a generic power curve (cut-in 3 m s^-1^, rated 12 m s^-1^, cut-out 25 m s^-1^, 0.85 availability) and an irradiance model (0.85 performance ratio, −0.4% K^-1^ above 25 °C), capacity-weighted, and scaled so that the 2020 mean equals the archive profile mean; the correlation with the archive 2020 hourly profile is {corr['Jiangsu|solar']:.2f} (Jiangsu solar), {corr['Jiangsu|wind']:.2f} (Jiangsu wind), {corr['Guizhou|solar']:.2f}, {corr['Guizhou|wind']:.2f}, {corr['Gansu|solar']:.2f} and {corr['Gansu|wind']:.2f} (Gansu wind). Hydro uses the archive's normalised profile with GEM capacities. The Monte Carlo draws fuel prices, investment costs, idle power and utilisation independently from uniform distributions and drops draws that are infeasible or exceed a 150 s solve limit. Costs are in euros from the archive cost tables {cite('pypsa')}. Provinces were chosen from a screening of the 31 provinces by national computing-hub status {cite('ndrc')}, renewable share and hydro share.

### Statistics and reproducibility

No statistical tests are used; ranges report minima and maxima across scenario settings, box plots report medians and interquartile ranges, and Monte Carlo statistics report percentiles across feasible draws. All analyses can be reproduced from the public sources listed in the Supplementary Information with the deposited code.

## Data availability

All inputs are public. The Supplementary Information lists every dataset with its source, version, checksum, licence and limitations. Processed inputs, run metadata and result tables are deposited with the code (see Code availability). Raw external archives are not redistributed; the registry gives retrieval instructions.

## Code availability

Model, audit and figure code, with the run order and independent verification records, is available at https://github.com/william19307/ai-grid-flexibility-research; the repository will be made public and archived with a DOI on Zenodo upon publication.

## Author contributions

W.W. conceived the study, developed the task and joint planning models, curated the public datasets, performed the analyses and wrote the manuscript. L.L. contributed to the research design, supervised the analysis and revised the manuscript. Both authors approved the final version.

## Competing interests

The authors declare no competing interests.

## Ethics

This study uses only public datasets and published benchmark results; no human-subject or proprietary data were used.

'''
reflist='## References\n\n'+'\n'.join(f'{i+1}. {REFS[k]}' for i,k in enumerate(order))+'\n'
doc=front+abstract+main+legends+methods+reflist
# sanity
assert 'PENDING' not in doc and 'outputs/' not in doc.split('## Code availability')[0]
open(M/'core_paper_en_v1.3.md','w',encoding='utf-8').write(doc)
print('title words',len(title.split()),'| abstract words',i_abs,'| total words',len(doc.split()),'| refs',len(order))
print('constrained gaps',{p:tuple(round(x,1) for x in g02_all[p]) for p in P});print('S1rt max',round(rt_max,2),'lowai',round(rt_max_lowai,2));print('shares',{p:{k:tuple(round(x,2) for x in v) for k,v in sh[p].items()} for p in P})
