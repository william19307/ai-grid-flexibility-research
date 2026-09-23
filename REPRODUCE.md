# 复现说明

当前独立重建先读 [阶段 27](outputs/research/revision/clean_reconstruction/RUNBOOK.md)，显式来源版本复算再读 [阶段 28](outputs/research/revision/reviewed_tariff_version/RUNBOOK.md)。同机新克隆/隔离环境的限定链条已在显式版本下复算且数值一致；严格原 HTML 恢复仍是 13/14。下列历史流程不表示整篇论文或所有原件已恢复。

环境：`work/figure-env`（Python 3.14；numpy、pandas、scipy、matplotlib、h5py、tables、tabulate）。原始外部数据不入库，按 `outputs/research/tables/data_registry.csv` 的来源、版本与校验值重新获取到 `work/research/sources/`。

按顺序运行（均在仓库根目录，`P=work/figure-env/bin/python`）：

| 步骤 | 脚本 | 产出 |
|---|---|---|
| 1 源输入审计 | `analysis/audit_archive_inputs.py`, `audit_china_sources.py`, `audit_plant_tracker.py`, `audit_major_hydro.py`, `reconcile_nuclear_baseyear.py`, `extract_official_reliability.py` | `tables/*_audit.json`, 对照表 |
| 2 负荷锚定 | `analysis/calibrate_annual_load.py`, `plot_load_calibration.py` | `prepared/load_2020_annual_anchored_hourly_shape_UNVALIDATED.npz`, 校准图 |
| 3 模型验证 | `analysis/validate_sequential_tasks.py`, `validate_response_cost.py`, `validate_coupled_grid_compute.py`, `validate_reservoir_coupling.py` | `tables/*_validation.json` |
| 4 生产轨迹审计 | `analysis/audit_helios.py`, `audit_alibaba_pai_2020.py`, `audit_philly.py`, `plot_production_traces.py` | `tables/*_trace_audit.json`, 分布表, 图 |
| 5 选区与机组清单 | `analysis/build_region_selection_matrix.py`, `build_gem_fleet_three_provinces.py`（31 省版本见阶段 08 内联脚本，产出 `gem_fleet_all_provinces_2020_2030.csv`） | 选区矩阵, GEM 机组清单 |
| 6 2020 粗跑 | `analysis/run_regional_smoke_s0_s1_s2.py --grid [--coal_min 0.4]`, `summarize_smoke_grids.py`, `plot_regional_smoke.py` | `tables/regional_smoke_*`, 图 |
| 7 2030 情景 | `analysis/run_regional_2030_s0_s3.py --grid --ext_mode price` 与 `--ext_mode neighbours`, `summarize_2030_grid.py price|neighbours` | `tables/regional_2030_*`, 图 |
| 8 文稿 | `drafts/update_manuscript_v05.py` … `v07.py` | 工作稿、阶段报告、英文稿 |

所有脚本路径相对 `work/research/`。每个脚本头部写明证据层级；`tables/*_NOT_*`、`*_UNVERIFIED*`、`*_UNVALIDATED*` 命名的文件不得作为实证结果引用。

## 2026-09-22 起的实质修订实验

上表是冻结稿历史流程。审读后新实验位于 `outputs/research/revision/`，状态及未解决要求见 `REVISION_STATUS.md`，不能由旧版 READY 推断新版完成。

在仓库根目录、原始与 prepared 输入齐全时依次运行：

```sh
work/figure-env/bin/python work/research/analysis/build_hydro_revision_inventory.py
work/figure-env/bin/python work/research/analysis/validate_hydro_revision.py
work/figure-env/bin/python work/research/analysis/run_hydro_revision.py --treatment legacy
work/figure-env/bin/python work/research/analysis/run_hydro_revision.py --treatment split_pumped_storage --duration 8
work/figure-env/bin/python work/research/analysis/run_hydro_revision.py --treatment remove_pumped_storage
work/figure-env/bin/python work/research/analysis/sweep_hydro_revision.py
work/figure-env/bin/python work/research/analysis/audit_hydro_revision_results.py
```

运行入口拒绝覆盖已完成配置。重现时应使用新检出目录，或先归档既有 `revision/hydro/runs/`；发生错误应先检查具体进程与日志，不能仅凭等候超时重启。第三至五条运行的默认省份为江苏、AI20%、孤岛；sweep 补充另外十组。抽蓄时长/效率是显式敏感性参数，常规水库、整机功率、任务期限等旧假设仍保留，结果仅供隔离本次修正影响。资产分类按原始 Technology 字段进行，未知类型会拒绝静默归类。

汇总审计核对运行前代码哈希、原结果复现、储能守恒、31 省总容量与未决技术类型，并输出 `paired_results.csv`。当前 prepared 数据的完整下载重建入口与锁定环境仍是开放工作，以上命令不应被表述为已经通过全新机器端到端复现。

### 阶段 02：功率边界与政策归因

在阶段 01 输入清单已生成后运行：

```sh
work/figure-env/bin/python work/research/analysis/validate_power_attribution_revision.py
work/figure-env/bin/python work/research/analysis/regress_power_attribution_revision.py
work/figure-env/bin/python work/research/analysis/sweep_power_attribution_revision.py
work/figure-env/bin/python work/research/analysis/audit_power_attribution_revision.py
work/figure-env/bin/python work/research/analysis/plot_power_attribution_revision.py
```

sweep 共定义 60 组配置，最多三个本地子进程并发；已完成结果只在源码和输入哈希均与当前一致时复用，失败输出保留并返回失败状态。单次入口 `run_power_attribution_revision.py` 拒绝覆盖目录。每组保留源码文本、运行前源码和输入哈希，独立审计不要求后续修订代码与历史代码仍相同，但会记录差异。真正重新求解须在另一检出目录准备输入并移走该检出中的旧 `power_attribution/runs/`，不可把复用计为新的独立求解。

