# Supplementary Information

**Efficient modes, not load shifting, deliver most of the grid value of flexible AI computing**

William Wei^1,2,\*^, Lanlan Liu (刘岚岚)^3^ — ^1^ School of Computer Science, Faculty of Engineering and Physical Sciences, University of Leeds, Leeds, UK; ^2^ Spatial Computing (Fujian) Technology Co., Ltd., Fuzhou, China; ^3^ School of Public Administration, Fujian Normal University, Fuzhou, China; \* qkfp0742@leeds.ac.uk

Supplementary Information v1.4, 17 September 2026. Base case: idle power 41% of nameplate; 25% is a sensitivity. Metric: total incremental system cost for the same computing work (EUR per representative week, expected over four weeks); reductions are relative to rigid full-speed operation (S0); shifting value is (cost S0e − cost S2)/cost S2. Full-precision, machine-readable versions of every table are provided as Supplementary Data 1 (spreadsheet, one sheet per table) and in the code repository under `outputs/research/tables/`.

**Column key (Tables S7–S12).** `cost_X`: incremental system cost under scenario X, i.e. total expected system cost with the AI pool minus that without it (EUR per representative week). `red_A_B_pct` = (1 − cost B / cost A) × 100. `gap_A_B_pct` = (cost A / cost B − 1) × 100. `share_S1` = (cost S0 − cost S1)/(cost S0 − cost S2), the share of total coordination value captured by the tariff-driven firm. `timing_share_X` = (cost S0e − cost X)/(cost S0e − cost S2), the share of shifting value realised by scenario X (negative when shifting raises cost above no-shifting operation). `ai_mwh_X`: AI pool energy under scenario X (MWh per representative week). `new_ocgt_X`, `new_batt_X`: new open-cycle gas-turbine and battery capacity (MW) relative to the reference without AI. `curtail_NOAI`: curtailment share in the reference without AI. `idle`: idle power as a fraction of nameplate. `ai_share`: AI pool as a share of the 2030 provincial peak; `slack_mult`: multiplier on observed queueing wait in the deadline (1 or 3); `export`: interprovincial exchange allowed. In Table S12, `system_cost_X` is the total system cost and savings are in EUR per representative week.

## S1. Data registry
| id   | dataset                                                                                            | url                                                                                     | evidence_type                                                      | licence                                                                      | status                                                                             | limits                                                                                                                                                                                                      |
|:-----|:---------------------------------------------------------------------------------------------------|:----------------------------------------------------------------------------------------|:-------------------------------------------------------------------|:-----------------------------------------------------------------------------|:-----------------------------------------------------------------------------------|:------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| D01  | Emerald AI May 2025 experiment                                                                     | https://github.com/ai-emerald/emerald-ai-demo-may-2025                                  | published_experimental_data                                        | Apache-2.0 repository licence                                                | downloaded_reanalysed                                                              | GPU-only modes; timestamp/aggregate conflicts; no independent repeated runs or complete service logs                                                                                                        |
| D02  | China 2018 provincial hourly load                                                                  | https://doi.org/10.5281/zenodo.8322210                                                  | reconstructed_historical_load                                      | CC-BY-4.0                                                                    | checksums_verified_column_mapping_verified                                         | daily-extrema typical-profile reconstruction; not current metered load                                                                                                                                      |
| D03  | China interprovincial transmission                                                                 | https://doi.org/10.5281/zenodo.8322210                                                  | compiled_infrastructure                                            | CC-BY-4.0                                                                    | quarantined_pending_asset_checks                                                   | sheet classifications reversed vs appendix; 3 matrix/list edge conflicts; aliases and endpoints unresolved                                                                                                  |
| D04  | PyPSA-China model and assumptions                                                                  | https://github.com/PyPSA/PyPSA-China                                                    | code_and_derived_inputs                                            | MIT code; per-input licences need checking                                   | repository_downloaded_load_provenance_traced                                       | load shares historical origin with D02; not independent validation; default future load scaled shape                                                                                                        |
| D05  | Dunlap capacity-adequacy source model                                                              | https://github.com/ctdunlap32/data-center-flexibility-resource-adequacy                 | author_code_manuscript_processed_inputs                            | MIT code; upstream data licences separate                                    | method_inspected_not_reproduced                                                    | exogenous ELCC and partially unobserved assumptions; author manuscript is not Nature publication                                                                                                            |
| D06  | Azure LLM inference trace 2024                                                                     | https://github.com/Azure/AzurePublicDataset/blob/master/AzureLLMInferenceDataset2024.md | production_request_metadata                                        | CC-BY-4.0                                                                    | schema_license_release_sizes_inspected_not_downloaded                              | invocation and token lengths only; no deadlines or GPU power; code 692 MB, conversation 1135 MB                                                                                                             |
| A01  | Two-block diagnostic scenarios                                                                     | local analysis                                                                          | analyst_assumptions                                                | original analysis                                                            | implemented_verified                                                               | not production workloads or grid results                                                                                                                                                                    |
| A02  | Sequential-task diagnostic scenarios                                                               | local analysis                                                                          | analyst_assumptions                                                | original analysis                                                            | implemented_verified                                                               | uniform arrivals; assumed deadline and idle power; no grid or switching cost                                                                                                                                |
| D07  | BurstGPT release v2.0 part 1                                                                       | https://github.com/HPMLL/BurstGPT/releases/tag/v2.0                                     | production_request_metadata                                        | CC-BY-4.0                                                                    | download_digest_verified_schema_and_hourly_audit_complete                          | no deadlines, elapsed time, request IDs or power; retain repeated metadata and zero-output records                                                                                                          |
| D08  | PyPSA-China V3.0 selected archive members                                                          | https://doi.org/10.5281/zenodo.13987282                                                 | published_model_inputs                                             | CC-BY-4.0 record; verify upstream embedded sources before redistribution     | member_crc_size_verified_and_inputs_audited                                        | not a calibrated base year; source-model totals and official statistics differ; hydro leapday missing; reservoir subsystem separate                                                                         |
| D09  | 2020 national power reliability annual report                                                      | https://prpq.nea.gov.cn/uploads/file1/20211009/616107fe94a8e.pdf                        | official_aggregate_reliability_statistics                          | public official report; reuse facts with attribution                         | PDF_obtained_three_tables_extracted_with_sum_checks                                | not chronological outage telemetry; unplanned/forced/availability metrics differ; unit-year exposure definitions require checking                                                                           |
| D10  | DynamoLLM HPCA 2025 published experiment                                                           | https://jovans2.github.io/files/DynamoLLM_HPCA2025.pdf                                  | published_experimental_methods_and_aggregate_tables                | author-hosted paper; numeric facts attributed; no PDF redistribution planned | PDF_obtained_tables_and_methods_inspected                                          | raw power/performance profiling dataset not obtained; cannot treat example SLOs as BurstGPT observed deadlines                                                                                              |
| A03  | Fixed commitment operational cost scenarios                                                        | local analysis                                                                          | analyst_assumptions_with_measured_modes                            | original analysis                                                            | implemented_analytic_dual_and_convexity_checks_passed                              | assumed tariffs, arrivals, deadlines, idle power; no observed company costs or grid value                                                                                                                   |
| D11  | GEM Global Integrated Power Tracker July 2025 China subset                                         | https://doi.org/10.5281/zenodo.16810831                                                 | compiled_unit_phase_inventory                                      | CC-BY-4.0 confirmed About sheet                                              | download_checksum_verified_unit_ID_and_date_completeness_audited                   | tracking thresholds, unknown dates, conversions and historical retired coverage require reconciliation; not complete official historical fleet                                                              |
| D12  | Alibaba PAI GPU cluster trace 2020 (NSDI 22)                                                       | https://github.com/alibaba/clusterdata/tree/master/cluster-trace-gpu-v2020              | production_job_task_instance_metadata_and_instance_average_sensors | CC-BY-4.0 (repository LICENSE)                                               | downloaded_extracted_sha256_recorded_audit_complete                                | no deadlines, no power; plan_gpu is requested not used; wait = scheduling latency only; dates fake                                                                                                          |
| D13  | SenseTime Helios GPU cluster traces (SC 21)                                                        | https://github.com/S-Lab-System-Group/HeliosData                                        | production_slurm_job_metadata                                      | see LICENSE.txt in release (Apache-2.0 text)                                 | downloaded_sha256_verified_audit_complete                                          | no power or utilisation; queue is observed scheduling wait not a deadline; 39% of GPU-hours in CANCELLED jobs                                                                                               |
| D14  | Microsoft Philly DL training trace (ATC 19)                                                        | https://github.com/msr-fiddle/philly-traces                                             | production_job_log_and_per_minute_gpu_utilisation                  | CC-BY-4.0 (repository LICENSE)                                               | downloaded_via_lfs_sha256_recorded_job_log_and_streamed_utilisation_audit_complete | 2017 hardware; per-GPU per-minute utilisation with variable columns (DST duplicate rows truncated to first 8 values); 68% of GPU-hours in Failed/Killed jobs; no deadlines                                  |
| A04  | Region selection matrix                                                                            | local analysis                                                                          | screening_table_from_archive_and_official_inputs                   | original analysis                                                            | built                                                                              | archive capacities unverified; Gansu large hydro absent from archive; Inner Mongolia grid split                                                                                                             |
| A05  | Regional S0/S0b/S1/S2 smoke grid                                                                   | local analysis                                                                          | uncalibrated_regional_smoke_test                                   | original analysis                                                            | pipeline_verified_results_not_empirical                                            | unvalidated hourly load shape; archive capacities; placeholder tariff and external market; no unit commitment or coal minimum load                                                                          |
| D15  | Jiangsu grid 2020-2022 T&D and retail tariff notice (苏发改价格发〔2020〕1183号) incl. industrial TOU table | https://www.njqxq.gov.cn/qxqrmzf/qxqfzhggj/202011/P020201111396651530459.pdf            | official_tariff_document_scanned_pdf                               | public government document                                                   | pdf_saved_pages_read_values_transcribed                                            | scanned images, transcribed by reading; 2021 effective date used for 2020 base year; market users pay market price + T&D                                                                                    |
| D16  | Gansu 2020-12 notice on retail tariff adjustment and TOU optimisation (policy interpretation page) | http://www.gansu.gov.cn/art/2020/12/3/art_10359_474921.html                             | official_policy_interpretation_web_page                            | public government page                                                       | mirror_page_fetched_values_transcribed                                             | original gansu.gov.cn page returned HTTP 412 to fetch; mirror gsei.com.cn used; ratios not absolute prices                                                                                                  |
| D17  | Guizhou TOU mechanism notice 黔发改价格〔2023〕481号                                                       | https://fgw.guizhou.gov.cn/zwgk/zcwj/zcwj/202306/t20230628_80566840.html                | official_notice_web_page                                           | public government page                                                       | page_fetched_values_transcribed                                                    | 2023 rules used as nearest official structure; no 2020 Guizhou TOU document obtained; year mismatch flagged                                                                                                 |
| A06  | GEM-based unit-level 2020/2030 fleets for Gansu, Jiangsu, Guizhou                                  | local analysis of D11                                                                   | derived_unit_inventory                                             | CC-BY-4.0 upstream                                                           | built_compared_with_archive                                                        | GEM size thresholds (lower bound vs official); unknown start years excluded; pre-construction listed separately                                                                                             |
| A07  | Provincial 2030 S0/S1/S2/S3 scenario runs                                                          | local analysis                                                                          | public_data_scenario_with_documented_assumptions                   | original analysis                                                            | pipeline_run_results_labelled_scenario_not_calibrated                              | hourly load shape unvalidated (2018-derived); external-market proxy; committed-capacity must-run heuristic; RE existing = 2020 archive; no new coal; S3 event rule = >20% above weekly median marginal cost |
| D18  | MLPerf Training v4.0 AC power logs (Supermicro 8xH100, llama2_70b_lora)                            | https://github.com/mlcommons/training_results_v4.0/tree/main/smc-ac-power               | published_benchmark_power_measurements                             | MLCommons results repository (Apache-2.0)                                    | downloaded_parsed_idle_active_extracted_three_benchmarks                           | node-level incl. non-GPU components; benchmark workloads; one run per benchmark                                                                                                                             |
| D19  | Open-Meteo historical weather API (ERA5-based) hourly 2015-2024 at GEM wind/solar sites            | https://archive-api.open-meteo.com/v1/archive                                           | reanalysis_weather_free_api                                        | CC-BY 4.0 (Open-Meteo; ERA5 Copernicus)                                      | pulled_cached_converted_to_capacity_factors                                        | simple power-curve and GHI conversions; level scaled to archive 2020 mean; not measured generation                                                                                                          |

