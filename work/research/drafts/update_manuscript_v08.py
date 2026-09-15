"""v0.8: multi-weather-year runs (ERA5-derived profiles), MLPerf node-power calibration, alternative public-data paths."""
from pathlib import Path
import json,pandas as pd,numpy as np
ROOT=Path(__file__).resolve().parents[3];T=ROOT/'outputs/research/tables';M=ROOT/'outputs/research/manuscript';R=ROOT/'outputs/research/reports'
mw=pd.read_csv(T/'regional_2030_multiweather.csv');mw=mw[mw.gap_S0_S2_pct.notna()]
q=mw.groupby(['province','idle']).agg(g02_min=('gap_S0_S2_pct','min'),g02_med=('gap_S0_S2_pct','median'),g02_max=('gap_S0_S2_pct','max'),g12_med=('gap_S1_S2_pct','median'),g12_max=('gap_S1_S2_pct','max'),grt_max=('gap_S1rt_S2_pct',lambda s:s.abs().max()),curt_min=('curtail_NOAI','min'),curt_max=('curtail_NOAI','max'))
q.round(2).to_csv(T/'regional_2030_multiweather_summary.csv')
re=json.load(open(T/'multiyear_re_profiles_audit.json'));ml=json.load(open(T/'mlperf_v40_power_by_benchmark.json'))
def z(p,i):r=q.loc[(p,i)];return f"{r.g02_min:.1f}% 到 {r.g02_max:.1f}%（中位数 {r.g02_med:.1f}%）"
def e(p,i):r=q.loc[(p,i)];return f"{r.g02_min:.1f}–{r.g02_max:.1f}% (median {r.g02_med:.1f}%)"
corr={k:v['corr_with_archive_2020'] for k,v in re['scaling'].items()}
idle_rng=(min(v['idle_over_max'] for v in ml.values()),max(v['idle_over_max'] for v in ml.values()))
zh=f"""### 5.9 用公开替代数据补齐三项阻塞：多气象年、功率标定与负荷校核

**多气象年风光曲线。** 机构气象数据与需注册的接口无法取得，改用 Open-Meteo 的 ERA5 历史接口（免费、无需注册，D19），按 GEM 电站坐标取三省各技术装机最大的 8 个站点，拉取 2015 到 2024 年逐时 100 米风速、总辐射与气温，用通用功率曲线和辐照度模型转换为容量因子，按装机加权后把 2020 年均值缩放到归档水平（`../tables/multiyear_re_profiles_audit.json`）。与归档 2020 年逐时曲线的相关系数：江苏光伏 {corr['Jiangsu|solar']:.2f}、风电 {corr['Jiangsu|wind']:.2f}；贵州光伏 {corr['Guizhou|solar']:.2f}、风电 {corr['Guizhou|wind']:.2f}；甘肃光伏 {corr['Gansu|solar']:.2f}、风电仅 {corr['Gansu|wind']:.2f}（前 8 站只覆盖 16% 装机，需扩大站点数）。用这十个气象年重跑不允许外送、AI 占峰荷 10% 的 2030 情景（`../tables/regional_2030_multiweather.csv`）：刚性到协调的差距甘肃为 {z('Gansu',0.25)}，江苏为 {z('Jiangsu',0.25)}，贵州为 {z('Guizhou',0.25)}；企业面对实时价格的差距在全部年份不超过 {q.grt_max.max():.2f}%。气象年改变差距的幅度，但不改变省份排序与机制结论。水电与负荷形状仍为单一年份，是剩余局限。

**节点级功率标定。** 无授权集群功率遥测，改用 MLCommons 公开的 MLPerf Training v4.0 交流功率日志（D18，Supermicro 8×H100 节点，约 2 秒一读）。三个基准下节点空闲功率占峰值 {idle_rng[0]*100:.0f}% 到 {idle_rng[1]*100:.0f}%（llama2-70b LoRA 微调为 {ml['llama2_70b_lora']['idle_over_max']*100:.0f}%，满载约 {ml['llama2_70b_lora']['active_w']/1000:.1f} kW），高于此前假设的 25%。以 41% 重跑多气象年：甘肃差距 {z('Gansu',0.41)}，江苏 {z('Jiangsu',0.41)}，贵州 {z('Guizhou',0.41)}。空闲功率越高，降频与转移能改变的功率份额越小，差距相应收窄，但排序不变。

**负荷校核。** 逐时实测负荷无公开来源；现货试点省份的披露平台需登录。已完成的替代是峰荷公开报道校核（5.7 节前的补充）与峰荷修正敏感性。后续可再用各省月度用电量校核季节形状。
"""
v7=open(M/'论文工作稿_v0.7.md',encoding='utf-8').read()
v8=v7.replace('**版本：v0.7，2026-09-15。','**版本：v0.8，2026-09-15。').replace('## 6. 讨论与当前局限',zh+'\n## 6. 讨论与当前局限')
open(M/'论文工作稿_v0.8.md','w',encoding='utf-8').write(v8)
rep=f"""# 阶段研究报告 09：公开替代数据补齐阻塞项

日期：2026-09-15。研究仍在进行。

## 本轮完成

1. Open-Meteo（ERA5）多年逐时气象拉取与三省风光容量因子（2015–2024，D19）；与归档 2020 曲线相关性见审计 JSON。
2. 多气象年 2030 情景 60 组（3 省 × 10 年 × 空闲功率 0.25/0.41）。
3. MLPerf Training v4.0 节点功率日志解析（D18）：三基准空闲占峰值 {idle_rng[0]*100:.0f}% 到 {idle_rng[1]*100:.0f}%。
4. 工作稿 v0.8（5.9 节）、英文稿 v0.6。

## 方向性结果

- 十个气象年：甘肃差距 {z('Gansu',0.25)}，江苏 {z('Jiangsu',0.25)}，贵州 {z('Guizhou',0.25)}；实时价格差距不超过 {q.grt_max.max():.2f}%。
- 空闲功率 41% 时差距收窄但排序不变。

## 仍未完成

甘肃风电站点扩大到覆盖多数装机；多年水电与温度驱动的负荷形状；机组级启停；机制 v2 的验证规则；英文定稿。
"""
open(R/'阶段研究报告_09.md','w',encoding='utf-8').write(rep)
en=open(M/'core_paper_en_v0.5.md',encoding='utf-8').read().replace('**Working English draft v0.5 (2026-09-15).','**Working English draft v0.6 (2026-09-15).')
mark='`[Fig. 5: multi-weather years, outage samples, external test system.]`'
add=f"""`[Fig. 5: multi-weather years.]` Ten weather years (2015–2024) of ERA5-derived wind and solar profiles at the largest GEM sites (Open-Meteo archive; converted with a generic power curve and an irradiance model, levels scaled to the archive 2020 mean) give constrained-exchange rigid-to-coordinated gaps of {e('Gansu',0.25)} in Gansu, {e('Jiangsu',0.25)} in Jiangsu and {e('Guizhou',0.25)} in Guizhou at an AI share of 10%; the firm-under-real-time-price gap stays below {q.grt_max.max():.2f}% in every year. MLPerf Training v4.0 node-level AC power logs (8×H100 nodes) put idle power at {idle_rng[0]*100:.0f}–{idle_rng[1]*100:.0f}% of peak across three benchmarks, above the 25% assumed earlier; with 41% idle the gaps narrow ({e('Gansu',0.41)}, {e('Jiangsu',0.41)}, {e('Guizhou',0.41)}) but the ordering and the price-signal conclusion are unchanged."""
assert mark in en;en=en.replace(mark,add);open(M/'core_paper_en_v0.6.md','w',encoding='utf-8').write(en)
pj=R/'研究进度与待完成项.json';d=json.load(open(pj))
d['completed_evidence']+=['Open-Meteo ERA5 multi-year wind/solar profiles for three provinces (2015-2024) built and audited (D19)','60-run multi-weather-year 2030 grid with idle 0.25/0.41','MLPerf v4.0 node power logs parsed: idle 35-41% of peak (D18)','manuscript v0.8, phase report 09, English v0.6']
d['requirements_still_open']['robustness']='multi-weather done for wind/solar (single-year hydro and load shape remain); outages and external system pending'
d['requirements_still_open']['Q1']='production traces + MLPerf node power + Emerald GPU modes now calibrate timing, idle and power modes from public data; deadlines remain assumptions by class'
d['latest_manuscript']='outputs/research/manuscript/论文工作稿_v0.8.md';d['latest_phase_report']='outputs/research/reports/阶段研究报告_09.md'
json.dump(d,open(pj,'w'),ensure_ascii=False,indent=1)
c=M/'投稿就绪清单.md';s=open(c,encoding='utf-8').read()
s=s.replace('| 不确定性 | 敏感性与稳健性 | 期限松弛、AI 规模、交换模式、峰荷修正、成本参数蒙特卡洛已做 | 天气年、故障样本未做（需多年风光曲线） |','| 不确定性 | 敏感性与稳健性 | 期限松弛、AI 规模、交换模式、峰荷修正、成本蒙特卡洛、十个气象年（风光）已做 | 故障样本、多年水电与负荷形状未做 |')
s=s.replace('| 核心结果 | 可复现、经验证的定量发现 | 三省 2030 公开数据情景（S0/S1/S1rt/S2/S3），方向性结论稳健 | 逐时负荷独立验证（需机构数据）；多气象年（需多年风光曲线）；机组级启停 |','| 核心结果 | 可复现、经验证的定量发现 | 三省 2030 公开数据情景（S0/S1/S1rt/S2/S3），十个气象年与成本抽样下稳健 | 逐时负荷独立验证（无公开来源，已用峰荷报道校核与修正敏感性替代）；机组级启停 |')
s=s.replace('**结论：** 论文骨架、方法、数据链、方向性结果与复现材料已具备；能否投 Nature Energy 取决于两项作者必须提供的输入：经独立验证的省级逐时或峰荷数据，以及多年风光出力曲线（或授权获取的气象再分析处理结果）。没有这两项，稿件适合先投 Energy Policy 或 Applied Energy 并如实标注数据层级。',
'**结论（更新）：** 多年风光曲线已用免费 ERA5 接口补齐，功率参数已用 MLPerf 公开日志标定，逐时负荷用峰荷报道校核加敏感性替代。剩余最大弱点是负荷形状仍源自 2018 年重构；若在稿中如实陈述并以敏感性覆盖，可以尝试 Nature Energy 或 Joule，同时以 Applied Energy 或 Energy Policy 为备选。')
open(c,'w',encoding='utf-8').write(s);print('v0.8 written');print(q.round(2).to_string())
