from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[3]
folder=ROOT/'outputs/research/manuscript'
text=(folder/'论文工作稿_v0.2.md').read_text()
text=text.replace('版本：v0.2','版本：v0.3',1)
text=text.replace('本稿的已完成部分是公开数据再分析、计算任务与承诺成本模型，以及电力系统输入和可靠性资料审计。',
                  '本稿的已完成部分是公开数据再分析、计算任务与承诺成本模型、计算任务与电力投资运行联合求解器及其数学验证，以及电力系统输入和可靠性资料审计。',1)
text=text.replace('模型经手算和穷举案例验证；系统投资、排放、可靠性与机制效果仍待联合研究。',
                  '任务与联合规划模型经手算、穷举及独立投资算例验证；真实地区的投资、排放、可靠性与机制效果仍待校准后的联合研究。',1)
insertion='''### 2.5 核电基年输入的年份与统计范围核对

进一步将归档核电容量与官方逐机组资料逐省比对，发现归档中标为“2020”的 31 个省级值，全部等于官方 2021 年“首次装料后列入运行统计”的容量按 MW 取整结果，合计分别为 54,647 MW 与 54,646.95 MWe。[14–15] 这组逐省数值对应关系证明该列不能直接作为同口径的 2020 年输入，但不能据此断言档案未公开的制作过程。

官方 2020 年同口径资料包含 49 台机组。已从表格图像逐行录入并放大核对，额定容量、发电量和上网电量之和分别为 51,027.16 MWe、3662.43 亿 kWh 和 3428.54 亿 kWh，与表内合计一致。2021 年同口径容量增加 3619.79 MWe，其中 3608.79 MWe 来自四台新列入统计的机组，另有同一机组跨年度报告的额定值变化 11 MWe；额定值变化本身不证明发生了物理扩容。

“已装料运行”“已并网”和“商业运行”具有不同边界。福清 5 号机组在 2020 年已经并网并列入运行表，但商业运行始于 2021 年。[16] 因此不能把上述 51.03 GW 与商业运行或其他统计口径的约 49.9 GW 直接当作彼此错误。2020 年新并网机组还必须按实际投运时间处理，不能把年末容量赋予全年。当前已形成省级核电年度发电与上网电量校准目标，尚未据此构造或验证逐时出力。

'''
assert '## 3. 已实现的计算任务方法' in text
text=text.replace('## 3. 已实现的计算任务方法',insertion+'## 3. 已实现的计算任务方法',1)
start=text.index('## 5. 待实施的联合系统研究')
end=text.index('## 6. 讨论与当前局限')
replacement='''## 5. 联合系统模型与待完成的地区研究

### 5.1 已实现的联合求解器

当前已将多节点本地计算任务与发电、输电、储能投资及连续时序运行联立求解。投资变量跨场景共享，运行与任务变量按场景设置；目标包含研究期投资、概率加权发电运行、线路流量、储能吞吐、指定服务延后成本和非 AI 未供电惩罚。投资费用的年化与研究期权重由调用方明确设置。

任务沿用逐批到达、期限与工作量约束，算力池计入空闲功率和并网功率上限。固定外部功率轨迹时仍保留逐批任务等式，因而不会把电力侧可以供给、计算侧却无法完成的轨迹误判为可行。输电按发送端容量和接收端损耗处理，两方向共享容量；储能状态连续递推，期末回到初始状态。

模型可设置期望排放和非 AI 未供电量上限。零未供电上限只证明所提供场景内的供需约束满足，不能替代随机故障和样本外可靠性检验。当前运输网络、分时执行和完美预见均是模型近似；尚未实现机组启停、任务迁移、检查点开销和非预见性控制。完整公式、单位、约束和验证方法另见《联合模型方法与验证 v0.1》。

### 5.2 联合模型数学验证

首轮共完成 118 项检查，其中包括 60 个利用分段线性成本转折点独立求解的投资案例、40 个直接穷举排程的单位任务案例，以及损耗、恢复、时间单位、初末储能、排放和未供电等检查。验证从输出独立重构了电力平衡、任务完成量、储能状态和成本分项，所有检查通过。

一个完全人为设定的两小时案例检验了任务时移能否正确改变新增供电容量。两个方案完成同一批任务；在首小时存在可用电源、第二小时需要新建供电能力的条件下，模型正确识别出时移可避免该案例的新增容量。该算例是实现检验，不是中国容量价值的初步估计，也不作为原创实证发现。

### 5.3 尚待完成的地区对照与可靠性验证

地区研究仍需将核对后的资产年代、投运时间、负荷、风光和完整水电约束接入模型并完成基年回测。对于可迁移任务，需要加入有来源的通信流量、时延、硬件兼容及目的地容量约束。

S0、S1、S2、S3 分别表示刚性基准、企业自主优化、系统协调和机制实施。各情景使用相同的任务需求、服务质量要求和供电可靠性标准。企业电费及补偿影响参与决策，但社会资源成本核算应避免与发电成本重复相加。成本目标不预设排放同时最优。

容量价值需通过增加或减少供电能力，使对照系统在独立连续时序的故障、天气和需求样本下具有相同可靠性来识别。不能以平均功率降幅或外生比例代替可靠容量检验。关键任务服务指标与电力未供电指标分别记录。

机制部分优先研究有期限、持续时间和恢复边界的可验证承诺。比较给定承诺下的最低兑现成本、补偿及企业参与收益，并检查基线操纵、信息需求和违约处置。正式机制效果尚未产生。

'''
text=text[:start]+replacement+text[end:]
text=text.replace('当前成本模型仅包括运行电费与可指定的服务成本，检查点、迁移、额外设备和风险成本仍待加入；价格也尚未与电网模型形成内生反馈。',
                  '企业承诺成本模型目前包括运行电费与可指定的服务成本；联合系统模型另已纳入发电、储能和输电投资运行成本。检查点、任务迁移、额外服务器和风险成本仍待加入，企业价格也尚未与电网模型形成内生均衡反馈。')
