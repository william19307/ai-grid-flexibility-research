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