配图读取 `factorial_results.csv`，输出 PNG/PDF/SVG 和源表哈希。分量模型、八配置的相关性及未关闭的实证缺口见阶段 02 报告。已有任务与成本回归输出单独保存在 `power_attribution/regression/`，没有覆盖冻结稿验证结果。

### 阶段 03：无 AI 反事实

在阶段 02 的输入清单和三地区中心配置已存在时运行：

```sh
work/figure-env/bin/python work/research/analysis/validate_counterfactual_revision.py
work/figure-env/bin/python work/research/analysis/sweep_counterfactual_revision.py
work/figure-env/bin/python work/research/analysis/audit_counterfactual_revision.py
```

27 组分别比较历史规则、只修正 NOAI、全煤电调度放宽；运行入口拒绝覆盖已有输出，sweep 不自动复用既有运行。每次保存实际煤电约束、源码及输入哈希。独立审计跨 AI 规模比较 NOAI，并核验只改参考不会改变 AI 场景。调度放宽不是机组组合或停运验证。

### 阶段 04：严格服务与原始时序

需要原 prepared Helios 表，以及 `work/research/sources/helios_sensetime/data/` 下四集群原始作业与容量文件。

```sh
work/figure-env/bin/python work/research/analysis/validate_strict_service_revision.py
work/figure-env/bin/python work/research/analysis/audit_strict_service_revision.py
work/figure-env/bin/python work/research/analysis/audit_chronological_helios.py
work/figure-env/bin/python work/research/analysis/verify_service_results.py
```

两个 audit 入口拒绝覆盖已有结果；重新求解应在单独检出中准备输入并归档旧 `revision/service/`。`cases/*.json` 的 `source_meta` 是 u=1 的规范化形态，实际 u 和任务量分别位于 `parameters`、`jobs`；不依据可行性改变窗口或工作形态。28 个不可行结果是研究发现，不是需要删除的运行错误。完整尾部仅是有限批次诊断；真实时序是分配的 GPU 时间，不是电功率或 SLA。

严格案例有运行前源码与输入哈希；原始时序审计的源码哈希和快照在独立核验时补充，明确记录为运行后收集。新机器可用对应来源重新取得原始文件，再核验哈希；尚未完成自动下载与全新机器端到端验证。

### 阶段 05：事件级回放与整组构造

原始 Helios 文件与 DVFS 曲线齐全时，在没有既有 `revision/replay/` 结果的新检出中运行：

```sh
work/figure-env/bin/python work/research/analysis/validate_chronological_replay.py
work/figure-env/bin/python work/research/analysis/validate_gang_replay.py
work/figure-env/bin/python work/research/analysis/sweep_chronological_replay.py
work/figure-env/bin/python work/research/analysis/verify_chronological_replay.py
work/figure-env/bin/python work/research/analysis/run_gang_replay_revision.py
work/figure-env/bin/python work/research/analysis/verify_gang_replay.py
work/figure-env/bin/python work/research/analysis/plot_chronological_replay.py
```

pilot 在求解前写入四集群、第一完整周、三种宽限的清单。LP 的时间和变量数限制是运行预算，不是不可行证明。当前历史目录还保留时间转换错误的原始尝试和修正后的 `pilot_process_results_corrected.json`；`retry_replay_time_conversion.py` 仅用于重放这次已确认终止的历史错误，修正后的代码在全新运行中不需要调用它。独立核验优先读取存在的 corrected 清单，否则读取正常清单。

所有入口拒绝覆盖既有运行。整组排程以规范秒坐标保存，并由原始作业及全状态背景独立核验；与 LP 共用同一任务群及完成基准，但不宣称全局最优。图的两个面板分母不同，已明确标注。真实 SLA、逐任务曲线、节点放置、整机能耗和省级电网收益不由这组回放认证。

### 阶段 06：固定算法的时间扩展与多曲线验证

预设清单和代码快照在结果前已提交为 `6c6cd63`。288 个条件及运行前数据哈希见 `outputs/research/revision/multiperiod/manifest.json`；回放算法未因结果改变。以下入口的 `freeze` 只可用于不存在该输出目录的干净副本，`run` 只可在尚无 `runs` 子目录时启动，防止覆盖证据；不要删除现有记录后重跑。

```bash
work/figure-env/bin/python work/research/analysis/run_gang_multiperiod_revision.py freeze
work/figure-env/bin/python work/research/analysis/run_gang_multiperiod_revision.py run
work/figure-env/bin/python work/research/analysis/verify_gang_multiperiod_revision.py
work/figure-env/bin/python work/research/analysis/summarize_gang_multiperiod_revision.py
```

现有完整输出只需运行后两项便可独立核对及重建描述性表图。原始轨迹按既有来源步骤准备，不包含于此输出包。`failed_cases.csv` 为无失败时的空表；`complete.json` 和 `independent_verification.json` 记录全部案例数量。288 个条件仅对应 12 个集群—周，不能当作独立统计重复，详细证据边界见阶段 06 报告。

### 阶段 07（已完成）：固定服务的四组政策与确定性归因界

冻结清单提交为 `091ea10`；108 个四格实验和独立核验均已完成，原进程以 0 退出。不要再次向既有输出目录启动构造；运行以下入口可核验现有记录并重建表图：

```bash
work/figure-env/bin/python work/research/analysis/verify_gang_policy_revision.py
work/figure-env/bin/python work/research/analysis/summarize_gang_policy_revision.py
```