## S2. Model verification records
Joint planning–operation LP: 118 checks in total, of which 100 are independent oracle cases (60 screening-curve capacity cases, 40 enumerated task-assignment cases); reservoir-cascade extension: 74 checks, of which 60 are independent dynamic-programming cases; task model: 120 exhaustive assignment oracles and 256 diagnostic cases; commitment-cost model: 72 frontiers, 360 points, dual and finite-difference checks.

## S3. MLPerf Training v4.0 node power (8×H100 nodes)
| benchmark       |   nodes |   idle_kW |   active_kW |   max_kW |   idle_over_max |
|:----------------|--------:|----------:|------------:|---------:|----------------:|
| llama2_70b_lora |       8 |     2.647 |        6.25 |     6.42 |           0.412 |
| resnet          |       8 |      2.24 |       5.859 |    5.933 |           0.378 |
| ssd             |       8 |     2.235 |       6.277 |    6.372 |           0.351 |

## S4. GEM-based 2020 and 2030 fleets, three provinces (MW)
| province   | type       |   mw_2020 |   units_2020 |   mw_2030_operating_plus_construction |   units_2030 |   mw_2030_preconstruction_announced |
|:-----------|:-----------|----------:|-------------:|--------------------------------------:|-------------:|------------------------------------:|
| Gansu      | coal       |     21630 |           61 |                                 33650 |           75 |                                2000 |
| Gansu      | oil/gas    |       180 |            1 |                                   180 |            1 |                                   0 |
| Gansu      | nuclear    |         0 |            0 |                                     0 |            0 |                                   0 |
| Gansu      | hydropower |      5514 |           34 |                                  8094 |           36 |                                   0 |
| Gansu      | wind       |   12798.4 |          111 |                               28451.6 |          215 |                                 200 |
| Gansu      | solar      |    8632.1 |          286 |                               24919.9 |          407 |                                   0 |
| Jiangsu    | coal       |     75804 |          199 |                                 92481 |          221 |                                2700 |
| Jiangsu    | oil/gas    |     17542 |           73 |                                 24779 |          108 |                                   0 |
| Jiangsu    | nuclear    |      5490 |            5 |                                  9138 |            8 |                                   0 |
| Jiangsu    | hydropower |      2600 |            3 |                                  3950 |            5 |                                1200 |
| Jiangsu    | wind       |   13261.2 |          136 |                               21955.2 |          179 |                                   0 |
| Jiangsu    | solar      |    9303.6 |         1283 |                                 11198 |         1301 |                                   0 |
| Guizhou    | coal       |     31860 |           75 |                                 41890 |           95 |                                2210 |
| Guizhou    | oil/gas    |         0 |            0 |                                     0 |            0 |                                   0 |
| Guizhou    | nuclear    |         0 |            0 |                                     0 |            0 |                                   0 |
| Guizhou    | hydropower |     16735 |           39 |                                 18235 |           40 |                                   0 |
| Guizhou    | wind       |    4807.5 |           95 |                                6626.1 |          123 |                                 100 |
| Guizhou    | solar      |      9095 |          128 |                               21149.5 |          236 |                                   0 |

## S5. Peak-load plausibility check
| province   |   anchored_2020_peak_MW | official_reference                                       | reference_value_MW   | status                                                                                  |
|:-----------|------------------------:|:---------------------------------------------------------|:---------------------|:----------------------------------------------------------------------------------------|
| Jiangsu    |                 109,828 | 2020 年夏季与冬季最高调度负荷均突破 1 亿千瓦（国网江苏，2021-01 报道）              | >100000              | consistent in magnitude; exact value not obtained                                       |
| Gansu      |                   19679 | 2021 年全网最大用电负荷 1766 万千瓦（北极星电力网转载）                        | 17660                | anchored 2020 peak exceeds 2021 official peak by ~11%                                   |
| Guizhou    |                   31255 | 贵州电网统调负荷 2026-01 首次突破 3000 万千瓦（央广网）；2025 年底最高 2955.3 万千瓦 | <30000 in 2020       | anchored 2020 peak exceeds the 2026 record; 2020 peak must have been well below 31.3 GW |

