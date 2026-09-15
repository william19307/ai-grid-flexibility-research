"""Compose 论文工作稿 v0.5 and 阶段研究报告 06 from v0.4 plus audit JSON / CSV outputs (numbers are read, not typed)."""
from pathlib import Path
import json,pandas as pd,numpy as np
ROOT=Path(__file__).resolve().parents[3];T=ROOT/'outputs/research/tables';M=ROOT/'outputs/research/manuscript';R=ROOT/'outputs/research/reports'
hel=json.load(open(T/'helios_trace_audit.json'));ali=json.load(open(T/'alibaba_pai_2020_trace_audit.json'));phi=json.load(open(T/'philly_trace_audit.json'))
hs=hel['gpu_job_statistics'];as_=ali['statistics'];ps=phi['statistics']
grid=pd.read_csv(T/'regional_smoke_grid_summary.csv');g24=grid[grid.W==24]
base=g24[g24.case=='NOAI'].set_index(['province','export','ai_share'])
def inc(p,e,a,c,m):
    r=g24[(g24.province==p)&(g24.export==e)&(g24.ai_share==a)&(g24.case==c)].iloc[0];b=base.loc[(p,e,a)]
    return (r[m]-b[m])/r.ai_mwh
def gap(p,e,a):
    s0=inc(p,e,a,'S0','total_cost');s0b=inc(p,e,a,'S0b','total_cost');s1=inc(p,e,a,'S1','total_cost');s2=inc(p,e,a,'S2','total_cost')
    return s0,s0b,s1,s2