已完成的方法检查入口为 `validate_gang_policy.py`（241 项）和 `validate_policy_attribution.py`（201 项）。可行策略份额与全局最优份额界不能混称，详见 `policy_attribution_methods_draft.md`。新增整机功率候选核查入口为 `audit_tokenpowerbench_source.py`，固定上游提交且只读取文本/结果，不执行下载代码；其结果尚不能作为整机校准。

阶段 07 的构造仍在运行时，可执行 `verify_gang_policy_revision.py --available` 检查已完成案例；它明确记录 pending，并不会使汇总入口接受不完整实验。逐案核验缓存绑定核验器源码、冻结清单、案例结果及四份排程的哈希，且校验导出的小时轨迹哈希；源码或数据变化会重新核验。最终仍须无 `--available` 执行完整核验。2026-09-22 检查点为 71 组/284 份排程，第二次同输入检查确认 71 个案例复用成功。

另有独立性能原型 `gang_policy_fast.py`，检查入口 `validate_fast_gang_policy.py`，大案例对照入口 `benchmark_fast_gang_policy.py`。它未替换当前冻结的 108 组实验。性能记录存于 `policy/performance/`，不作为新增独立研究样本。

### 阶段 08：可调整机组承诺的数学核验

```bash
work/figure-env/bin/python work/research/analysis/validate_thermal_commitment.py
work/figure-env/bin/python work/research/analysis/validate_coupled_grid_compute.py --output-dir outputs/research/revision/commitment/validation
work/figure-env/bin/python work/research/analysis/validate_reservoir_coupling.py --output-dir outputs/research/revision/commitment/validation
```

新增承诺配置由 `thermal_commitment.py` 定义，只有显式传入时才启用 MILP。75+118+74 项数学检查不能作为真实省级启停或全年可靠性的证据；参数、模型边界与后续门槛详见阶段 08 报告。省级旧冻结结果应使用其冻结版本/源代码快照复现。

煤电来源字段恢复入口：`work/figure-env/bin/python work/research/analysis/audit_coal_operational_fields.py`。需要原始 GEM XLSX 和既有逐机组选择 JSON；它只生成候选字段表与审计摘要，不覆写冻结容量或赋予缺失运行参数默认值。

### 阶段 09：已认证真实轨迹的强制功率接入

```bash
work/figure-env/bin/python work/research/analysis/validate_verified_power_bridge.py
work/figure-env/bin/python work/research/analysis/validate_thermal_commitment.py --output-dir outputs/research/revision/power_bridge/regression
work/figure-env/bin/python work/research/analysis/validate_coupled_grid_compute.py --output-dir outputs/research/revision/power_bridge/regression
work/figure-env/bin/python work/research/analysis/validate_reservoir_coupling.py --output-dir outputs/research/revision/power_bridge/regression
```

第一项需要原始输入及已认证的 Earth–Dolly–6h–江苏价形案例；只使用完整轨迹及其核验证据，不重新生成任务。文件篡改检查在临时复制件中运行，原始数据不变。整机功率和同步副本都是显式假设，解析发电机案例不构成省级结果。

阶段 07 完成状态：原构造进程已退出，108 组全部核验完成。已有输出可运行无 `--available` 的核验与汇总入口重建表图；无需也不应再次启动已有目录的构造。最终报告见 `阶段07_固定服务下的政策归因.md`。

### 阶段 10：外部整机功率来源重分析

下载 `whole_node_power/source_snapshot.json` 中的作者补充 PDF 为 `work/research/sources/whole_node_power_20260922/supplementary.pdf`；从出版方下载主文 PDF 为同目录 `main.pdf`，并核对快照哈希。需要 Poppler、numpy、matplotlib，以及独立环境中的 pdfplumber。

```bash
work/figure-env/bin/python work/research/analysis/audit_whole_node_power_source.py --pdf-python /path/to/python-with-pdfplumber
```

输出位于 `outputs/research/revision/whole_node_power/`。两种 PDF 提取核对全部 544 个表值，140 个假设条件核对统一时长能量表达。原表标准差单位保留未解，不生成置信区间；此入口不修改电网或任务模型。

### 阶段 11：共同观察窗口的条件准入预算

```bash
work/figure-env/bin/python work/research/analysis/derive_power_admission_margins.py
```

需要阶段 10 的原始 PDF、固定哈希表及提取实现。全部结果写入 `outputs/research/revision/power_admission/`；用精确十进制枚举表格舍入端点，并检查同时使用能量和时间预算的情况。其边界不包含运行波动、仪器误差或质量不确定性；补测空表位于 `revision/measurement/`，不是可分析的测量数据。

### 阶段 12：天气来源、日历与旧验证范围

```bash
work/figure-env/bin/python work/research/analysis/audit_weather_revision_inputs.py
```

入口只读既有缓存、站点表、归档输入与旧结果；不导入求解入口，不改旧表。输出到 `outputs/research/revision/weather_input_audit/`。需要本地 `openmeteo_cache` 和归档 NPZ；逐站哈希在 `cache_manifest.json`。显式 ERA5 接入试验按 `explicit_era5_pilot_manifest.json` 的 URL 下载，保存为 `work/research/sources/weather_revision_era5/gansu_solar_largest_site_2020_era5.json`。原始响应哈希绑定本次下载；以后即使只有服务耗时变化也需保留新响应与新清单，不能覆盖原记录。该试验存在时会额外校验日历与单位。

### 阶段 13：显式来源与小时区间的审计重建

**2026-09-23：旧站点请求已因阶段 15 的技术错配进入研究暂停。不要删除暂停标记后续传；先定义新技术/年代清单。现有 2020 曲线只用于审计，不是准入的省级发电输入。**