## S6. Multi-year renewable profiles: site coverage and agreement with archive 2020 profiles
| province_tech   |   level_scale |   corr_with_archive_2020 |   top_site_capacity_share |   n_operating_sites |
|:----------------|--------------:|-------------------------:|--------------------------:|--------------------:|
| Gansu / solar   |         0.955 |                    0.936 |                     0.254 |                 442 |
| Gansu / wind    |          1.16 |                     0.66 |                     0.303 |                 217 |
| Guizhou / solar |         0.711 |                    0.956 |                     0.227 |                 227 |
| Guizhou / wind  |         2.391 |                    0.954 |                     0.266 |                 125 |
| Jiangsu / solar |         0.973 |                    0.967 |                     0.274 |                1704 |
| Jiangsu / wind  |         0.901 |                    0.805 |                     0.305 |                 187 |

## S7. 2030 scenario results, islanded (export = False) and fixed-price exchange proxy (export = True), idle 41%

### S7a. Incremental system cost by scenario (EUR per representative week)
| province   | export   |   ai_share |   slack_mult |     cost_S0 |    cost_S0e |     cost_S1 |     cost_S3 |   cost_S1rt |     cost_S2 |
|:-----------|:---------|-----------:|-------------:|------------:|------------:|------------:|------------:|------------:|------------:|
| Gansu      | False    |       0.05 |            1 |   4,716,346 |   4,081,179 |   4,101,238 |   4,101,238 |   4,077,055 |   4,075,821 |
| Gansu      | False    |       0.05 |            3 |   4,716,346 |   3,757,311 |   3,781,838 |   3,781,838 |   3,753,656 |   3,753,117 |
| Gansu      | False    |        0.1 |            1 |   9,391,522 |   8,113,527 |   8,157,286 |   8,157,286 |   8,110,767 |   8,106,916 |
| Gansu      | False    |        0.1 |            3 |   9,391,522 |   7,461,038 |   7,510,092 |   7,510,092 |   7,459,868 |   7,453,211 |
| Gansu      | False    |        0.2 |            1 |  18,494,780 |  15,929,656 |  16,017,524 |  16,017,524 |  15,924,103 |  15,917,783 |
| Gansu      | False    |        0.2 |            3 |  18,494,780 |  14,606,454 |  14,705,016 |  14,705,016 |  14,604,649 |  14,592,950 |
| Gansu      | True     |       0.05 |            1 |   5,093,788 |   4,419,542 |   4,439,700 |   4,439,700 |   4,416,253 |   4,416,168 |
| Gansu      | True     |       0.05 |            3 |   5,093,788 |   4,070,916 |   4,095,626 |   4,095,626 |   4,068,188 |   4,068,156 |
| Gansu      | True     |        0.1 |            1 |  10,184,505 |   8,834,452 |   8,875,171 |   8,875,171 |   8,828,409 |   8,828,313 |
| Gansu      | True     |        0.1 |            3 |  10,184,505 |   8,137,469 |   8,185,936 |   8,185,936 |   8,131,902 |   8,131,208 |
| Gansu      | True     |        0.2 |            1 |  20,352,157 |  17,651,024 |  17,731,532 |  17,731,532 |  17,638,367 |  17,638,290 |
| Gansu      | True     |        0.2 |            3 |  20,352,157 |  16,258,282 |  16,352,857 |  16,352,857 |  16,244,905 |  16,244,482 |
| Guizhou    | False    |       0.05 |            1 |   6,406,987 |   5,585,695 |   5,557,422 |   5,578,925 |   5,517,965 |   5,503,164 |
| Guizhou    | False    |       0.05 |            3 |   6,406,987 |   5,131,669 |   5,136,342 |   5,155,081 |   5,066,188 |   5,056,744 |
| Guizhou    | False    |        0.1 |            1 |  12,737,351 |  10,999,516 |  10,959,127 |  10,962,125 |  10,882,236 |  10,850,800 |
| Guizhou    | False    |        0.1 |            3 |  12,737,351 |  10,074,534 |  10,089,706 |  10,118,625 |   9,972,867 |   9,937,528 |
| Guizhou    | False    |        0.2 |            1 |  25,007,943 |  21,243,656 |  21,221,539 |  21,221,539 |  21,120,171 |  20,999,481 |
| Guizhou    | False    |        0.2 |            3 |  25,007,943 |  19,339,271 |  19,366,970 |  19,582,761 |  19,233,822 |  19,087,095 |
| Guizhou    | True     |       0.05 |            1 |   8,264,055 |   7,163,267 |   7,198,604 |   7,198,604 |   7,159,400 |   7,159,202 |
| Guizhou    | True     |       0.05 |            3 |   8,264,055 |   6,598,262 |   6,625,980 |   6,625,980 |   6,594,357 |   6,594,258 |
| Guizhou    | True     |        0.1 |            1 |  16,384,621 |  14,191,353 |  14,265,554 |  14,265,554 |  14,186,077 |  14,185,069 |
| Guizhou    | True     |        0.1 |            3 |  16,384,621 |  13,065,919 |  13,125,223 |  13,125,223 |  13,061,256 |  13,060,137 |
| Guizhou    | True     |        0.2 |            1 |  32,220,264 |  27,863,288 |  28,028,551 |  28,028,551 |  27,861,604 |  27,858,980 |
| Guizhou    | True     |        0.2 |            3 |  32,220,264 |  25,621,877 |  25,755,850 |  25,755,850 |  25,621,578 |  25,619,232 |
| Jiangsu    | False    |       0.05 |            1 |  28,905,044 |  24,712,571 |  24,779,466 |  24,772,013 |  24,610,641 |  24,597,050 |
| Jiangsu    | False    |       0.05 |            3 |  28,905,044 |  22,667,442 |  22,680,700 |  22,680,700 |  22,517,787 |  22,504,657 |
| Jiangsu    | False    |        0.1 |            1 |  60,564,006 |  51,315,483 |  51,448,812 |  51,744,240 |  51,168,598 |  51,100,438 |
| Jiangsu    | False    |        0.1 |            3 |  60,564,006 |  46,798,303 |  46,744,502 |  46,734,867 |  46,464,921 |  46,404,857 |
| Jiangsu    | False    |        0.2 |            1 | 140,005,403 | 116,358,518 | 118,347,943 | 118,850,619 | 113,102,184 | 111,481,799 |
| Jiangsu    | False    |        0.2 |            3 | 140,005,403 | 101,190,396 | 101,560,918 | 101,615,317 | 102,603,733 | 100,048,295 |
| Jiangsu    | True     |       0.05 |            1 |  26,801,003 |  23,195,195 |  23,319,371 |  23,319,371 |  23,183,959 |  23,181,802 |
| Jiangsu    | True     |       0.05 |            3 |  26,801,003 |  21,354,049 |  21,452,284 |  21,452,284 |  21,337,164 |  21,335,366 |
| Jiangsu    | True     |        0.1 |            1 |  54,086,719 |  46,771,340 |  47,027,907 |  47,027,907 |  46,752,940 |  46,745,368 |
| Jiangsu    | True     |        0.1 |            3 |  54,086,719 |  43,018,531 |  43,217,892 |  43,217,892 |  42,981,138 |  42,973,250 |
| Jiangsu    | True     |        0.2 |            1 | 109,499,873 |  94,653,841 |  95,205,981 |  95,205,981 |  94,633,015 |  94,623,243 |
| Jiangsu    | True     |        0.2 |            3 | 109,499,873 |  87,007,025 |  87,445,255 |  87,445,255 |  86,982,402 |  86,969,565 |