pct=lambda x:f'{x*100:.1f}%'
sec_traces=f"""### 2.8 公开生产 GPU 集群轨迹：观测到的等待、时长与利用率

为给任务到达、完成时间与可容忍延迟提供经验依据，新增取得三套公开生产集群轨迹并逐一登记来源、许可与校验值（数据登记 D12–D14）。三套轨迹都不含功率遥测，也不含服务期限；生产中观测到的排队等待只能作为用户实际容忍延迟的下界，不能解释为期限。

**Helios（商汤，2020 年 4—9 月，4 个集群）。** [7] 共 {sum(v['rows'] for v in hel['clusters'].values()):,} 条作业记录，其中 GPU 作业 {hs['gpu_jobs_all_states']:,} 条；`queue` 与 `duration` 字段分别与起止时间差完全一致（最大差 {max(v['queue_col_equals_start_minus_submit_max_abs_s'] for v in hel['clusters'].values()):.0f} 秒）。按 GPU 小时加权，运行时长超过 24 小时的作业占 {pct(hs['gpu_hour_weighted_duration_share_gt_24h'])}；观测等待超过 1 小时的占 {pct(hs['gpu_hour_weighted_queue_share_gt_1h'])}，超过 6 小时的占 {pct(hs['gpu_hour_weighted_queue_share_gt_6h'])}，超过 24 小时的占 {pct(hs['gpu_hour_weighted_queue_share_gt_24h'])}。被取消作业占 GPU 小时的 {pct(hs['gpu_hours_share_by_state'].get('CANCELLED',0))}，说明"已消耗的 GPU 小时"与"完成的服务"不能等同。

**阿里 PAI（2020 年 7—8 月，约 6,500 GPU）。** [6] 作业 {ali['job_rows']:,} 条、任务 {ali['task_rows']:,} 条、实例传感器记录 {ali['sensor_rows_with_gpu_util']:,} 条。README 定义作业 `start_time` 为提交时间、任务 `start_time` 为启动时间，两者之差为调度等待。{as_['terminated_gpu_jobs']:,} 个成功结束的 GPU 作业中，等待的第 99 百分位仅 {as_['wait_hours']['p99']*60:.1f} 分钟，GPU 小时加权等待超过 1 小时的比例为 {pct(as_['gpu_hour_weighted_wait_share_gt_1h'])}；即该平台在观测期内几乎不排队，因此它不能提供可容忍延迟的证据，但提供了运行时长（超过 24 小时的作业占 GPU 小时 {pct(as_['gpu_hour_weighted_run_share_gt_24h'])}）和利用率证据：{pct(as_['instance_share_gpu_util_below_10pct'])} 的实例平均 GPU 利用率低于 10%，中位数为 {as_['instance_avg_gpu_util_percent_of_one_gpu']['p50']:.1f}%。这直接影响空闲功率与冗余算力假设。

**Philly（微软，2017 年 8—12 月）。** [8] {phi['jobs']:,} 个作业；{ps['gpu_jobs_with_times']:,} 个有完整时间的 GPU 作业中，GPU 小时加权等待超过 1 小时的占 {pct(ps['gpu_hour_weighted_wait_share_gt_1h'])}，超过 24 小时的占 {pct(ps['gpu_hour_weighted_wait_share_gt_24h'])}；运行超过 24 小时的占 {pct(ps['gpu_hour_weighted_run_share_gt_24h'])}。逐分钟机器级 GPU 利用率共 {ps['gpu_minute_samples']:,} 个样本，{pct(ps['share_of_gpu_minutes_below_10pct_util'])} 低于 10%。该轨迹硬件为 2017 年代，只用于形状对照。

三套轨迹的共同含义：多数 GPU 小时来自持续一天以上的长作业，具备时间转移的物理基础；但观测到的等待分布因平台容量策略而异，从几乎为零到近两成 GPU 小时超过 1 小时。因此论文不能采用单一的"可延迟比例"，必须把期限作为按业务类别设定并做敏感性分析的参数，并把等待下界与 DynamoLLM 等服务约束证据一起作为区间的两端。图：`../figures/production_traces_wait_duration_util.png`。
"""
sec_region=f"""### 5.5 选区筛选矩阵

用已锚定的年度负荷、归档装机（未核实为 2020 年实际装机）、重建的省间联络容量（未验证）以及 2022 年国家算力枢纽批复，对 31 省做筛选（`../tables/region_selection_matrix.csv`）。三类候选：A 类新能源富集且水电占比低的枢纽省（甘肃、宁夏、内蒙古、河北），B 类负荷中心枢纽省（江苏、广东、浙江），C 类水电混合枢纽省（贵州、四川）。内蒙古存在蒙西蒙东两网需拆分；甘肃的大型水电在归档中缺失，须补官方数据；宁夏年度负荷锚定偏差最大。当前建议首轮采用甘肃或宁夏、江苏、贵州，最终以校准数据可得性决定。

### 5.6 单省 S0/S0b/S1/S2 管线的未校准粗跑

已把逐批任务模型、承诺成本模型与联合规划模型接成单省管线：S0 为全速最早期限调度的固定轨迹；S0b 为时间上刚性但采用能完成每小时工作量的最低能耗实测档位的固定轨迹，用于把"降频节能"与"时间转移"分开；S1 为企业在给定分时电价下的最低电费调度，得到的轨迹固定后进入系统模型；S2 为任务变量自由的系统协调解。四个 2020 年代表周（1、4、7、10 月各一周）作为等概率场景共享投资；省间交换用一个外部市场节点近似。输入为年度锚定但逐时形状未验证的负荷、未核实的归档装机、分析者设定的算力规模（峰荷的 5% 或 20%）、空闲功率、均匀到达与期限、电价形状。没有机组启停与煤电最小出力约束。

粗跑结果只用于验证管线并观察数量级（`../tables/regional_smoke_grid_summary.csv`，图 `../figures/regional_smoke_grid_W24.png`）：

- 甘肃：在归档的 2020 年系统中煤电装机远高于峰荷，且没有零边际成本小时，四种情景的单位 AI 电量增量成本完全相同（均为煤电边际成本），灵活性没有任何价值。
- 贵州（不允许外送、AI 占峰荷 20%、期限 24 小时）：单位 AI 电量的增量系统成本 S0 为 {gap('Guizhou',False,0.2)[0]:.2f}、S0b 为 {gap('Guizhou',False,0.2)[1]:.2f}、S1 为 {gap('Guizhou',False,0.2)[2]:.2f}、S2 为 {gap('Guizhou',False,0.2)[3]:.2f} 欧元每兆瓦时（归档成本口径）；刚性到协调的差距约 {((gap('Guizhou',False,0.2)[0]/gap('Guizhou',False,0.2)[3])-1)*100:.1f}%，其中降频节能贡献了相当部分。期限从 6 小时放宽到 72 小时对结果几乎没有影响，说明该设定下价值主要来自日内转移。
- 江苏（不允许外送、AI 占峰荷 20%）：刚性 S0 触发 {g24[(g24.province=='Jiangsu')&(~g24.export)&(g24.ai_share==0.2)&(g24.case=='S0')].new_ocgt.iloc[0]:.0f} MW 燃气调峰新增投资，S0b、S1、S2 均避免了这项投资；允许外送时投资消失。

这些结果表明管线可以同时输出投资、运行、排放与弃电指标并区分四种情景，但其数值不能用于任何实证陈述。价值是否出现取决于系统是否存在零边际小时与容量紧缺，这与文献 [3][9] 的方向一致，需在校准的 2030 情景中重新检验。
"""
v4=open(M/'论文工作稿_v0.4.md',encoding='utf-8').read()
v5=v4.replace('**版本：v0.4a，2026-09-15。','**版本：v0.5，2026-09-15。')
v5=v5.replace('## 3. 已实现的计算任务方法',sec_traces+'\n## 3. 已实现的计算任务方法')
v5=v5.replace('## 6. 讨论与当前局限',sec_region+'\n## 6. 讨论与当前局限')
v5=v5.replace('本稿的已完成部分是公开数据再分析、计算任务与承诺成本模型、计算任务与电力投资运行联合求解器、水量守恒的梯级水电扩展及其数学验证，以及电力系统输入和可靠性资料审计。',
 '本稿的已完成部分是公开数据再分析、三套生产集群轨迹审计、计算任务与承诺成本模型、计算任务与电力投资运行联合求解器、水量守恒的梯级水电扩展及其数学验证、电力系统输入和可靠性资料审计、选区筛选，以及单省 S0/S0b/S1/S2 管线的未校准粗跑。')