```bash
work/figure-env/bin/python work/research/analysis/rebuild_explicit_era5.py --plan-only
work/figure-env/bin/python work/research/analysis/build_explicit_era5_year.py --year 2020
work/figure-env/bin/python work/research/analysis/verify_explicit_era5_year.py --year 2020
```

后两项需要 `era5_rebuild/request_plan.json` 和 `boundary_plan_2020.json` 的所有 2020 年/下一年边界原始响应，以及配套 meta，保存在 `work/research/sources/era5_revision_2015_2024/{request_id}.json` 与 `.meta.json`。现有原始响应哈希在年度审计及状态记录中；配对缺失或哈希变化会拒绝复用，不能静默覆盖。旧站点表、旧六条曲线及旧缩放审计也是对照输入，不能把这些依赖隐去。服务响应可能随版本变化；以后下载的数据必须保留新来源记录，不能声称逐字节重建本次快照。

2020 原始和边界各 115 份完整，2015 年度 115 份完整但缺下一年边界。其余 920 年度请求未取得。年度和边界采集器共用缓存锁、计量台账，尊重滚动额度；当前二者均在网络前检查 `acquisition_hold.json`。2020 独立验证为 61 个分层小时×6 曲线，不是全部小时的独立物理校准。

### 阶段 14：固定投资完整年份诊断

```bash
work/figure-env/bin/python work/research/analysis/validate_fixed_fleet_annual.py
```

入口检查固定发电/线路/储能功率和能量，分别求最小未供电量及该水平下的经济运行；23 项核验结果在 `revision/fixed_fleet_annual/validation.json`，绑定四份源码哈希。无需原始外部观测即可运行数学检查，但这不生成省级结果。真实应用需另行绑定规划来源、测试年份使用历史以及同边界物理输入。

### 阶段 15：恢复技术/年份并对照官方风电统计

使用带 openpyxl、pandas 的 Python 运行前两项来源分析；独立 OOXML 核验仅用标准库。下方 `python` 表示该环境的解释器。

```bash
python work/research/analysis/audit_weather_site_technology.py
python work/research/analysis/audit_official_wind_2020.py
python work/research/analysis/verify_weather_site_technology.py
```

机组来源需要固定 GEM July-2025 工作簿，路径为 `work/research/sources/zenodo_16810831/Global-integrated-Plant-Tracker-July-2025_china.xlsx`，SHA256 `4ed14c94a305ec43af9ac33a49134fcee5c1271e2d93d248ab608c7781ea71d0`。120 行回查表与汇总在 `revision/weather_site_technology/`，2,902 行候选清单重建到排除的 prepared 目录，不覆盖原清单。

官方网页按 `weather_site_technology/official_2020_wind_audit.json` 所列两个 URL 获取到 `work/research/sources/renewable_observations_20260923/wind_2020_q1.html`、`wind_2020_h1_nea.html`；各有同名 `.html.meta.json`，包含 url、sha256、bytes、retrieved_utc。该记录绑定本次网页快照，网页改变时须新建版本并复核表格。18 个值与人工转录交叉核对，周期诊断不是同机组校准或独立重复实验。

### 阶段 16：技术分离候选与八请求网格配对试验

计划及采集器在新结果前冻结于 `ed4e1a2`，计划 SHA256 为 `679acfd3aa2d5acdd38e860f3b1000a8a07edbe6a511f3153f64c51e58539583`。库存构建器使用 Python 3.14.6、Shapely 2.1.2；两个独立核验器仅使用标准库。阶段 15 的 2,902 条候选 CSV 是输入，SHA256 `dce044cf7c2cd0d0a81774fc9b10e85ed566fd8e79378949e72459f36432c25a`。

地理文件保存在排除目录 `work/research/sources/weather_fleet_revision_v2/`。`province_boundaries.geojson` 来自 https://media.githubusercontent.com/media/wmgeolab/geoBoundaries/9469f09/releaseData/gbOpen/CHN/ADM1/geoBoundaries-CHN-ADM1.geojson ，SHA256 `3a00467a0db9b4136facb5f2f3d0edbfd96adb15651cfdf63991da9281030e85`。`geoboundaries_metadata.json` 是 https://www.geoboundaries.org/api/current/gbOpen/CHN/ADM1/ 当次快照，SHA256 `b5816c51ebefc26b1154872e663cd5a8eda830008f738a965d5dd610e72b09d0`；动态元数据以后改变须另留新版本，不得伪称原快照。初次下载所得 LFS 指针另存，真实边界与其对象 SHA 一致。

```bash
work/figure-env/bin/python work/research/analysis/prepare_weather_fleet_v2.py
work/figure-env/bin/python work/research/analysis/verify_weather_fleet_v2.py
work/figure-env/bin/python work/research/analysis/analyze_weather_grid_pilot_v2.py
```

最后一项需要 `pilot_plan.json`、`pilot_acquisition.json` 以及 `work/research/sources/weather_fleet_revision_v2/pilot/{id}.json` 与 `{id}.meta.json` 八组缓存。每项 URL、参数、获取时间与响应哈希见 `pilot_acquisition.json`；原始文件不进入 Git。已完整缓存无需再次下载。缺缓存时，仅可按冻结八请求入口 `acquire_weather_grid_pilot_v2.py` 获取，需保留新获取记录；API 动态响应不能保证逐字节重现旧快照，不得覆盖旧证据。新机器完整复现尚未执行。

采集器共用阶段 13 的锁和额度台账；首次干净环境需要先建立该台账目录与空 `call_ledger.jsonl`，已有台账绝不能清空。旧计划暂停标记不因新试验而解除。正式 421 格点的多年采集不在此试验内。报告及逐变量差值表只说明这四场址两种选择的数值关系，不生成省级风电容量因子。

