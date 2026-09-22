# 复现说明

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

### 阶段 07（运行中）：固定服务的四组政策与确定性归因界

冻结清单提交为 `091ea10`；108 个四格实验还在运行时，不得再次启动 `run_gang_policy_revision.py run`。先根据 `outputs/research/revision/policy/RUN_STATE_NOTE.json` 的历史句柄重新核验当前进程；观察超时不是终止证据。原构造结束且 `complete.json` 覆盖全部案例后，运行以下独立核验与汇总入口：

```bash
work/figure-env/bin/python work/research/analysis/verify_gang_policy_revision.py
work/figure-env/bin/python work/research/analysis/summarize_gang_policy_revision.py
```

已完成的方法检查入口为 `validate_gang_policy.py`（241 项）和 `validate_policy_attribution.py`（201 项）。可行策略份额与全局最优份额界不能混称，详见 `policy_attribution_methods_draft.md`。新增整机功率候选核查入口为 `audit_tokenpowerbench_source.py`，固定上游提交且只读取文本/结果，不执行下载代码；其结果尚不能作为整机校准。