### S7b. Reductions, gaps and realised shares
| province   | export   |   ai_share |   slack_mult |   red_S0_S2_pct |   red_S0_S0e_pct |   gap_S0e_S2_pct |   share_S1 |   timing_share_S1 |   timing_share_S1rt |   gap_S1rt_S2_pct |
|:-----------|:---------|-----------:|-------------:|----------------:|-----------------:|-----------------:|-----------:|------------------:|--------------------:|------------------:|
| Gansu      | False    |       0.05 |            1 |          13.581 |           13.467 |            0.131 |       0.96 |            -3.744 |                0.77 |              0.03 |
| Gansu      | False    |       0.05 |            3 |          20.423 |           20.334 |            0.112 |       0.97 |            -5.848 |               0.872 |             0.014 |
| Gansu      | False    |        0.1 |            1 |          13.678 |           13.608 |            0.082 |      0.961 |            -6.619 |               0.417 |             0.048 |
| Gansu      | False    |        0.1 |            3 |          20.639 |           20.556 |            0.105 |      0.971 |            -6.268 |                0.15 |             0.089 |
| Gansu      | False    |        0.2 |            1 |          13.934 |           13.869 |            0.075 |      0.961 |              -7.4 |               0.468 |              0.04 |
| Gansu      | False    |        0.2 |            3 |          21.097 |           21.024 |            0.093 |      0.971 |            -7.299 |               0.134 |              0.08 |
| Gansu      | True     |       0.05 |            1 |          13.303 |           13.237 |            0.076 |      0.965 |            -5.975 |               0.975 |             0.002 |
| Gansu      | True     |       0.05 |            3 |          20.135 |           20.081 |            0.068 |      0.973 |            -8.953 |               0.989 |             0.001 |
| Gansu      | True     |        0.1 |            1 |          13.316 |           13.256 |             0.07 |      0.965 |            -6.633 |               0.984 |             0.001 |
| Gansu      | True     |        0.1 |            3 |          20.161 |             20.1 |            0.077 |      0.973 |            -7.742 |               0.889 |             0.009 |
| Gansu      | True     |        0.2 |            1 |          13.335 |           13.272 |            0.072 |      0.966 |            -6.322 |               0.994 |                 0 |
| Gansu      | True     |        0.2 |            3 |          20.183 |           20.115 |            0.085 |      0.974 |            -6.853 |               0.969 |             0.003 |
| Guizhou    | False    |       0.05 |            1 |          14.107 |           12.819 |              1.5 |       0.94 |             0.343 |               0.821 |             0.269 |
| Guizhou    | False    |       0.05 |            3 |          21.075 |           19.905 |            1.482 |      0.941 |            -0.062 |               0.874 |             0.187 |
| Guizhou    | False    |        0.1 |            1 |          14.811 |           13.644 |            1.371 |      0.943 |             0.272 |               0.789 |              0.29 |
| Guizhou    | False    |        0.1 |            3 |          21.981 |           20.906 |            1.379 |      0.946 |            -0.111 |               0.742 |             0.356 |
| Guizhou    | False    |        0.2 |            1 |          16.029 |           15.052 |            1.163 |      0.945 |             0.091 |               0.506 |             0.575 |
| Guizhou    | False    |        0.2 |            3 |          23.676 |           22.667 |            1.321 |      0.953 |             -0.11 |               0.418 |             0.769 |
| Guizhou    | True     |       0.05 |            1 |          13.369 |            13.32 |            0.057 |      0.964 |            -8.692 |               0.951 |             0.003 |
| Guizhou    | True     |       0.05 |            3 |          20.206 |           20.157 |            0.061 |      0.981 |            -6.924 |               0.975 |             0.001 |
| Guizhou    | True     |        0.1 |            1 |          13.424 |           13.386 |            0.044 |      0.963 |           -11.809 |                0.84 |             0.007 |
| Guizhou    | True     |        0.1 |            3 |           20.29 |           20.255 |            0.044 |       0.98 |           -10.256 |               0.806 |             0.009 |
| Guizhou    | True     |        0.2 |            1 |          13.536 |           13.522 |            0.015 |      0.961 |           -38.367 |               0.391 |             0.009 |
| Guizhou    | True     |        0.2 |            3 |          20.487 |           20.479 |             0.01 |      0.979 |           -50.657 |               0.113 |             0.009 |
| Jiangsu    | False    |       0.05 |            1 |          14.904 |           14.504 |             0.47 |      0.958 |            -0.579 |               0.882 |             0.055 |
| Jiangsu    | False    |       0.05 |            3 |          22.143 |            21.58 |            0.723 |      0.972 |            -0.081 |               0.919 |             0.058 |
| Jiangsu    | False    |        0.1 |            1 |          15.626 |           15.271 |            0.421 |      0.963 |             -0.62 |               0.683 |             0.133 |
| Jiangsu    | False    |        0.1 |            3 |          23.379 |           22.729 |            0.848 |      0.976 |             0.137 |               0.847 |             0.129 |
| Jiangsu    | False    |        0.2 |            1 |          20.373 |            16.89 |            4.374 |      0.759 |            -0.408 |               0.668 |             1.453 |
| Jiangsu    | False    |        0.2 |            3 |           28.54 |           27.724 |            1.142 |      0.962 |            -0.324 |              -1.237 |             2.554 |
| Jiangsu    | True     |       0.05 |            1 |          13.504 |           13.454 |            0.058 |      0.962 |            -9.272 |               0.839 |             0.009 |
| Jiangsu    | True     |       0.05 |            3 |          20.393 |           20.324 |            0.088 |      0.979 |            -5.258 |               0.904 |             0.008 |
| Jiangsu    | True     |        0.1 |            1 |          13.573 |           13.525 |            0.056 |      0.962 |            -9.879 |               0.708 |             0.016 |
| Jiangsu    | True     |        0.1 |            3 |          20.548 |           20.464 |            0.105 |      0.978 |            -4.403 |               0.826 |             0.018 |
| Jiangsu    | True     |        0.2 |            1 |          13.586 |           13.558 |            0.032 |      0.961 |           -18.045 |               0.681 |              0.01 |
| Jiangsu    | True     |        0.2 |            3 |          20.576 |           20.541 |            0.043 |      0.979 |           -11.699 |               0.657 |             0.015 |

### S7c. AI energy and new capacity
| province   | export   |   ai_share |   slack_mult |   ai_mwh_S0 |   ai_mwh_S2 |   new_ocgt_S0 |   new_ocgt_S2 |   new_batt_S0 |
|:-----------|:---------|-----------:|-------------:|------------:|------------:|--------------:|--------------:|--------------:|
| Gansu      | False    |       0.05 |            1 |     172,282 |     149,992 |             0 |             0 |             0 |
| Gansu      | False    |       0.05 |            3 |     172,282 |     138,555 |             0 |             0 |             0 |
| Gansu      | False    |        0.1 |            1 |     344,564 |     299,590 |             0 |             0 |             0 |
| Gansu      | False    |        0.1 |            3 |     344,564 |     276,421 |             0 |             0 |             0 |
| Gansu      | False    |        0.2 |            1 |     689,127 |     598,274 |             0 |             0 |             0 |
| Gansu      | False    |        0.2 |            3 |     689,127 |     551,319 |             0 |             0 |             0 |
| Gansu      | True     |       0.05 |            1 |     172,282 |     149,564 |             0 |             0 |             0 |
| Gansu      | True     |       0.05 |            3 |     172,282 |     137,710 |             0 |             0 |             0 |
| Gansu      | True     |        0.1 |            1 |     344,564 |     299,028 |             0 |             0 |             0 |
| Gansu      | True     |        0.1 |            3 |     344,564 |     275,372 |             0 |             0 |             0 |
| Gansu      | True     |        0.2 |            1 |     689,127 |     597,887 |             0 |             0 |             0 |
| Gansu      | True     |        0.2 |            3 |     689,127 |     550,653 |             0 |             0 |             0 |
| Guizhou    | False    |       0.05 |            1 |     289,389 |     260,341 |             0 |             0 |             0 |
| Guizhou    | False    |       0.05 |            3 |     289,389 |     246,129 |             0 |             0 |             0 |
| Guizhou    | False    |        0.1 |            1 |     578,779 |     517,361 |             0 |             0 |             0 |
| Guizhou    | False    |        0.1 |            3 |     578,779 |     488,041 |             0 |             0 |             0 |
| Guizhou    | False    |        0.2 |            1 |   1,157,558 |   1,022,775 |             0 |             0 |             0 |
| Guizhou    | False    |        0.2 |            3 |   1,157,558 |     958,617 |             0 |             0 |             0 |
| Guizhou    | True     |       0.05 |            1 |     289,389 |     251,072 |             0 |             0 |             0 |
| Guizhou    | True     |       0.05 |            3 |     289,389 |     231,239 |             0 |             0 |             0 |
| Guizhou    | True     |        0.1 |            1 |     578,779 |     502,144 |             0 |             0 |             0 |
| Guizhou    | True     |        0.1 |            3 |     578,779 |     462,478 |             0 |             0 |             0 |
| Guizhou    | True     |        0.2 |            1 |   1,157,558 |   1,004,288 |             0 |             0 |             0 |
| Guizhou    | True     |        0.2 |            3 |   1,157,558 |     924,956 |             0 |             0 |             0 |
| Jiangsu    | False    |       0.05 |            1 |     896,015 |     777,748 |             0 |             0 |             0 |
| Jiangsu    | False    |       0.05 |            3 |     896,015 |     715,968 |             0 |             0 |             0 |
| Jiangsu    | False    |        0.1 |            1 |   1,792,029 |   1,555,066 |             0 |             0 |       165.982 |
| Jiangsu    | False    |        0.1 |            3 |   1,792,029 |   1,431,936 |             0 |             0 |       165.982 |
| Jiangsu    | False    |        0.2 |            1 |   3,584,059 |   3,118,654 |      9498.094 |       591.061 |       969.722 |
| Jiangsu    | False    |        0.2 |            3 |   3,584,059 |   2,870,654 |      9498.094 |             0 |       969.722 |
| Jiangsu    | True     |       0.05 |            1 |     896,015 |     777,375 |             0 |             0 |             0 |
| Jiangsu    | True     |       0.05 |            3 |     896,015 |     715,968 |             0 |             0 |             0 |
| Jiangsu    | True     |        0.1 |            1 |   1,792,029 |   1,554,750 |             0 |             0 |             0 |
| Jiangsu    | True     |        0.1 |            3 |   1,792,029 |   1,431,936 |             0 |             0 |             0 |
| Jiangsu    | True     |        0.2 |            1 |   3,584,059 |   3,109,500 |             0 |             0 |             0 |
| Jiangsu    | True     |        0.2 |            3 |   3,584,059 |   2,863,872 |             0 |             0 |             0 |