### 阶段 17：隔离风机曲线形状与设备来源交叉读取

方案 `revision/wind_conversion_v1/conversion_plan.json` 在计算转换前提交为 `5d9884f`。它使用阶段 16 四条 nearest 响应，不新增气象请求。参考 YAML、固定 atlite 源码和海事 PDF 按 `source_manifest.json` 的 URL 保存到 `work/research/sources/wind_conversion_revision_20260923/`，逐文件校对 SHA256。发行人公告镜像的 URL/哈希另见 `equipment_source_audit.json` 的 issuer_source，保存为 `rudong_issuer_2018_065.pdf`；两个 PDF 还须保留原获取 meta。三峡网页只有本轮网页读取证据，无本地快照，复核时不得把脚本中转录字段当作自动重取的来源。

```bash
work/figure-env/bin/python work/research/analysis/compare_wind_reference_shapes.py
work/figure-env/bin/python work/research/analysis/verify_wind_reference_shapes.py
python work/research/analysis/audit_wind_equipment_sources.py
```

第三项使用含 pypdf 的解释器并要求 pdftotext 可用；本轮运行路径为 Codex bundled Python。逐小时诊断重建在排除目录 `work/research/prepared/wind_reference_shapes_2020_UNCALIBRATED.csv.gz`，摘要和哈希进入版本控制。独立数值核验覆盖全部 105,408 个小时值及 12 个积分，而非实际发电量。87 个节点检查明确重复节点和切出边界。两条参考数据由 Contributors to atlite 按 CC-BY-4.0 标记，表值经过归一化、插值和共同系数处理，署名与具体变换见阶段 17 报告。0.85 和端点线性积分仍是假设；未估计实际设备、风场损失、置信区间或省级容量价值。

### 阶段 18：同范围年度观测候选与冻结跨年诊断

方案 `revision/rudong_h2_validation/site_weather_plan.json` 于 `16934de` 冻结。三份年报按 observation_audit.json 的 source_manifest 下载为 `work/research/sources/rudong_h2_observations_20260923/annual2022.pdf` 等，保留 `.pdf.meta.json`（url、sha256、bytes、retrieved_utc），逐文件校核哈希。年报观测核验需要 pypdf 与 pdftotext；计算需 NumPy/Pandas，独立数值核验使用标准库和阶段 17 的独立标量函数。

```bash
python work/research/analysis/audit_rudong_h2_observations.py
work/figure-env/bin/python work/research/analysis/validate_rudong_h2_transfer.py
work/figure-env/bin/python work/research/analysis/verify_rudong_h2_transfer.py
```

第二项需要阶段 17 固定来源参考曲线，以及 acquisition.json 列出的三组天气响应及 meta，存于上述 sources 目录的 weather 子目录。三年 2022/2023/2024 各包含次年 1 月 1 日全天，输出取完整本年小时及下一端点。已有完整缓存不再请求；缺缓存时可运行 acquire_rudong_h2_weather.py，沿用共享额度台账和锁，不能清空账本或解除旧计划研究暂停。动态 API 字节变化须新留证据，不能冒充原快照。采集清单记录参数、URL、时间、哈希、返回网格及单位。

逐小时输出在排除目录 `work/research/prepared/rudong_h2_2022_2024_EXPLORATORY.csv.gz`，9 条件摘要与全部审计入版本控制。共 157,824 个值独立复算，包含两平年和一闰年、校准前后、三条曲线。固定 2022 年系数、显式计数 CF>1、不裁剪、不切换 gross/net、不以时间可用率当能量损失。观测舍入范围仅为显示精度，不是统计区间。此流程不等于全新机器完整研究复现、小时观测校准或省级验证。

### 阶段 19：季度观测与年度误差抵消

`revision/rudong_h2_quarterly/analysis_plan.json` 在季度聚合前冻结于 `1eac401`，SHA256 `ce972c86eb621db2a3fd7afcef71dc003ba154e7ddf8b3720586a75aaa02467f`。不重新估计阶段 18 的任何参数，不发起新气象请求。

按该目录 source_manifest.json 的六个 URL 保存对应 PDF 到 `work/research/sources/rudong_h2_quarterly_20260923/`，检查固定 SHA256。部分来源是新浪托管的公司报告原文镜像；不是新闻摘要。PDF 核验需 pypdf 和 pdftotext；本轮使用 Codex bundled Python。跨页表头须保留 PDF 原页，具体页序见 observation_audit.json。原 PDF、meta 和六个表格页渲染仅保留在排除的 sources 目录。

```bash
python work/research/analysis/audit_rudong_h2_quarters.py
work/figure-env/bin/python work/research/analysis/analyze_rudong_h2_quarters.py
work/figure-env/bin/python work/research/analysis/verify_rudong_h2_quarters.py
work/figure-env/bin/python work/research/analysis/plot_rudong_h2_quarters.py
```

第二项使用阶段 18 已冻结且校验哈希的小时诊断输出；第三项从相同原始天气和固定曲线使用独立 Decimal 实现重建，不调用生产聚合函数。绘图只读取已核验结果，PNG/PDF/SVG 与图来源哈希同存。三个累计周期的重复 2023 披露必须一致，否则源核验立即失败，不静默选取或平均。Q2–Q4 由累计差分恢复，±1,000 MWh 只是显示末位的保守界，存在共享端点。36 条件/9 年度的计算一致性不构成小时物理验证；未执行全新机器完整论文复现。

### 阶段 20：同信息价格/事件框架及净收益采购