text=text.replace('## 配图与补充材料状态','''14. 中国核能行业协会，国家原子能机构转载，[2020 年 1—12 月全国核电运行情况](https://www.caea.gov.cn/n6760340/n6760356/c6827514/content.html)，表 1、表 2；图像已经逐行核对。
15. 中国核能行业协会，国家原子能机构转载，[全国核电运行情况（2021 年 1—12 月）](https://www.caea.gov.cn/n6760340/n6760356/c6827530/content.html)，表 1、表 3 及统计范围说明。
16. 中国核工业集团，[First Hualong One begins commercial operation](https://en.cnnc.com.cn/2021-02/02/c_1026347.htm)，2021 年 2 月 2 日。

## 配图与补充材料状态''',1)
(folder/'论文工作稿_v0.3.md').write_text(text)
status_path=ROOT/'outputs/research/reports/研究进度与待完成项.json'
status=json.loads(status_path.read_text())
status['previous_goal_turn_classification']='no_progress: previous user-directed turn restated the agreed research direction and plan without changing research state; this continuation revalidated files and executed joint-model validation and nuclear vintage reconciliation'
status['last_verified']='2026-09-14'
status['completed_evidence'] += [
 'joint grid-compute planning LP implemented; 118 checks including 60 independent capacity oracles and 40 exhaustive task oracles passed',
 'all 31 archive nuclear province values match rounded official 2021 first-loaded fleet despite 2020 column label',
 'official 2020 nuclear 49-unit capacity, gross/net generation and two first-grid dates extracted; all three national totals reconciled',
 'manuscript v0.3, joint-model methods supplement v0.1 and phase report 03'
]
status['requirements_still_open']['Q2']='joint mathematical solver verified; calibrated regional planning/dispatch and independent same-reliability comparison pending'
status['next_actions']=[
 'use official nuclear unit dates and generation targets; reconcile remaining thermal/wind/solar vintages and gross/net load boundary',
 'obtain major-hydro reservoir and inflow inputs, reconcile leapday and province network edges',
 'calibrate workload/service profiles and avoid hourly deferral of interactive traces',
 'run calibrated regional S0/S1/S2 planning and dispatch, then independent chronological reliability validation',
 'add checkpoint/migration/extra-server/risk costs and validate S3 participation and net system benefit',
 'complete national 2030/2035 multi-weather analysis and final English manuscript plus reproduction package'
]
status['latest_manuscript']='outputs/research/manuscript/论文工作稿_v0.3.md'
status['live_jobs']=[]
status_path.write_text(json.dumps(status,ensure_ascii=False,indent=2))
print('Written manuscript v0.3 and updated authoritative status; goal remains in_progress.')
