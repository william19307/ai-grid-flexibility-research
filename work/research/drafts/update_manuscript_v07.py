"""Compose v0.7 (adds neighbour-node exchange and real-time-price results), phase report 08, English v0.3."""
from pathlib import Path
import json,pandas as pd,numpy as np
ROOT=Path(__file__).resolve().parents[3];T=ROOT/'outputs/research/tables';M=ROOT/'outputs/research/manuscript';R=ROOT/'outputs/research/reports'
gp=pd.read_csv(T/'regional_2030_gaps.csv');gn=pd.read_csv(T/'regional_2030_gaps_neighbours.csv')
def rr(g,p,e,a,sm):return g[(g.province==p)&(g.export==e)&(g.ai_share==a)&(g.slack_mult==sm)].iloc[0]
def rng_(g,p,e,col):x=g[(g.province==p)&(g.export==e)][col];return f'{x.min():.1f}% 到 {x.max():.1f}%'
def rng_en(g,p,e,col):x=g[(g.province==p)&(g.export==e)][col];return f'{x.min():.1f}–{x.max():.1f}%'
tab=gn[gn.export][['province','ai_share','slack_mult','cost_S0','cost_S1','cost_S1rt','cost_S2','cost_S3','gap_S0_S2_pct','gap_S1_S2_pct','gap_S1rt_S2_pct','gap_S3_S2_pct','curtail_NOAI','new_ocgt_S0','new_ocgt_S2','new_batt_S0','new_batt_S2']].copy()
tab.columns=['省份','AI 占峰荷','松弛倍数','S0','S1','S1rt','S2','S3','S0−S2 %','S1−S2 %','S1rt−S2 %','S3−S2 %','无 AI 弃电率','S0 新增燃气 MW','S2 新增燃气 MW','S0 新增储能 MW','S2 新增储能 MW']
md=tab.round(2).to_markdown(index=False)
rt_max=gn.gap_S1rt_S2_pct.abs().max();rt_max_p=gp.gap_S1rt_S2_pct.abs().max()
sec=f"""### 5.8 用邻省聚合节点替代外部市场代理，以及实时价格情景

**邻省节点。** 把外部节点改为该省直接相连省份的聚合：负荷为各邻省年度锚定形状乘以各自 2030 比、机组为各邻省 GEM 2030 清单（煤电必开按本省一半强度）、风光水为归档装机与曲线、可投资气电、风光与储能，另设三倍燃气成本的极高价备用电源使邻省稀缺被定价而不是免费供给。联络容量仍为重建的省间线路合计（未验证）。这样省际交换的价值由邻省自身的稀缺决定。

**实时价格情景（S1rt）。** 企业仍自主优化，但面对的价格形状为 S2 协调解的本省逐时节点边际成本（均值缩放到与分时电价相同）。它回答的问题是：如果企业看到的是系统真实的时间价格信号，兑现差距还剩多少。

**结果。** 邻省节点下允许交换的情景（`../tables/regional_2030_gaps_neighbours.csv`）：

{md}

三点判断：其一，用真实邻省替代固定价格代理后，允许交换情景的刚性到协调差距不再被抹平，甘肃为 {rng_(gn,'Gansu',True,'gap_S0_S2_pct')}，江苏为 {rng_(gn,'Jiangsu',True,'gap_S0_S2_pct')}，贵州为 {rng_(gn,'Guizhou',True,'gap_S0_S2_pct')}，说明省际交换只是把稀缺转移到邻省而非消除。其二，企业面对系统实时价格形状时，与协调解的差距在全部设定下不超过 {rt_max:.2f}%（固定价格代理下不超过 {rt_max_p:.2f}%），即差距几乎完全来自价格信号的形状，而不是企业自主本身。其三，事件型承诺机制 S3 仍与 S1 几乎相同。合起来的含义是：AI 负荷协调价值的兑现主要取决于企业面对的时间价格是否反映系统边际成本，连续的价格或调度信号比事件合同重要得多。这些是公开数据情景下的方向性结论，仍待逐时负荷验证与多气象年检验。

图：`../figures/regional_2030_cost_emissions_neighbours.png`。
"""
v6=open(M/'论文工作稿_v0.6.md',encoding='utf-8').read()
v7=v6.replace('**版本：v0.6，2026-09-15。','**版本：v0.7，2026-09-15。').replace('## 6. 讨论与当前局限',sec+'\n## 6. 讨论与当前局限')
v7=v7.replace('事件型承诺机制不能替代连续协调。','事件型承诺机制不能替代连续协调，而系统实时价格形状几乎可以完全弥合差距。')
open(M/'论文工作稿_v0.7.md','w',encoding='utf-8').write(v7)
rep=f"""# 阶段研究报告 08：邻省节点与实时价格情景

日期：2026-09-15。研究仍在进行。本轮结果为公开数据情景，逐时负荷形状未独立验证。

## 本轮完成

1. GEM 机组清单扩展到 31 省；2030 脚本新增"邻省聚合节点"交换模式，用相邻省份的真实负荷、机组与风光替代固定价格外部市场。
2. 新增 S1rt 情景：企业面对 S2 协调解的逐时节点边际成本形状自主优化。
3. 两种交换模式各 36 组设定重跑，含 S0、S1、S1rt、S2、S3。

## 方向性结果

- 邻省节点下允许交换的刚性到协调差距：甘肃 {rng_(gn,'Gansu',True,'gap_S0_S2_pct')}，江苏 {rng_(gn,'Jiangsu',True,'gap_S0_S2_pct')}，贵州 {rng_(gn,'Guizhou',True,'gap_S0_S2_pct')}；固定价格代理下均低于 1%。
- 企业面对系统实时价格形状时，与协调解的差距不超过 {rt_max:.2f}%。
- 事件型承诺机制仍几乎不改变结果。

## 仍未完成

逐时负荷独立验证；三省与邻省的多节点网络（当前为聚合节点）；机组级启停；多气象年与故障样本；机制 v2 的验证与基线规则；英文定稿与复现包。
"""
open(R/'阶段研究报告_08.md','w',encoding='utf-8').write(rep)
en=open(M/'core_paper_en_v0.2.md',encoding='utf-8').read().replace('**Working English draft v0.2 (2026-09-15).','**Working English draft v0.3 (2026-09-15).')
en=en.replace("`[PENDING: mechanism v2 with scarcity defined by system dual prices; continuous signals; verification and baseline manipulation.]`",
f"""When the firm instead optimises against the shape of the system's own hourly marginal cost (the dual prices of the coordinated solution, rescaled to the tariff's mean level), its outcome is within {rt_max:.2f}% of the coordinated optimum in every setting, with either exchange representation. The delivery gap is therefore almost entirely a property of the price signal the firm faces, not of autonomous operation as such. Replacing the fixed-price external market by an aggregate node of directly connected provinces (their own load, GEM 2030 fleets and renewables) restores local scarcity: with exchange allowed, rigid-to-coordinated gaps become {rng_en(gn,'Gansu',True,'gap_S0_S2_pct')} in Gansu, {rng_en(gn,'Jiangsu',True,'gap_S0_S2_pct')} in Jiangsu and {rng_en(gn,'Guizhou',True,'gap_S0_S2_pct')} in Guizhou. `[PENDING: validated hourly load; explicit multi-node network; verification and baseline rules for continuous signals.]`""")
open(M/'core_paper_en_v0.3.md','w',encoding='utf-8').write(en)
p=R/'研究进度与待完成项.json';d=json.load(open(p))
d['completed_evidence']+=["GEM fleets for all 31 provinces; neighbour-aggregate exchange node implemented; S1rt (firm under system real-time price shape) implemented; both 36-setting grids rerun with S0/S1/S1rt/S2/S3","manuscript v0.7 (5.8), phase report 08, English v0.3"]
d['latest_manuscript']="outputs/research/manuscript/论文工作稿_v0.7.md";d['latest_phase_report']="outputs/research/reports/阶段研究报告_08.md"
d['requirements_still_open']['Q3']="event-based commitment yields ~no system benefit; firm under system real-time price shape closes the gap to <1%; verification, baseline and transfer accounting for continuous signals pending"
json.dump(d,open(p,'w'),ensure_ascii=False,indent=1);print('v0.7 docs written')