新增 fair_mechanisms.py，将预测规划与实现成本评估分离，使用已存在的分数任务 LP。sequential_tasks.py 新增可选的时段电量上界和参考目标费用上界；未使用新选项时旧可行域与目标保持不变。两份旧验证脚本新增 `--output-dir`，输入仍固定读取原 `outputs/research/tables/dvfs_measured_and_derived.csv`，不能随输出路径切换输入。

```bash
work/figure-env/bin/python work/research/analysis/validate_fair_mechanisms.py
work/figure-env/bin/python work/research/analysis/validate_sequential_tasks.py --output-dir outputs/research/revision/mechanism_fairness/regression/sequential
work/figure-env/bin/python work/research/analysis/validate_response_cost.py --output-dir outputs/research/revision/mechanism_fairness/regression/response
```

新检查使用固定种子 20260923、60 个小规模穷举分配问题及手算实例，结果在 `revision/mechanism_fairness/`。旧两组 CSV（256/360 案）的原哈希与本轮哈希见 `regression/comparison_to_archived.json`，本轮完全相同；原结果未覆盖。源码版本由 validation.json 绑定，旧研究结果须按各自已冻结提交和来源复现，不把更新后的源码哈希冒充旧快照。

框架只对显式有限承诺集合优化，企业同费用响应使用显式容差的上下界，默认采购值相等判断容差为 1e−7 费用单位并写入计划。最低参与支付只是已知成本下、针对给定响应的核算下界，不是策略性支付规则。所有结果均为数学核验，不能视为现实预测质量、市场均衡、真实硬件或省级容量/价格收益。

### 阶段 21：固定响应电网联算与非线性边界反例

运行前设计提交为 `4a32998`。新增 `mechanism_grid.py` 审核逐任务分配与功率，然后输入既有电网模型；不修改原电网、启停或阶段 20 规划模型。

```bash
work/figure-env/bin/python work/research/analysis/validate_mechanism_grid.py
work/figure-env/bin/python work/research/analysis/validate_thermal_commitment.py --output-dir outputs/research/revision/mechanism_grid/regression/commitment
work/figure-env/bin/python work/research/analysis/validate_coupled_grid_compute.py --output-dir outputs/research/revision/mechanism_grid/regression/grid
```

新核验独立重建节点收支、线路损耗、发电与启停费用、服务成本和转移支付。`mechanism_grid/examples.json` 保留冻结的原选择、21 个响应取点和独立连续启动成本公式；连续最坏值由必要性/可行构造证明，不以有限采样冒充全局最优。20 项新检查和 75/118 项既有模型检查通过。

`input_snapshot.json` 和验证脚本包含人为设定的数学输入；不是实测机组或省级场景。完全预知的条件性重调度、期末义务、不可行/未知状态均明确报告。线性预测端点不得用于宣称非线性电网最坏响应边界。一般网格/启停下的保守采购与实际预测实验仍未完成。代码、证据和设计哈希见 `mechanism_grid/evidence_manifest.json`。

### 阶段 22：市场来源与历史版本准入

```bash
/Users/apple/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 work/research/analysis/audit_market_information_sources.py
work/figure-env/bin/python work/research/analysis/validate_forecast_vintages.py
```

第一项读取排除目录 `work/research/sources/market_information_20260923/` 中的两份原始 DOC、textutil 提取文本、带中文字体的本地 PDF 渲染及江苏通知 HTML；不访问网络。来源 URL、取得时间、原件哈希及失败记录见 `revision/market_information/source_attempts.json` 和 `source_audit.json`。两份官方 DOC 均须匹配 `6aaf7a70f9a2c3b2f9b9f1f9f5c7babcfa5689ed9aa447c990f46720e3c87d82`；若重取不同版本，不得静默覆盖为同一证据。浏览/版本旁证另记于 `additional_access_observations.json`。

来源重建步骤：从国家能源局及中国政府网列明的两个附件 URL 分别取得 `national_disclosure_nea.doc`、`national_disclosure.doc`；从江苏通知 URL 取得 `jiangsu_disclosure_202606.html`。原取得/失败日志为审计记录，应从仓库存档恢复而不是伪造新的取得日期。macOS 运行 `textutil -convert txt .../national_disclosure.doc -output .../national_disclosure.txt`。复制 `revision/market_information/render_fonts.conf` 到源目录 `render/fonts.conf`，以 `FONTCONFIG_FILE` 指向该文件，用捆绑 LibreOffice `--headless --convert-to pdf --outdir .../render/cjk .../national_disclosure_nea.doc` 渲染。首次默认字体配置缺失中文字形已记录，不能使用那版输出。原文未改，渲染仅用于来源审读；跨环境分页可能改变，需重新查看相关条款/附表页。

第二项仅使用人工合成的 96 点曲线，17 项检查不依赖真实市场数据。真实 `approved_vintages.json` 当前为空。版本选择器只是外部来源审核之后的一致性检查，不自动证明时间戳真实性、提取正确性或预测性能；尚未与论文主实验连通。不得将合成样例当作准入数据，也不得把市场“公开信息”直接等同于匿名可取得数据。全新机器完整论文复现仍未完成。

### 阶段 23：2030 输入、油气技术和需求边界

```bash
work/figure-env/bin/python work/research/analysis/audit_2030_input_consistency.py
```

读取既有 GEM July 2025 原始 China 工作簿、准备表、冻结三省容量表，以及 PyPSA-China 归档需求/成本/存量表；只写 `outputs/research/revision/input_consistency/`，不导入或运行旧求解入口。完整输入路径与 SHA256 见该目录 `source_hashes.json`。源文件恢复沿用本仓库 GEM / Zenodo 归档取得流程；这些未跟踪的原始输入必须先取得且哈希一致，不能仅凭此命令声称全新机器已可复现。

