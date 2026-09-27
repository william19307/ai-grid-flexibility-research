# 阶段37 MLPerf同硬件功率准入审计

日期：2026-09-27

## 研究问题

阶段 10–11 已说明，GPU 遥测、整机交流输入和设施电力不能互换。本阶段进一步检验公开基准是否已经提供“同一硬件、同等质量、常规模式与限功率模式均有整机交流功率”的可用对照，从而替代尚未完成的现场实验。

## 固定来源与方法

审计固定在 MLCommons 官方 `inference_results_v4.0` 仓库提交 `343c3d2cb03f2ae02b1023a44e4a45ba4b8422ef`。对象为 NVIDIA DGX H100，包含 8 张 H100-SXM-80GB；常规与 MaxQ 系统描述除系统名称外逐字段一致。MLPerf 功率规则要求在系统交流输入侧测量受 LoadGen 激活的主机、加速器、内存和风扇，并要求功率与性能来自同一次运行。

脚本匹配常规和 MaxQ 目录下相同任务、精度目标和场景的有效结果，读取性能摘要、精度记录、MaxQ 的 PTDaemon `server.json` 及 NVIDIA 配置中的 GPU 功率上限。原始基准仓库不随本仓库再分发；固定提交、相对路径和 SHA-256 写入来源清单。

另核读 Elsayed 等 2026 年 *Scientific Data* 的 H100/B200 高分辨率训练数据。该数据提供 20 ms GPU 遥测和 32 个节点训练会话，但作者明确说明节点功率是各 GPU 功率之和，节点 CPU 功率因虚拟化权限缺失，因此不能视为整机交流输入。

## 结果

共得到 24 个任务—精度—场景配对，覆盖 13 个任务/精度配置和 Offline、Server 两种场景。所有性能摘要均为 VALID，两侧精度记录均存在。MaxQ 每组由 Yokogawa WT333E 交流功率分析仪记录至少 600 个样本；平均整机输入为 3.777–5.377 kW。

与同系统常规性能相比，MaxQ 保留 65.13%–82.03% 的性能，中位数为 74.57%，对应 17.97%–34.87% 的性能损失。任务差异明显：同为 350 W 单卡上限时，不同任务和场景仍呈现不同的性能保留率。24 行包含共享相同运行记录的精度目标，不能当作 24 个独立统计重复，也没有用来拟合通用功率曲线。

常规模式目录没有提交交流功率日志。由此只能确认：在相同硬件描述与有效精度记录下，限功率运行伴随任务相关的性能损失，并且其限功率侧整机输入可测。不能计算常规到 MaxQ 的整机功率差、整机能耗差或单位有效工作节能率。若用 MaxQ 功率除以两侧性能，仍缺少常规功率分子，无法补出能效对照。

## 准入决定

本阶段准入两类事实：

1. 公共标准基准能够在交流系统边界同时记录限功率侧性能与功率；
2. 同一硬件上的服务性能代价随任务和场景改变，不能把一个档位折减系数无条件转移到 Helios 任务。

本阶段拒绝三类用途：

1. 不把单侧 MaxQ 功率解释为整机节能率；
2. 不把 H100 推理结果校准为 Helios 训练任务或三省数据中心功率曲线；
3. 不把 GPU 遥测之和解释为含主机、内存、风扇、网络、制冷或 UPS 的设施功率。

公开数据缩小了现场实验设计空间，但没有关闭硬件证据门槛。下一次可形成节能主张的实验必须在同一节点、相同有效工作与质量下，对常规和每个候选档位都记录同步交流功率、完成时间、空闲与切换能量，并报告重复运行和不确定度。

## 产物与复现

- `mlperf_power_admission/matched_results.csv`：24 个配对的性能、MaxQ 交流功率、精度摘要、功率上限和原文件哈希；
- `mlperf_power_admission/audit_summary.json`：范围、统计量与准入决定；
- `mlperf_power_admission/system_identity.json`：两侧系统描述差异；
- `mlperf_power_admission/source_manifest.json`：固定官方提交、相对路径和 100 余项文件哈希；
- `mlperf_power_admission/adjacent_node_dataset_audit.json`：高分辨率节点训练数据的可用范围和排除用途；
- `mlperf_power_admission/independent_verification.json`：16 项独立结构与边界检查；
- `work/research/analysis/audit_mlperf_power_pair.py`：从固定官方仓库构建审计表；
- `work/research/analysis/verify_mlperf_power_pair.py`：不读取外网的独立检查。

运行前将官方仓库固定提交放在 `work/tmp/mlperf-inference-v40`，然后执行：

```bash
python3 work/research/analysis/audit_mlperf_power_pair.py
python3 work/research/analysis/verify_mlperf_power_pair.py
```

16 项检查全部通过，包括 24 个唯一配对、正值性能、合理交流功率、每行至少 600 个功率样本、两侧精度记录、固定提交、系统字段一致及显式拒绝节能率。

## 对论文的决定

下一版正文应加入这一公开同硬件审计，以实证说明“相同硬件”仍不足以建立节能结论：两侧必须同时具备定义一致的功率与有效工作。该结果可以增强功率边界论证，并给出公开的服务性能范围；不能替代共同硬件上的双侧测量，也不改变当前 `nature_energy_system_claim_ready=false` 的判断。