v5=v5.replace('6. Wu 与 Kan，','6. Weng 等，MLaaS in the Wild: Workload Analysis and Scheduling in Large-Scale Heterogeneous GPU Clusters，NSDI 2022，[轨迹发布](https://github.com/alibaba/clusterdata/tree/master/cluster-trace-gpu-v2020)。\n7. Hu 等，Characterization and Prediction of Deep Learning Workloads in Large-Scale GPU Datacenters，SC 2021，[轨迹发布](https://github.com/S-Lab-System-Group/HeliosData)。\n8. Jeon 等，Analysis of Large-Scale Multi-Tenant GPU Clusters for DNN Training Workloads，USENIX ATC 2019，[轨迹发布](https://github.com/msr-fiddle/philly-traces)。\n\n（以下沿用 v0.4 编号，正文引用 [6][7] 指数据集时以本节对应条目为准）\n\n6. Wu 与 Kan，')
open(M/'论文工作稿_v0.5.md','w',encoding='utf-8').write(v5)
rep=f"""# 阶段研究报告 06：生产集群轨迹、选区筛选与地区管线粗跑

日期：2026-09-15。研究仍在进行。本轮交付的是任务侧经验分布、选区筛选和端到端管线验证；仍然没有校准后的地区结果，也没有 AI 灵活性价值、投资替代、排放或机制效果的结论。

## 本轮完成的工作

1. 修复了阶段报告与表格中指向本地 Codex 目录的绝对路径，全部改为仓库相对路径。
2. 取得并审计三套公开生产 GPU 集群轨迹，登记为 D12–D14：
   - Helios（商汤）：{sum(v['rows'] for v in hel['clusters'].values()):,} 条作业，GPU 作业 {hs['gpu_jobs_all_states']:,} 条。GPU 小时加权：运行超过 24 小时占 {pct(hs['gpu_hour_weighted_duration_share_gt_24h'])}；等待超过 1、6、24 小时分别占 {pct(hs['gpu_hour_weighted_queue_share_gt_1h'])}、{pct(hs['gpu_hour_weighted_queue_share_gt_6h'])}、{pct(hs['gpu_hour_weighted_queue_share_gt_24h'])}；取消作业占 {pct(hs['gpu_hours_share_by_state'].get('CANCELLED',0))}。
   - 阿里 PAI：{ali['job_rows']:,} 作业、{ali['task_rows']:,} 任务、{ali['sensor_rows_with_gpu_util']:,} 传感器记录。等待第 99 百分位 {as_['wait_hours']['p99']*60:.1f} 分钟；运行超过 24 小时占 GPU 小时 {pct(as_['gpu_hour_weighted_run_share_gt_24h'])}；{pct(as_['instance_share_gpu_util_below_10pct'])} 的实例平均 GPU 利用率低于 10%。
   - Philly（微软）：{phi['jobs']:,} 作业；等待超过 1 小时占 GPU 小时 {pct(ps['gpu_hour_weighted_wait_share_gt_1h'])}；逐分钟 GPU 利用率 {ps['gpu_minute_samples']:,} 个样本中 {pct(ps['share_of_gpu_minutes_below_10pct_util'])} 低于 10%。
   三套轨迹均无功率、无期限；观测等待只作为可容忍延迟的下界。
3. 建立 31 省选区筛选矩阵（`../tables/region_selection_matrix.csv`），识别 A 新能源富集低水电枢纽、B 负荷中心枢纽、C 水电混合枢纽三类候选，并记录内蒙古两网拆分、甘肃大水电缺失、宁夏负荷锚定偏差等约束。
4. 把联合模型接成单省 S0/S0b/S1/S2 管线，并对甘肃、江苏、贵州 × 外送开关 × AI 规模 × 期限长度共 36 组做未校准粗跑（`../tables/regional_smoke_grid_summary.csv`）。

## 粗跑显示的机制（管线验证，不是实证）

- 无零边际小时、煤电过剩的系统（归档甘肃 2020）：四种情景重合，灵活性价值为零。
- 水电与新能源混合、外送受限的系统（归档贵州）：刚性到协调的单位 AI 电量成本差距约 {((gap('Guizhou',False,0.2)[0]/gap('Guizhou',False,0.2)[3])-1)*100:.1f}%（AI 占峰荷 20%），降频节能与日内转移各占一部分；期限 6 到 72 小时几乎不改变结果。
- 负荷中心（归档江苏，不允许外送，AI 占峰荷 20%）：刚性运行触发约 {g24[(g24.province=='Jiangsu')&(~g24.export)&(g24.ai_share==0.2)&(g24.case=='S0')].new_ocgt.iloc[0]:.0f} MW 燃气调峰投资，任何一种灵活运行都避免了它。

这些方向与既有规划研究一致，不构成新发现；它们说明结论将取决于校准后系统中零边际小时与容量紧缺的分布，而非灵活性参数本身。

## 已更新的材料

- [论文工作稿 v0.5](../manuscript/论文工作稿_v0.5.md)：新增 2.8 节生产轨迹、5.5 节选区筛选、5.6 节管线粗跑。
- [英文核心论文骨架 v0.1](../manuscript/core_paper_en_v0.1.md)：Nature Energy 结构，所有未完成结果以 PENDING 标注。
- 审计记录：`../tables/helios_trace_audit.json`、`../tables/alibaba_pai_2020_trace_audit.json`、`../tables/philly_trace_audit.json`。
- 图：`../figures/production_traces_wait_duration_util.png`、`../figures/regional_smoke_grid_W24.png`。
- 脚本：`../../../work/research/analysis/audit_helios.py`、`audit_alibaba_pai_2020.py`、`audit_philly.py`、`build_region_selection_matrix.py`、`run_regional_smoke_s0_s1_s2.py`。

## 仍未完成

最终选区与其官方分省装机、分时电价、省间交换数据；把轨迹分布接入任务模型并按业务类别设定期限区间；煤电最小出力与机组约束；逐时负荷独立验证；校准后的 2030 地区 S0—S3；多天气与故障可靠性检验；英文正文与复现包。
"""
open(R/'阶段研究报告_06.md','w',encoding='utf-8').write(rep)
print('manuscript v0.5 and phase report 06 written')