## S8. 2030 scenario results, neighbour-aggregate exchange node (export = True rows), idle 41%

### S8a. Incremental system cost by scenario (EUR per representative week)
| province   |   ai_share |   slack_mult |     cost_S0 |   cost_S0e |    cost_S1 |    cost_S3 |   cost_S1rt |    cost_S2 |
|:-----------|-----------:|-------------:|------------:|-----------:|-----------:|-----------:|------------:|-----------:|
| Gansu      |       0.05 |            1 |   4,790,243 |  4,160,773 |  4,179,565 |  4,179,565 |   4,155,356 |  4,155,344 |
| Gansu      |       0.05 |            3 |   4,790,243 |  3,836,905 |  3,864,010 |  3,864,010 |   3,832,843 |  3,832,843 |
| Gansu      |        0.1 |            1 |   9,578,732 |  8,319,781 |  8,357,807 |  8,357,807 |   8,311,059 |  8,309,365 |
| Gansu      |        0.1 |            3 |   9,578,732 |  7,672,038 |  7,726,246 |  7,726,246 |   7,663,942 |  7,663,934 |
| Gansu      |        0.2 |            1 |  19,148,256 | 16,635,459 | 16,713,269 | 16,713,269 |  16,616,220 | 16,616,145 |
| Gansu      |        0.2 |            3 |  19,148,256 | 15,334,546 | 15,442,977 | 15,442,977 |  15,320,840 | 15,320,114 |
| Guizhou    |       0.05 |            1 |   7,957,847 |  6,917,865 |  6,939,766 |  6,939,766 |   6,906,688 |  6,906,486 |
| Guizhou    |       0.05 |            3 |   7,957,847 |  6,377,242 |  6,404,402 |  6,404,402 |   6,358,127 |  6,357,912 |
| Guizhou    |        0.1 |            1 |  15,912,304 | 13,822,922 | 13,868,325 | 13,868,325 |  13,802,506 | 13,800,894 |
| Guizhou    |        0.1 |            3 |  15,912,304 | 12,738,025 | 12,792,399 | 12,792,399 |  12,703,082 | 12,699,252 |
| Guizhou    |        0.2 |            1 |  31,796,779 | 27,576,531 | 27,673,179 | 27,673,179 |  27,541,847 | 27,537,910 |
| Guizhou    |        0.2 |            3 |  31,796,779 | 25,395,318 | 25,504,306 | 25,504,306 |  25,336,671 | 25,324,864 |
| Jiangsu    |       0.05 |            1 |  25,357,177 | 21,990,421 | 22,116,628 | 22,116,628 |  21,986,826 | 21,986,396 |
| Jiangsu    |       0.05 |            3 |  25,357,177 | 20,250,776 | 20,352,469 | 20,352,469 |  20,246,219 | 20,245,767 |
| Jiangsu    |        0.1 |            1 |  50,791,070 | 44,044,923 | 44,295,969 | 44,295,969 |  44,038,246 | 44,036,425 |
| Jiangsu    |        0.1 |            3 |  50,791,070 | 40,552,024 | 40,752,646 | 40,752,646 |  40,539,961 | 40,539,502 |
| Jiangsu    |        0.2 |            1 | 101,894,177 | 88,322,269 | 88,822,356 | 88,822,356 |  88,307,976 | 88,302,467 |
| Jiangsu    |        0.2 |            3 | 101,894,177 | 81,305,696 | 81,713,472 | 81,713,472 |  81,280,684 | 81,276,226 |

### S8b. Reductions, gaps and realised shares
| province   |   ai_share |   slack_mult |   red_S0_S2_pct |   red_S0_S0e_pct |   gap_S0e_S2_pct |   share_S1 |   timing_share_S1 |   timing_share_S1rt |   gap_S1rt_S2_pct |
|:-----------|-----------:|-------------:|----------------:|-----------------:|-----------------:|-----------:|------------------:|--------------------:|------------------:|
| Gansu      |       0.05 |            1 |          13.254 |           13.141 |            0.131 |      0.962 |            -3.461 |               0.998 |                 0 |
| Gansu      |       0.05 |            3 |          19.986 |           19.902 |            0.106 |      0.967 |            -6.672 |                   1 |                 0 |
| Gansu      |        0.1 |            1 |          13.252 |           13.143 |            0.125 |      0.962 |            -3.651 |               0.837 |              0.02 |
| Gansu      |        0.1 |            3 |           19.99 |           19.905 |            0.106 |      0.967 |             -6.69 |               0.999 |                 0 |
| Gansu      |        0.2 |            1 |          13.224 |           13.123 |            0.116 |      0.962 |            -4.029 |               0.996 |                 0 |
| Gansu      |        0.2 |            3 |          19.992 |           19.917 |            0.094 |      0.968 |            -7.513 |                0.95 |             0.005 |
| Guizhou    |       0.05 |            1 |          13.212 |           13.069 |            0.165 |      0.968 |            -1.925 |               0.982 |             0.003 |
| Guizhou    |       0.05 |            3 |          20.105 |           19.862 |            0.304 |      0.971 |            -1.405 |               0.989 |             0.003 |
| Guizhou    |        0.1 |            1 |          13.269 |           13.131 |             0.16 |      0.968 |            -2.061 |               0.927 |             0.012 |
| Guizhou    |        0.1 |            3 |          20.192 |           19.949 |            0.305 |      0.971 |            -1.402 |               0.901 |              0.03 |
| Guizhou    |        0.2 |            1 |          13.394 |           13.273 |             0.14 |      0.968 |            -2.502 |               0.898 |             0.014 |
| Guizhou    |        0.2 |            3 |          20.354 |           20.132 |            0.278 |      0.972 |            -1.547 |               0.832 |             0.047 |
| Jiangsu    |       0.05 |            1 |          13.293 |           13.277 |            0.018 |      0.961 |           -31.358 |               0.893 |             0.002 |
| Jiangsu    |       0.05 |            3 |          20.158 |           20.138 |            0.025 |      0.979 |           -20.303 |                0.91 |             0.002 |
| Jiangsu    |        0.1 |            1 |          13.299 |           13.282 |            0.019 |      0.962 |           -29.539 |               0.786 |             0.004 |
| Jiangsu    |        0.1 |            3 |          20.184 |           20.159 |            0.031 |      0.979 |           -16.022 |               0.963 |             0.001 |
| Jiangsu    |        0.2 |            1 |          13.339 |            13.32 |            0.022 |      0.962 |           -25.254 |               0.722 |             0.006 |
| Jiangsu    |        0.2 |            3 |          20.235 |           20.206 |            0.036 |      0.979 |           -13.837 |               0.849 |             0.005 |

## S9. Multi-weather-year summary (islanded, export = False, AI 10%; min/median/max across ten weather years, 2015–2024)
Rows are metric_statistic; columns are province / idle-power fraction.