脚本以独立 OOXML 解析核对选入的 109 台油气机组、每台 13 字段，并复原 18 组旧机组数量和容量。类别为 97 台联合循环、12 台工业副产气蒸汽轮机；逐机组候选 CSV 保留 CHP/用途/燃料和未准入状态。成本率由同一归档表使用 Decimal 计算，是情景参数比较，不是中国机组测量。其余账目保留未知投运/退役、统计年代和需求群体缺口，不自动补齐，也不改写原机组或成本文件。

需求群体和跨省边界的修订规范见 `input_boundary_methods_draft.md`；目前为待实证落实的方法要求，未宣称已接入重算。阶段报告说明全部能力边界。不得把这项来源审计当作 2030 物理验证、修正后省级数值或完整 Nature Energy 质量认证。

### 阶段 24：AI 群体需求账目和完整轨迹接入口

```bash
work/figure-env/bin/python work/research/analysis/validate_demand_cohort.py
```

只写 `outputs/research/revision/demand_cohort/`；不运行旧省级脚本。读取阶段 07 冻结的 Earth Dolly 6h 江苏配对案例及其全部输入/证书，所需源数据沿用阶段 07–09 的恢复路径。设计 `DESIGN.md` 在 d3af59d 冻结。四次两小时容量求解与解析值比较；四条既有真实任务轨迹在假定功率和人为 3 MW 背景下作 192h 条件联算。25 项检查通过；不是实际省级供电收益、测量功率或新服务质量实验。

`synthetic_counterexample_ledgers.json` 明确为人工反例；`verified_trace_synthetic_background_ledger.json` 含完整普通背景/强制群体/总需求、时钟、观察期指标、认证来源和功率假设。`NO_COHORT` 在真实轨迹接入口表示整个复制集群被移除，包括未参与优化作业与空闲。一般入口不认证调用者声称的群体包含关系；它只强制该关系在账目中一致实现。内容哈希用于一致性检查，不替代来源核实。没有生成新的论文省级主结果。

### 阶段 25：负荷范围、旧敏感性配对与江苏展望

```bash
work/figure-env/bin/python work/research/analysis/audit_load_scope_and_peak_sensitivity.py
```

只写 `outputs/research/revision/load_scope/`。读取 `work/research/sources/load_scope_20260923/` 原始官方 HTML、2020 年锚定数组、归档年度增长和 8 对旧峰值情景 JSON；不导入/运行旧求解入口。该目录 `source_access_log.json` 列出 URL、获取时间、哈希，原取得日志在源目录的 `download_log.json`、`download_supplement.json`。新机器恢复原始页面时须比对 `source_hashes.json`，网页版本不同需记录新证据，不能伪造原取得时间。

16 项检查包括 14 项日期/字段双读取、三省年度增长独立 Decimal 复算、8 对旧情景的 AI 满载功率及刚性电量缩放关系。`qualified_peak_observations.csv` 的 5 条记录均未获准作为全社会小时峰值拟合目标；`peak_sensitivity_scale_audit.csv` 显示旧敏感性同时改变群体电力规模。`jiangsu_2030_outlook_check.json` 比较的是 AI 另加之前的旧背景与 2025 包含既有 AI 的全社会年度量，不应称为总需求误差。没有生成新的小时负荷或省级收益。旧峰荷合理性 CSV 仅作历史存档，解释已由阶段 25 更新。

### 阶段 26：固定群体与形状独立控制

```bash
work/figure-env/bin/python work/research/analysis/validate_fixed_cohort_factorial.py
work/figure-env/bin/python work/research/analysis/validate_demand_cohort.py
```

设计先于结果冻结于 ddc24b8。第一条只写 `revision/fixed_cohort_factorial/`，读取阶段 07–09 的三个 Earth Dolly 6h 地区配对证书/原始输入，以及排除目录中的 `load_2020_annual_anchored_hourly_shape_UNVALIDATED.npz`（SHA256 为 86bc5a2ad0c1028cfd9420431e4d75283d2842be958f1c4d3bc092cbc85908f6）。恢复要求沿用对应阶段，不可用新形状文件静默替换。时钟完全匹配且保留 192h；输出 18 个账目哈希、90 行需求指标及全部政策/形状差分。账目不逐份冗余保存，可通过入口复建后核对 `factor_ledger_manifest.json`。

67 项新增检查、72 次政策解析求解及 1 次容量不足拒绝求解通过，第二条 25 项回归通过。1/1,000 个同步复制、0.5 kW/GPU、0.41 idle 和人工发电成本均是假设；背景未验证，群体排除关系未认证。该诊断不是 2030 省级重算、全年容量收益或观测验证。代码/产物/既有回归哈希记录在 evidence_manifest.json；全新机器完整输入重建尚未实测。

### 阶段 27：新克隆、隔离环境及来源恢复

完整命令、版本和失败处理见 `revision/clean_reconstruction/RUNBOOK.md`，核心入口为 `work/research/analysis/restore_certified_inputs.py`，固定依赖在 `work/research/requirements-reconstruction.txt`。恢复范围为认证功率/阶段 24–26 所需链条，不能扩称全部论文。

2026-09-23 实测从 GitHub 网络克隆 3ffe061，使用无系统 site packages 的新 Python 3.14.6 环境安装指定依赖。Helios 固定提交压缩包与八个 CSV、江苏 PDF、贵州 HTML、负荷 HDF5 成员和重新计算的 NPZ 均与预期哈希一致。初次重建因数组 F/C 顺序引入约 4.22e-10 MW 差异而失败；新副本从远端拉取 a8c2003，显式保持原 C 顺序后匹配 NPZ 原哈希。没有修改预期哈希或复制原 prepared。

