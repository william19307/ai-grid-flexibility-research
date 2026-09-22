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