| metric                 |   Gansu / idle 0.25 |   Gansu / idle 0.41 |   Guizhou / idle 0.25 |   Guizhou / idle 0.41 |   Jiangsu / idle 0.25 |   Jiangsu / idle 0.41 |
|:-----------------------|--------------------:|--------------------:|----------------------:|----------------------:|----------------------:|----------------------:|
| red_S0_S2_pct_min      |              15.185 |              13.484 |                15.672 |                14.125 |                15.743 |                14.389 |
| red_S0_S2_pct_median   |              15.442 |              13.922 |                16.922 |                14.833 |                16.269 |                 14.92 |
| red_S0_S2_pct_max      |              16.063 |              14.305 |                 17.48 |                 15.32 |                 16.86 |                15.536 |
| red_S0_S0e_pct_min     |              14.598 |              13.159 |                14.051 |                13.289 |                15.136 |                13.954 |
| red_S0_S0e_pct_median  |              15.035 |              13.621 |                14.722 |                13.776 |                15.727 |                14.513 |
| red_S0_S0e_pct_max     |              15.227 |              13.809 |                15.108 |                13.964 |                16.189 |                 15.09 |
| gap_S0e_S2_pct_min     |               0.143 |               0.102 |                 1.922 |                 0.968 |                 0.513 |                  0.41 |
| gap_S0e_S2_pct_median  |               0.673 |               0.285 |                 2.703 |                 1.246 |                 0.791 |                 0.511 |
| gap_S0e_S2_pct_max     |               1.073 |               0.685 |                 3.296 |                 1.795 |                 0.948 |                 0.664 |
| timing_share_S1_min    |              -6.288 |              -5.091 |                 0.191 |                 0.039 |                -1.885 |                -0.988 |
| timing_share_S1_median |              -0.469 |              -1.437 |                 0.312 |                 0.234 |                -0.989 |                -0.691 |
| timing_share_S1_max    |              -0.051 |               0.006 |                 0.409 |                 0.334 |                -0.355 |                -0.404 |
| gap_S1_S2_pct_min      |               0.931 |               0.614 |                 1.377 |                 0.763 |                 1.095 |                  0.74 |
| gap_S1_S2_pct_median   |               1.114 |               0.687 |                 1.749 |                 0.957 |                 1.481 |                 0.843 |
| gap_S1_S2_pct_max      |               1.436 |               0.805 |                 2.356 |                 1.465 |                 1.934 |                 1.219 |
| gap_S1rt_S2_pct_min    |               0.058 |               0.012 |                 0.364 |                 0.187 |                 0.168 |                 0.022 |
| gap_S1rt_S2_pct_median |               0.125 |               0.069 |                 0.569 |                 0.284 |                 0.258 |                 0.071 |
| gap_S1rt_S2_pct_max    |               0.389 |               0.215 |                 0.784 |                 0.354 |                  0.31 |                 0.173 |
| curtail_NOAI_min       |               0.036 |               0.036 |                 0.122 |                 0.122 |                     0 |                     0 |
| curtail_NOAI_median    |               0.055 |               0.055 |                 0.249 |                 0.249 |                     0 |                     0 |
| curtail_NOAI_max       |               0.105 |               0.105 |                 0.322 |                 0.323 |                     0 |                     0 |
| new_ocgt_S0_min        |                   0 |                   0 |                     0 |                     0 |                     0 |                     0 |
| new_ocgt_S0_median     |                   0 |                   0 |                     0 |                     0 |                     0 |                     0 |
| new_ocgt_S0_max        |                   0 |                   0 |                     0 |                     0 |                     0 |                     0 |
| new_ocgt_S2_min        |                   0 |                   0 |                     0 |                     0 |                     0 |                     0 |
| new_ocgt_S2_median     |                   0 |                   0 |                     0 |                     0 |                     0 |                     0 |
| new_ocgt_S2_max        |                   0 |                   0 |                     0 |                     0 |                     0 |                     0 |

## S10. Cost-parameter Monte Carlo summary (islanded, export = False, AI 10%; 20 feasible draws per province, infeasible or timed-out draws excluded)
Rows are metric and statistic (count, mean, standard deviation, minimum, 10th/50th/90th percentile, maximum); columns are provinces.

| metric          | statistic   |   Gansu |   Guizhou |   Jiangsu |
|:----------------|:------------|--------:|----------:|----------:|
| red_S0_S2_pct   | count       |      20 |        20 |        20 |
| red_S0_S2_pct   | mean        |  19.592 |    18.259 |    18.329 |
| red_S0_S2_pct   | std         |   5.983 |     6.947 |     6.705 |
| red_S0_S2_pct   | min         |   8.785 |    10.071 |     9.001 |
| red_S0_S2_pct   | 10%         |   9.543 |    10.835 |    10.286 |
| red_S0_S2_pct   | 50%         |  21.229 |    17.416 |     19.31 |
| red_S0_S2_pct   | 90%         |  24.802 |     27.05 |    26.704 |
| red_S0_S2_pct   | max         |  29.091 |     28.22 |    27.158 |
| red_S0_S0e_pct  | count       |      20 |        20 |        20 |
| red_S0_S0e_pct  | mean        |  19.196 |    16.895 |    17.767 |
| red_S0_S0e_pct  | std         |   5.806 |     6.673 |      6.57 |
| red_S0_S0e_pct  | min         |   8.742 |     9.345 |     8.998 |
| red_S0_S0e_pct  | 10%         |   9.412 |     9.658 |    10.009 |
| red_S0_S0e_pct  | 50%         |  20.793 |    15.666 |    18.044 |
| red_S0_S0e_pct  | 90%         |  24.293 |    25.768 |    25.923 |
| red_S0_S0e_pct  | max         |  28.105 |    25.991 |    26.305 |
| gap_S0e_S2_pct  | count       |      20 |        20 |        20 |
| gap_S0e_S2_pct  | mean        |   0.512 |     1.708 |     0.706 |
| gap_S0e_S2_pct  | std         |   0.587 |     0.704 |     0.479 |
| gap_S0e_S2_pct  | min         |   0.047 |     0.807 |     0.003 |
| gap_S0e_S2_pct  | 10%         |   0.079 |     0.936 |     0.235 |
| gap_S0e_S2_pct  | 50%         |    0.33 |     1.625 |     0.678 |
| gap_S0e_S2_pct  | 90%         |       1 |     2.536 |     1.146 |
| gap_S0e_S2_pct  | max         |   2.657 |     3.419 |     2.023 |
| timing_share_S1 | count       |      20 |        20 |        20 |
| timing_share_S1 | mean        |  -1.544 |     0.253 |    -3.289 |
| timing_share_S1 | std         |   2.485 |     0.186 |     8.396 |
| timing_share_S1 | min         |  -7.774 |    -0.169 |    -36.07 |
| timing_share_S1 | 10%         |  -4.565 |    -0.017 |    -7.205 |
| timing_share_S1 | 50%         |  -0.142 |      0.28 |    -0.165 |
| timing_share_S1 | 90%         |   0.426 |     0.412 |     0.236 |
| timing_share_S1 | max         |   0.569 |     0.534 |     0.337 |
| gap_S1_S2_pct   | count       |      20 |        20 |        20 |
| gap_S1_S2_pct   | mean        |   0.766 |     1.325 |     1.131 |
| gap_S1_S2_pct   | std         |   0.697 |     0.799 |     0.811 |
| gap_S1_S2_pct   | min         |   0.032 |     0.435 |     0.093 |
| gap_S1_S2_pct   | 10%         |   0.234 |     0.665 |       0.3 |
| gap_S1_S2_pct   | 50%         |   0.481 |     1.195 |     0.933 |
| gap_S1_S2_pct   | 90%         |   1.503 |       1.9 |      2.37 |
| gap_S1_S2_pct   | max         |   2.628 |     3.998 |     2.964 |
| gap_S1rt_S2_pct | count       |      20 |        20 |        20 |
| gap_S1rt_S2_pct | mean        |   0.118 |     0.464 |     0.189 |
| gap_S1rt_S2_pct | std         |   0.112 |     0.275 |      0.16 |
| gap_S1rt_S2_pct | min         |   0.022 |     0.091 |         0 |
| gap_S1rt_S2_pct | 10%         |   0.034 |     0.177 |      0.03 |
| gap_S1rt_S2_pct | 50%         |   0.087 |     0.412 |     0.146 |
| gap_S1rt_S2_pct | 90%         |   0.202 |     0.783 |     0.349 |
| gap_S1rt_S2_pct | max         |   0.518 |      1.08 |     0.586 |
| new_ocgt_S0     | count       |      20 |        20 |        20 |
| new_ocgt_S0     | mean        |       0 |         0 |         0 |
| new_ocgt_S0     | std         |       0 |         0 |         0 |
| new_ocgt_S0     | min         |       0 |         0 |         0 |
| new_ocgt_S0     | 10%         |       0 |         0 |         0 |
| new_ocgt_S0     | 50%         |       0 |         0 |         0 |
| new_ocgt_S0     | 90%         |       0 |         0 |         0 |
| new_ocgt_S0     | max         |       0 |         0 |         0 |
| new_ocgt_S2     | count       |      20 |        20 |        20 |
| new_ocgt_S2     | mean        |       0 |         0 |         0 |
| new_ocgt_S2     | std         |       0 |         0 |         0 |
| new_ocgt_S2     | min         |       0 |         0 |         0 |
| new_ocgt_S2     | 10%         |       0 |         0 |         0 |
| new_ocgt_S2     | 50%         |       0 |         0 |         0 |
| new_ocgt_S2     | 90%         |       0 |         0 |         0 |
| new_ocgt_S2     | max         |       0 |         0 |         0 |

