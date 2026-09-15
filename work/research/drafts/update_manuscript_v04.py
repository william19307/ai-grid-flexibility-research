from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[3]
folder=ROOT/'outputs/research/manuscript'
text=(folder/'论文工作稿_v0.3.md').read_text().replace('版本：v0.3','版本：v0.4',1)
text=text.replace('计算任务与电力投资运行联合求解器及其数学验证，','计算任务与电力投资运行联合求解器、水量守恒的梯级水电扩展及其数学验证，',1)
section='''### 2.6 大型水电资料的时序、库容与资产年代

已从归档 [9] 取得 43 站参数及 1979—2016 年、13,880 天的来水资料。源文件的 m³ 与 GWh 版本在低值区间并非直接一致：10,796 个零能量位置均对应正水量。每日水量在原代码中集中于午夜，其余小时置零；默认一小时下日总量保持，但小时内调节机会不同于均匀入流。代码选取的 2016 年来水又通过 365 天日历映射，遗漏闰日。该文件不含 2020 年水文，不能直接与 2020 年风光组合为同天气年观测。

初始库容和有效库容的参考亦需统一。43 座水库中，40 座的初始值高于有效库容；按总库容减有效库容推算死库容后，再调整初值，会有 11 座出现负值。不能通过直接截断完成校准。原代码设置循环储能，根据 PyPSA 文档，该模式忽略给定初值，因此上述冲突本身不证明原程序不可行。[17]

资产年代核对确认，归档白鹤滩和乌东德的完整容量合计 26,200 MW，而 2020 年末两站已经投产的容量合计为 6800 MW：白鹤滩首批机组在 2021 年投产，乌东德 2020 年投产 8 台、单台 850 MW。[18–19] 19,400 MW 的差额是输入年份差异，不是可由灵活性避免的投资。乌东德还需按年中陆续投运处理，不能用年末容量覆盖全年。

GEM 文件的水电记录是全厂级信息，不能仅按全厂起始年份推回每台机组；跨省电站的省份标签也需核对接入电网。当前完成了数据审计和两站年末容量校核，完整水文、库容和地区发电回测仍未完成。

'''
assert '## 3. 已实现的计算任务方法' in text
text=text.replace('## 3. 已实现的计算任务方法',section+'## 3. 已实现的计算任务方法',1)
anchor='### 5.3 尚待完成的地区对照与可靠性验证'
assert anchor in text
text=text.replace(anchor,'''### 5.3 水量守恒的梯级水电扩展

联合求解器新增各水库的可用水量状态，以当地增量来水、上游发电放水及弃水、本站发电耗水与弃水建立连续守恒。水量采用 hm³，发电采用 MW，以各站 m³/MWh 系数换算。初始可用水量显式给定，期末回到相同水量；机组可用率允许随投运时间变化。这样，上游发电量不会直接复制为下游可发电量。当前采用无河道时延、固定耗水系数近似，尚未包含防洪、生态下泄、水头变化与蒸发。

该扩展通过 74 项检查，其中包括 60 个独立动态规划算例。验证重新计算了每座水库的原始 m³ 收支、全流域来水与出口水量以及电力平衡；此前 118 项联合模型检查也在扩展后复跑通过。所有案例仍为数学验证，不代替实际流域校准。完整方程与来源限制见《水电约束与数据校核 v0.1》。

### 5.4 尚待完成的地区对照与可靠性验证''',1)
text=text.replace('## 配图与补充材料状态','''17. PyPSA，[Store 组件文档](https://docs.pypsa.org/stable/api/components/types/stores/)，循环与初始状态参数语义，2026-09-14 核对。
18. 三峡集团，[2021，历史镌刻下“白鹤滩时间”](https://www.ctg.com.cn/sxjt/xwzx55/zhxw23/2024081106181629105/index.html)，正文发布日期 2022-01-12；不以迁移后的网址年份作为事件年份。
19. 三峡集团，[乌东德水电站半年投产8台巨型机组](https://www.ctg.com.cn/sxjt/xwzx55/zhxw23/2024081106052368282/index.html)，正文发布日期 2020-12-20。

## 配图与补充材料状态''',1)
(folder/'论文工作稿_v0.4.md').write_text(text)
path=ROOT/'outputs/research/reports/研究进度与待完成项.json'
status=json.loads(path.read_text())
status['previous_goal_turn_classification']='progress: previous goal turn implemented and verified joint planning, reconciled nuclear vintage, and wrote manuscript v0.3; this continuation inspected that evidence before adding water-conserving hydro and source audits'
items=[
 '10 major-hydro archive members obtained and verified; 43 dams and 13880 daily rows from 1979-2016 decoded and audited',
 'water-conserving reservoir cascade coupled to joint LP; 74 checks including 60 independent dynamic-programming oracles passed; prior 118 checks rerun',
 'Baihetan/Wudongde 2020 year-end operating capacity reconciled with operator publications; 19400 MW vintage difference identified',
 'manuscript v0.4, hydro methods/data supplement and phase report 04 written'
]
for item in items:
    if item not in status['completed_evidence']:status['completed_evidence'].append(item)
status['latest_manuscript']='outputs/research/manuscript/论文工作稿_v0.4.md'
status['requirements_still_open']['Q2']='joint grid-compute and water-conserving reservoir solvers mathematically verified; calibrated regional planning/dispatch and independent same-reliability comparison pending'
status['next_actions']=[
 'resolve usable reservoir storage references, incremental vs catchment inflow, coherent weather years and intra-day flow treatment',
 'reconcile remaining thermal/wind/solar vintages, partial hydro commissioning, cross-province grid injection and gross/net load boundaries',
 'finish transmission edge reconciliation and regional baseline calibration, then run S0/S1/S2',
 'calibrate task service and recovery costs without treating interactive inference as freely deferrable',
 'independent chronological outages and multi-weather adequacy validation, then S3 participation and system net benefit',
 'complete national 2030/2035 results, English paper, final figures and portable reproduction package'
]
status['live_jobs']=[]
path.write_text(json.dumps(status,ensure_ascii=False,indent=2))
print('Updated manuscript v0.4 and open research checklist')