最终 13/14 项准入，唯一缺失为原甘肃 HTML。两个目前可访问的文章入口均返回不同字节，按原哈希拒绝，阶段 24/26 数值复算未执行。新环境的 75+118+74 项数学检查通过，仅证明对应模型可运行性。全部请求/失败、初始副本状态、环境、数组比较和最终准入见同目录 JSON；第二机器/操作系统及整篇论文重建仍未验证。

### 阶段 28：明确来源版本与限定链条独立复算

设计先于复算冻结于 ff23671。对甘肃原/新 HTML 使用正则字节跨度和独立 HTMLParser 边界审读：除一个路由/域名脚本外的 20,364 字节一致，192 个价形值不变。原清单和认证文件不修改，新版另存，默认仍严格验证原件，仅 `--reviewed-tariff-version` 开启这一具体审读版本，输出目录必须全新/为空。命令见上述阶段 28 操作说明。

新副本从 GitHub 拉取 9b9ce89，重新下载新版页面，使用阶段 27 隔离环境执行 25+67 项既有检查和 72 次因素实验政策求解。四个数值 CSV 逐字节一致，两个验证 JSON 除明确的准入模式外一致，完整 192h 账目及 18 条因素记录仅增加已声明来源证明。原源路径回归另证 9 个产物逐字节不变；新版本准入变异检查 11 项、来源核对 6 项、输出保护 2 项通过。逐记录比较器的 72 个断言不是独立研究样本。

`compare_reviewed_source_replay.py --checkout /absolute/path/to/checkout` 在主研究树比较并保存独立副本产物，来源审读脚本仍需旧本地原件作参照，不能称旧原件已从网络恢复。所有记录位于 `revision/reviewed_tariff_version/`；13 原字节输入 + 1 显式审读版本的限定复算，不代表重新优化 108 案、第二机器/操作系统或完整省级实证。

### 阶段 29：工业自备发电的来源与电网边界

```bash
python work/research/analysis/audit_captive_generation_boundary.py
```

环境需要 pypdf/pdfplumber，实测版本在 `revision/captive_boundary/evidence_manifest.json`。先按同目录 RUNBOOK 和 source_access_log 恢复三份原始机构文件到排除目录，核对固定哈希；动态页面不同则单独审读，不能改原预期直接放行。源码只读取阶段 23 台账和本阶段来源，不导入旧调度入口。48 项来源/算术/覆盖核对通过，完整相关 PDF 页已渲染审读；输出 12 台、1,125 MW 全量台账、两条候选项目匹配与预期电量分界。外送和可靠调节容量留空，未执行省级重算、未实现新的求解器准入。第二机器复现未验证。

### 阶段 30：机组投产时间与参数证据分级

```bash
python work/research/analysis/audit_captive_commissioning.py
```

恢复 `revision/captive_commissioning/source_access_log.json` 所列四个成功下载文件；年报 PDF、扫描评估 PDF、供应商 HTML 外壳和其直接引用的正文 JS。逐一比对固定哈希。供应商正文只按字符串解码，未执行远端脚本；扫描件须按 RUNBOOK 重新视觉审读人工转录。失败的验收报告记录不作输入。30 项读取/算术/台账检查通过，保留全部 12 条机组并叠加历史时间线；0 次调度、0 套新增运行参数准入。年报是双页排版，PDF 页 18/67 对应目标印刷页 24/122。没有第二机器复现声明。

### 阶段 31：共享煤气与厂区电网接口

```bash
python work/research/analysis/validate_industrial_coupling.py --output-dir work/tmp/industrial-stage31-replay
python work/research/analysis/compare_industrial_regression.py --scratch work/tmp/industrial-stage31-regression --output work/tmp/industrial-stage31-comparison.json
```

只使用明确标记的合成数据；47 项检查、19 次求解（14 可行/5 证明不可行）。第二条从固定历史提交提取旧源、分别运行三个检查套件（各 267 项），要求全新 scratch，避免覆盖；仅排除指定源哈希字段比较。已实际验证此完整入口。解释器需 NumPy/SciPy，不使用 `-O`。详细边界及现场参数准入见 `outputs/research/revision/industrial_coupling/RUNBOOK.md`；没有实测参数、省级新结果或第二机器复现声明。

### 阶段 32：工业年度电量与统计范围

```bash
python work/research/analysis/audit_captive_operating_scope.py --output-dir work/tmp/captive-operating-replay
```

恢复 captive_operating/source_access_log.json 的成功原件并核对哈希。需要 pypdf/pdfplumber；输出 24 个年度能源数值、38 项来源/读取/版本/算术检查和准入限制。PDF 双页排版及两个版本页码映射见 RUNBOOK；鉴证页为人工视觉读取。没有现场小时数据或新省级求解。

### 阶段 33：燃气技术、用途和存量/新增分离

```bash
python work/research/analysis/build_thermal_technology_staging.py --output-dir work/tmp/thermal-stage33-replay
python work/research/analysis/audit_thermal_unit_labels.py --output-dir work/tmp/thermal-stage33-replay
python work/research/analysis/validate_thermal_technology_staging.py --input-dir work/tmp/thermal-stage33-replay
```

均为标准库入口；恢复阶段 23 的 GEM 原工作簿和归档成本 CSV，并保留原哈希。输出 109 台完整待核实清单、三个权限未知的 OCGT 选项、19 个日期格式名称原值及 36 项检查。无旧省级程序导入/执行、无新实证准入或调度重算。详见 `revision/thermal_technology/RUNBOOK.md`。