## S11. Peak-adjusted sensitivity (incremental cost, EUR per representative week)
| province   | ext_mode   | export   | peak_adjusted   |   ai_share | case   |   inc_cost |   new_ocgt |   new_batt |   curtail_NOAI |   peak_2030 |
|:-----------|:-----------|:---------|:----------------|-----------:|:-------|-----------:|-----------:|-----------:|---------------:|------------:|
| Gansu      | price      | False    | False           |        0.1 | S0     |  9,391,522 |          0 |          0 |          0.025 |   24971.916 |
| Gansu      | price      | False    | False           |        0.1 | S0e    |  8,113,527 |          0 |          0 |          0.025 |   24971.916 |
| Gansu      | price      | False    | False           |        0.1 | S1     |  8,157,286 |          0 |          0 |          0.025 |   24971.916 |
| Gansu      | price      | False    | False           |        0.1 | S1rt   |  8,110,767 |          0 |          0 |          0.025 |   24971.916 |
| Gansu      | price      | False    | False           |        0.1 | S2     |  8,106,916 |          0 |          0 |          0.025 |   24971.916 |
| Gansu      | price      | False    | False           |        0.1 | S3     |  8,157,286 |          0 |          0 |          0.025 |   24971.916 |
| Gansu      | price      | False    | False           |        0.2 | S0     | 18,494,780 |          0 |          0 |          0.068 |   24971.916 |
| Gansu      | price      | False    | False           |        0.2 | S0e    | 15,929,656 |          0 |          0 |          0.068 |   24971.916 |
| Gansu      | price      | False    | False           |        0.2 | S1     | 16,017,524 |          0 |          0 |          0.068 |   24971.916 |
| Gansu      | price      | False    | False           |        0.2 | S1rt   | 15,924,103 |          0 |          0 |          0.068 |   24971.916 |
| Gansu      | price      | False    | False           |        0.2 | S2     | 15,917,783 |          0 |          0 |          0.068 |   24971.916 |
| Gansu      | price      | False    | False           |        0.2 | S3     | 16,017,524 |          0 |          0 |          0.068 |   24971.916 |
| Gansu      | price      | False    | True            |        0.1 | S0     |  8,488,611 |          0 |          0 |          0.017 |   22409.549 |
| Gansu      | price      | False    | True            |        0.1 | S0e    |  7,340,650 |          0 |          0 |          0.017 |   22409.549 |
| Gansu      | price      | False    | True            |        0.1 | S1     |  7,381,484 |          0 |          0 |          0.017 |   22409.549 |
| Gansu      | price      | False    | True            |        0.1 | S1rt   |  7,338,515 |          0 |          0 |          0.017 |   22409.549 |
| Gansu      | price      | False    | True            |        0.1 | S2     |  7,336,706 |          0 |          0 |          0.017 |   22409.549 |
| Gansu      | price      | False    | True            |        0.1 | S3     |  7,381,484 |          0 |          0 |          0.017 |   22409.549 |
| Gansu      | price      | False    | True            |        0.2 | S0     | 16,718,273 |          0 |          0 |          0.052 |   22409.549 |
| Gansu      | price      | False    | True            |        0.2 | S0e    | 14,414,338 |          0 |          0 |          0.052 |   22409.549 |
| Gansu      | price      | False    | True            |        0.2 | S1     | 14,497,019 |          0 |          0 |          0.052 |   22409.549 |
| Gansu      | price      | False    | True            |        0.2 | S1rt   | 14,414,250 |          0 |          0 |          0.052 |   22409.549 |
| Gansu      | price      | False    | True            |        0.2 | S2     | 14,408,208 |          0 |          0 |          0.052 |   22409.549 |
| Gansu      | price      | False    | True            |        0.2 | S3     | 14,497,019 |          0 |          0 |          0.052 |   22409.549 |
| Gansu      | neighbours | True     | False           |        0.1 | S0     |  9,578,732 |          0 |          0 |          0.004 |   24971.916 |
| Gansu      | neighbours | True     | False           |        0.1 | S0e    |  8,319,781 |          0 |          0 |          0.004 |   24971.916 |
| Gansu      | neighbours | True     | False           |        0.1 | S1     |  8,357,807 |          0 |          0 |          0.004 |   24971.916 |
| Gansu      | neighbours | True     | False           |        0.1 | S1rt   |  8,311,059 |          0 |          0 |          0.004 |   24971.916 |
| Gansu      | neighbours | True     | False           |        0.1 | S2     |  8,309,365 |          0 |          0 |          0.004 |   24971.916 |
| Gansu      | neighbours | True     | False           |        0.1 | S3     |  8,357,807 |          0 |          0 |          0.004 |   24971.916 |
| Gansu      | neighbours | True     | False           |        0.2 | S0     | 19,148,256 |          0 |          0 |          0.006 |   24971.916 |
| Gansu      | neighbours | True     | False           |        0.2 | S0e    | 16,635,459 |          0 |          0 |          0.006 |   24971.916 |
| Gansu      | neighbours | True     | False           |        0.2 | S1     | 16,713,269 |          0 |          0 |          0.006 |   24971.916 |
| Gansu      | neighbours | True     | False           |        0.2 | S1rt   | 16,616,220 |          0 |          0 |          0.006 |   24971.916 |
| Gansu      | neighbours | True     | False           |        0.2 | S2     | 16,616,145 |          0 |          0 |          0.006 |   24971.916 |
| Gansu      | neighbours | True     | False           |        0.2 | S3     | 16,713,269 |          0 |          0 |          0.006 |   24971.916 |
| Gansu      | neighbours | True     | True            |        0.1 | S0     |  8,597,494 |          0 |          0 |          0.003 |   22409.549 |
| Gansu      | neighbours | True     | True            |        0.1 | S0e    |  7,467,710 |          0 |          0 |          0.003 |   22409.549 |
| Gansu      | neighbours | True     | True            |        0.1 | S1     |  7,501,527 |          0 |          0 |          0.003 |   22409.549 |
| Gansu      | neighbours | True     | True            |        0.1 | S1rt   |  7,458,148 |          0 |          0 |          0.003 |   22409.549 |
| Gansu      | neighbours | True     | True            |        0.1 | S2     |  7,458,068 |          0 |          0 |          0.003 |   22409.549 |
| Gansu      | neighbours | True     | True            |        0.1 | S3     |  7,501,527 |          0 |          0 |          0.003 |   22409.549 |
| Gansu      | neighbours | True     | True            |        0.2 | S0     | 17,186,950 |          0 |          0 |          0.005 |   22409.549 |
| Gansu      | neighbours | True     | True            |        0.2 | S0e    | 14,931,508 |          0 |          0 |          0.005 |   22409.549 |
| Gansu      | neighbours | True     | True            |        0.2 | S1     | 15,001,276 |          0 |          0 |          0.005 |   22409.549 |
| Gansu      | neighbours | True     | True            |        0.2 | S1rt   | 14,914,691 |          0 |          0 |          0.005 |   22409.549 |
| Gansu      | neighbours | True     | True            |        0.2 | S2     | 14,914,307 |          0 |          0 |          0.005 |   22409.549 |
| Gansu      | neighbours | True     | True            |        0.2 | S3     | 15,001,276 |          0 |          0 |          0.005 |   22409.549 |
| Guizhou    | price      | False    | False           |        0.1 | S0     | 12,737,351 |          0 |          0 |          0.306 |   41946.452 |
| Guizhou    | price      | False    | False           |        0.1 | S0e    | 10,999,516 |          0 |          0 |          0.306 |   41946.452 |
| Guizhou    | price      | False    | False           |        0.1 | S1     | 10,959,127 |          0 |          0 |          0.306 |   41946.452 |
| Guizhou    | price      | False    | False           |        0.1 | S1rt   | 10,882,236 |          0 |          0 |          0.306 |   41946.452 |
| Guizhou    | price      | False    | False           |        0.1 | S2     | 10,850,800 |          0 |          0 |          0.306 |   41946.452 |
| Guizhou    | price      | False    | False           |        0.1 | S3     | 10,962,125 |          0 |          0 |          0.306 |   41946.452 |
| Guizhou    | price      | False    | False           |        0.2 | S0     | 25,007,943 |          0 |          0 |          0.435 |   41946.452 |
| Guizhou    | price      | False    | False           |        0.2 | S0e    | 21,243,656 |          0 |          0 |          0.435 |   41946.452 |
| Guizhou    | price      | False    | False           |        0.2 | S1     | 21,221,539 |          0 |          0 |          0.435 |   41946.452 |
| Guizhou    | price      | False    | False           |        0.2 | S1rt   | 21,120,171 |          0 |          0 |          0.435 |   41946.452 |
| Guizhou    | price      | False    | False           |        0.2 | S2     | 20,999,481 |          0 |          0 |          0.435 |   41946.452 |
| Guizhou    | price      | False    | False           |        0.2 | S3     | 21,221,539 |          0 |          0 |          0.435 |   41946.452 |
| Guizhou    | price      | False    | True            |        0.1 | S0     | 12,739,894 |          0 |          0 |          0.255 |   38919.945 |
| Guizhou    | price      | False    | True            |        0.1 | S0e    | 11,054,777 |          0 |          0 |          0.255 |   38919.945 |
| Guizhou    | price      | False    | True            |        0.1 | S1     | 11,029,002 |          0 |          0 |          0.255 |   38919.945 |
| Guizhou    | price      | False    | True            |        0.1 | S1rt   | 10,963,723 |          0 |          0 |          0.255 |   38919.945 |
| Guizhou    | price      | False    | True            |        0.1 | S2     | 10,931,892 |          0 |          0 |          0.255 |   38919.945 |
| Guizhou    | price      | False    | True            |        0.1 | S3     | 11,029,002 |          0 |          0 |          0.255 |   38919.945 |
| Guizhou    | price      | False    | True            |        0.2 | S0     | 24,696,485 |          0 |          0 |          0.401 |   38919.945 |
| Guizhou    | price      | False    | True            |        0.2 | S0e    | 21,004,844 |          0 |          0 |          0.401 |   38919.945 |
| Guizhou    | price      | False    | True            |        0.2 | S1     | 21,051,233 |          0 |          0 |          0.401 |   38919.945 |
| Guizhou    | price      | False    | True            |        0.2 | S1rt   | 20,941,978 |          0 |          0 |          0.401 |   38919.945 |
| Guizhou    | price      | False    | True            |        0.2 | S2     | 20,834,107 |          0 |          0 |          0.401 |   38919.945 |
| Guizhou    | price      | False    | True            |        0.2 | S3     | 21,051,233 |          0 |          0 |          0.401 |   38919.945 |
| Guizhou    | neighbours | True     | False           |        0.1 | S0     | 15,912,304 |          0 |          0 |          0.001 |   41946.452 |
| Guizhou    | neighbours | True     | False           |        0.1 | S0e    | 13,822,922 |          0 |          0 |          0.001 |   41946.452 |
| Guizhou    | neighbours | True     | False           |        0.1 | S1     | 13,868,325 |          0 |          0 |          0.001 |   41946.452 |
| Guizhou    | neighbours | True     | False           |        0.1 | S1rt   | 13,802,506 |          0 |          0 |          0.001 |   41946.452 |
| Guizhou    | neighbours | True     | False           |        0.1 | S2     | 13,800,894 |          0 |          0 |          0.001 |   41946.452 |
| Guizhou    | neighbours | True     | False           |        0.1 | S3     | 13,868,325 |          0 |          0 |          0.001 |   41946.452 |
| Guizhou    | neighbours | True     | False           |        0.2 | S0     | 31,796,779 |          0 |          0 |          0.003 |   41946.452 |
| Guizhou    | neighbours | True     | False           |        0.2 | S0e    | 27,576,531 |          0 |          0 |          0.003 |   41946.452 |
| Guizhou    | neighbours | True     | False           |        0.2 | S1     | 27,673,179 |          0 |          0 |          0.003 |   41946.452 |
| Guizhou    | neighbours | True     | False           |        0.2 | S1rt   | 27,541,847 |          0 |          0 |          0.003 |   41946.452 |
| Guizhou    | neighbours | True     | False           |        0.2 | S2     | 27,537,910 |          0 |          0 |          0.003 |   41946.452 |
| Guizhou    | neighbours | True     | False           |        0.2 | S3     | 27,673,179 |          0 |          0 |          0.003 |   41946.452 |
| Guizhou    | neighbours | True     | True            |        0.1 | S0     | 14,827,909 |          0 |          0 |              0 |   38919.945 |
| Guizhou    | neighbours | True     | True            |        0.1 | S0e    | 12,874,986 |          0 |          0 |              0 |   38919.945 |
| Guizhou    | neighbours | True     | True            |        0.1 | S1     | 12,919,408 |          0 |          0 |              0 |   38919.945 |
| Guizhou    | neighbours | True     | True            |        0.1 | S1rt   | 12,860,265 |          0 |          0 |              0 |   38919.945 |
| Guizhou    | neighbours | True     | True            |        0.1 | S2     | 12,857,139 |          0 |          0 |              0 |   38919.945 |
| Guizhou    | neighbours | True     | True            |        0.1 | S3     | 12,919,408 |          0 |          0 |              0 |   38919.945 |
| Guizhou    | neighbours | True     | True            |        0.2 | S0     | 29,618,173 |          0 |          0 |          0.001 |   38919.945 |
| Guizhou    | neighbours | True     | True            |        0.2 | S0e    | 25,683,631 |          0 |          0 |          0.001 |   38919.945 |
| Guizhou    | neighbours | True     | True            |        0.2 | S1     | 25,781,296 |          0 |          0 |          0.001 |   38919.945 |
| Guizhou    | neighbours | True     | True            |        0.2 | S1rt   | 25,653,364 |          0 |          0 |          0.001 |   38919.945 |
| Guizhou    | neighbours | True     | True            |        0.2 | S2     | 25,652,339 |          0 |          0 |          0.001 |   38919.945 |
| Guizhou    | neighbours | True     | True            |        0.2 | S3     | 25,781,296 |          0 |          0 |          0.001 |   38919.945 |

