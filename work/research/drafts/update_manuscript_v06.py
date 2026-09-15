"""Compose 论文工作稿 v0.6, 阶段研究报告 07 and core_paper_en_v0.2 from v0.5 + 2030 grid outputs."""
from pathlib import Path
import json,pandas as pd,numpy as np
ROOT=Path(__file__).resolve().parents[3];T=ROOT/'outputs/research/tables';M=ROOT/'outputs/research/manuscript';R=ROOT/'outputs/research/reports'
g=pd.read_csv(T/'regional_2030_gaps.csv');fleet=pd.read_csv(T/'gem_fleet_three_provinces_2020_2030.csv');cmp=pd.read_csv(T/'gem_vs_archive_capacity_three_provinces.csv')
def r(p,e,a,sm):return g[(g.province==p)&(g.export==e)&(g.ai_share==a)&(g.slack_mult==sm)].iloc[0]
ne=g[~g.export];ex=g[g.export]
f=lambda x:f'{x:.1f}'
tab=g[~g.export][['province','ai_share','slack_mult','cost_S0','cost_S1','cost_S2','cost_S3','gap_S0_S2_pct','gap_S1_S2_pct','gap_S3_S2_pct','new_ocgt_S0','new_ocgt_S2','new_batt_S0','s3_system_saving_vs_S1','s3_compensation_floor']].copy()
tab.columns=['省份','AI 占峰荷','松弛倍数','S0','S1','S2','S3','S0−S2 %','S1−S2 %','S3−S2 %','S0 新增燃气 MW','S2 新增燃气 MW','S0 新增储能 MW','S3 相对 S1 系统节省','S3 补偿下限']
md_tab=tab.round(2).to_markdown(index=False)
gz=fleet[fleet.province=='Gansu'].set_index('type');jsf=fleet[fleet.province=='Jiangsu'].set_index('type');gzf=fleet[fleet.province=='Guizhou'].set_index('type')
js20=r('Jiangsu',False,0.2,1.0);js20b=r('Jiangsu',False,0.2,3.0)
sec=f"""### 5.7 三省 2030 情景：公开数据下的 S0 到 S3 结果

**输入与口径。** 采用 GEM 2025 年 7 月机组库构建三省 2030 年火电、核电、水电机组清单（运行中加在建、按投运与退役年份筛选；`../tables/gem_fleet_three_provinces_2020_2030.csv`），GEM 有规模门槛因而相对官方统计偏低，与归档容量的对照见 `../tables/gem_vs_archive_capacity_three_provinces.csv`。甘肃 2030 年煤电 {gz.loc['coal','mw_2030_operating_plus_construction']:.0f} MW、水电 {gz.loc['hydropower','mw_2030_operating_plus_construction']:.0f} MW（补上了归档缺失的水电）；江苏煤电 {jsf.loc['coal','mw_2030_operating_plus_construction']:.0f} MW、气电 {jsf.loc['oil/gas','mw_2030_operating_plus_construction']:.0f} MW、核电 {jsf.loc['nuclear','mw_2030_operating_plus_construction']:.0f} MW；贵州煤电 {gzf.loc['coal','mw_2030_operating_plus_construction']:.0f} MW、水电 {gzf.loc['hydropower','mw_2030_operating_plus_construction']:.0f} MW。2030 年负荷用归档的省级 2030 与 2020 年负荷比放大年度锚定的 2020 逐时形状（形状不变是假设）；风光既有装机取 2020 归档值，风电、光伏、储能、燃气调峰按归档 2030 成本可投资，不允许新建煤电；煤电必开按"承诺容量"启发式（覆盖周内最大剩余负荷除以 0.85 的机组容量的 40%）。AI 池规模为 2030 峰荷的 5%、10%、20%，批次由 Helios 已完成作业抽样，期限松弛取作业自身观测等待乘以 1 或 3 再加 6 或 24 小时。S3 事件时段取 S1 运行中边际成本高于周中位数 20% 以上的前 5% 小时；企业相对自身 S1 调度承诺最大可交付削减，并至少获得机会成本补偿。全部结果为公开数据情景，逐时负荷形状未经独立验证，省间交换为外部市场代理。

**结果一：外部市场代理吸收了几乎全部价值。** 允许外送时，三省所有设定下刚性到协调的差距都低于 1%（`../tables/regional_2030_gaps.csv`）。这不是"灵活性无价值"的证据，而是"以固定价格无限吸纳外送"的代理消除了本地稀缺。多省耦合模型必须替代这一代理才能给出可信的省际结论。

**结果二：外送受限时，价值随系统结构与 AI 规模变化。** 下表列出不允许外送的情景（单位 AI 电量的增量系统成本，欧元每兆瓦时，归档成本口径）：

{md_tab}

甘肃刚性到协调的差距为 1% 到 2%，贵州为 8% 到 11%，江苏随 AI 规模从 2% 升到 15%。江苏在 AI 占峰荷 20% 时，刚性运行需要新增 {js20.new_ocgt_S0:.0f} MW 燃气调峰和 {js20.new_batt_S0:.0f} MW 储能，系统协调只需 {js20.new_ocgt_S2:.0f} MW（松弛加大后为 {js20b.new_ocgt_S2:.0f} MW）燃气，这是投资通道的直接体现。放宽期限松弛（观测等待乘 3 加 24 小时）使协调情景的成本进一步下降，但企业自主情景的改善小得多，说明企业在电价下不会自动利用更长的期限。

**结果三：企业自主运行只兑现了协调价值的一部分，比例因电价与系统而异。** 以 S0 到 S2 为全部协调价值，S1 兑现的份额在甘肃约为四到八成，在贵州约为一到四成，在江苏 AI 5% 到 10% 时接近全部而在 20% 时只有三到八成。贵州的低兑现与官方分时电价的低谷时段和系统富余时段不重合有关（见 5.6 节）。

**结果四：第一版事件型承诺机制几乎不产生系统净收益。** S3 相对 S1 的系统节省在多数设定下为零或为负，而补偿下限为正；S3 相对 S2 的差距与 S1 相近。原因有二：事件规则依据企业自主运行下的边际成本，而这些边际成本在多数小时近乎平坦；协调价值主要来自持续的日内转移和投资替代，而不是少数事件小时的削减。这一负结果本身有意义：以事件为单位的需求响应合同只能捕获 AI 负荷协调价值的很小一部分，后续机制设计应转向连续的价格或调度信号，并以 S2 的对偶价格而非 S1 的边际成本定义稀缺。

图：`../figures/regional_2030_cost_emissions.png`。
"""
disc="""
### 6.1 2030 情景后的判断

公开数据已足以支撑一个方向性的结论链：AI 负荷灵活性的系统价值取决于本地稀缺（零边际小时、容量紧缺、外送受限）而非灵活性参数本身；企业在现行分时电价下兑现的比例可以很低甚至为负；事件型承诺机制不能替代连续协调。要把这一链条变成可发表的实证结论，还需要：经独立验证的逐时负荷或峰荷；替代外部市场代理的多省耦合网络；机组级启停约束；多气象年与故障样本下的可靠性检验；以及以系统对偶价格定义稀缺的第二版机制。
"""
v5=open(M/'论文工作稿_v0.5.md',encoding='utf-8').read()
v6=v5.replace('**版本：v0.5，2026-09-15。','**版本：v0.6，2026-09-15。').replace('## 6. 讨论与当前局限',sec+'\n## 6. 讨论与当前局限').replace('## 参考来源',disc+'\n## 参考来源')
open(M/'论文工作稿_v0.6.md','w',encoding='utf-8').write(v6)
rep=f"""# 阶段研究报告 07：三省 2030 情景与第一版机制

日期：2026-09-15。研究仍在进行。本轮产出的是公开数据下的 2030 省级情景结果，带有明确假设；它不是经独立验证的实证结论。

## 本轮完成

1. 从 GEM 机组库建立甘肃、江苏、贵州 2020 与 2030 年机组级火电、核电、水电清单（A06），补上归档缺失的甘肃水电，并与归档容量对照。
2. 新建 2030 省级情景脚本：归档 2030 负荷比放大、2030 成本、可投资风光储气、不新建煤电、承诺容量必开启发式、Helios 批次与观测等待松弛、S3 事件型承诺机制（A07）。三省 × 外送开关 × AI 5/10/20% × 两种松弛，共 36 组、180 次求解。
3. 工作稿 v0.6 新增 5.7 节与 6.1 节；英文核心稿 v0.2 填入方向性结果；图 `../figures/regional_2030_cost_emissions.png`。

## 方向性结果

- 允许外送时差距均低于 1%：外部市场代理消除了本地稀缺，是模型局限。
- 外送受限时：甘肃差距 1% 到 2%，贵州 8% 到 11%，江苏 2% 到 15% 随 AI 规模上升；江苏 AI 20% 时刚性需新增 {js20.new_ocgt_S0:.0f} MW 燃气与 {js20.new_batt_S0:.0f} MW 储能，协调只需 {js20.new_ocgt_S2:.0f} MW 燃气。
- 企业自主兑现比例因省份与电价而异，贵州最低。
- 第一版事件型 S3 几乎无系统净收益，补偿下限常高于节省：协调价值来自连续转移与投资替代，不来自少数事件小时。

## 仍未完成

独立逐时或峰荷验证；多省耦合网络替代外部市场代理；机组级启停；多气象年与故障可靠性；以系统对偶价格定义稀缺的第二版机制；英文正文定稿与复现包。
"""
open(R/'阶段研究报告_07.md','w',encoding='utf-8').write(rep)
en=open(M/'core_paper_en_v0.1.md',encoding='utf-8').read()
en=en.replace('**Working English draft v0.1 (2026-09-15).','**Working English draft v0.2 (2026-09-15).')
en=en.replace("Smoke-test observation (uncalibrated, not citable): in a coal-slack provincial system with no surplus hours the four scenarios coincide; in a hydro–renewable-mixed system the rigid-to-coordinated gap is several percent of incremental cost and avoided peaker investment appears only when export is constrained. `[PENDING: calibrated results.]`",
f"""Public-data 2030 scenario (documented assumptions; hourly load shape not independently validated; see Methods): when interprovincial exchange is represented by an unconstrained external market at a fixed price, the rigid-to-coordinated gap in incremental system cost per AI MWh is below 1% in all three provinces, i.e. the exchange proxy removes local scarcity. With exchange constrained, the gap is 1–2% in Gansu (wind/solar-rich, coal-heavy), 8–11% in Guizhou (hydro–renewable mix) and 2–15% in Jiangsu, rising with the AI share of peak. At an AI share of 20% of the 2030 Jiangsu peak, rigid operation requires {js20.new_ocgt_S0:.0f} MW of new gas peakers and {js20.new_batt_S0:.0f} MW of batteries, whereas system-coordinated operation requires {js20.new_ocgt_S2:.0f} MW of gas ({js20b.new_ocgt_S2:.0f} MW with longer deadlines) and no batteries. `[PENDING: validated hourly load; multi-province network; unit commitment; multi-weather adequacy.]`""")
en=en.replace("`[Fig. 3: gap decomposition — efficiency-mode effect (S0→S0b), temporal shifting under tariffs (S0b→S1), coordination (S1→S2); dependence on deadline length W, spare capacity, tariff structure and interconnection.]`",
"""`[Fig. 3: gap decomposition.]` Firm-autonomous operation under official provincial time-of-use tariffs realises a province-dependent share of the coordination value: roughly 40–80% in Gansu, 10–40% in Guizhou and near 100% in Jiangsu at AI shares of 5–10% but only 30–80% at 20%. In Guizhou the tariff's valley (00:00–08:00) does not coincide with the system's surplus hours, so autonomous shifting can even raise system cost relative to rigid operation. Longer deadline slack lowers coordinated cost substantially but improves autonomous outcomes much less, because the tariff gives firms no reason to use the extra slack.""")
en=en.replace("`[Fig. 4: commitment–compensation frontier; participation condition; delivered vs. committed reduction under verification rules; cost bearers.]`",
"""`[Fig. 4: commitment–compensation frontier.]` A first event-based commitment mechanism (events = the top 5% hours whose marginal cost exceeds the weekly median by more than 20%; the firm commits the maximum deliverable reduction relative to its own autonomous schedule and is compensated at least its opportunity cost) yields zero or negative system savings relative to autonomous operation in most settings while its compensation floor is positive, and leaves the gap to coordinated operation essentially unchanged. Coordination value arises from continuous intra-day shifting and avoided investment, not from a few event hours; event-based demand-response contracts therefore capture only a small fraction of it. `[PENDING: mechanism v2 with scarcity defined by system dual prices; continuous signals; verification and baseline manipulation.]`""")
open(M/'core_paper_en_v0.2.md','w',encoding='utf-8').write(en)
p=R/'研究进度与待完成项.json';d=json.load(open(p))
d['completed_evidence']+=["GEM unit-level 2020/2030 fleets for Gansu, Jiangsu, Guizhou built and compared with archive (A06)","provincial 2030 S0/S1/S2/S3 scenario pipeline built and run: 36 settings, 180 solves (A07); results labelled public-data scenario","manuscript v0.6 (sections 5.7, 6.1), phase report 07, English core paper v0.2 with directional results"]
d['requirements_still_open']['Q3']="first event-based commitment mechanism implemented and evaluated: near-zero system net benefit; v2 with system dual-price scarcity, continuous signals, baseline/verification pending"
d['next_actions']=["obtain independent hourly or peak load validation for the three provinces (institutional data) or document the limitation","replace the external-market proxy by a multi-province coupled network for the three provinces and their neighbours","unit-level commitment using GEM unit sizes; multi-weather years (archive 1979-2016 hydrology/weather where available) and outage samples","mechanism v2: scarcity from S2 dual prices, continuous price/dispatch signals, verification and baseline rules","finalise English manuscript, figures and reproduction package"]
d['latest_manuscript']="outputs/research/manuscript/论文工作稿_v0.6.md";d['latest_phase_report']="outputs/research/reports/阶段研究报告_07.md";d['previous_goal_turn_classification']="progress: first full S0-S3 provincial 2030 scenario results on public data; still not independently validated"
json.dump(d,open(p,'w'),ensure_ascii=False,indent=1);print('v0.6, report 07, EN v0.2, progress written')