## S12. Mechanism comparison

### S12a. Settlement designs under identical tasks and reliability (rows are metrics; columns are provinces)
| metric                             |                                                Gansu |                                              Jiangsu |                                              Guizhou |
|:-----------------------------------|-----------------------------------------------------:|-----------------------------------------------------:|-----------------------------------------------------:|
| system_cost_S1                     |                                          159,260,672 |                                          550,965,702 |                                          114,426,853 |
| system_cost_S3                     |                                          159,260,672 |                                          551,261,129 |                                          114,429,851 |
| system_cost_S1rt                   |                                          159,214,152 |                                          550,685,488 |                                          114,349,963 |
| system_cost_S2                     |                                          159,210,301 |                                          550,617,327 |                                          114,318,526 |
| s3_saving_vs_S1                    |                                                    0 |                                             -295,427 |                                            -2998.019 |
| s3_compensation_floor_own_baseline |                                                    0 |                                              459,446 |                                            20236.509 |
| s3_mean_commitment_mw              |                                                    0 |                                              295.466 |                                               41.165 |
| s1rt_saving_vs_S1                  |                                            46519.224 |                                              280,214 |                                            76890.129 |
| gap_S1rt_S2_pct                    |                                                0.048 |                                                0.133 |                                                 0.29 |
| system_cost_S0                     |                                          160,494,908 |                                          560,080,895 |                                          116,205,077 |
| system_cost_S0e                    |                                          159,216,912 |                                          550,832,373 |                                          114,467,242 |
| system_cost_NOAI                   |                                          151,103,385 |                                          499,516,889 |                                          103,467,726 |
| n_events                           | {'winter': 0, 'spring': 0, 'summer': 0, 'autumn': 0} | {'winter': 8, 'spring': 0, 'summer': 0, 'autumn': 0} | {'winter': 0, 'spring': 0, 'summer': 8, 'autumn': 0} |
| ai_mwh_S1                          |                                              300,635 |                                            1,563,793 |                                              505,168 |
| ai_mwh_S1rt                        |                                              299,660 |                                            1,555,012 |                                              518,678 |

### S12b. Baseline-manipulation exposure of the event contract (rows are metrics; columns are province / week)
| metric                            |   Guizhou / week summer |   Jiangsu / week winter |
|:----------------------------------|------------------------:|------------------------:|
| n_events                          |                       8 |                       8 |
| commit_own_mw                     |                 164.662 |                1181.866 |
| comp_own                          |               80946.034 |               1,837,782 |
| commit_inflated_mw                |                  51.262 |                       0 |
| comp_inflated                     |                16112.12 |                       0 |
| inflated_minus_own_event_power_mw |                 689.945 |                3708.718 |
