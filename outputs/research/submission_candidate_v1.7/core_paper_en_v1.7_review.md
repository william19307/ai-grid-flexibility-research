# Service constraints and power boundaries shape the grid value of flexible AI computing

William Wei¹ ² and Lanlan Liu³

¹ School of Computer Science, Faculty of Engineering and Physical Sciences, University of Leeds, Leeds, UK

² Spatial Computing (Fujian) Technology Co., Ltd., Fuzhou, China

³ School of Public Administration, Fujian Normal University, Fuzhou, China

Correspondence: qkfp0742@leeds.ac.uk

Revision v1.7 power-boundary review edition | 27 September 2026 | Evidence consolidated through revision stage 37

**Manuscript status.** This edition integrates the supported revision findings with the stage 36 literature audit and the stage 37 public power-boundary audit. It is not submission-ready and does not replace the submitted v1.4. Provincial system-benefit estimates, annual firm-capacity results and implementable market comparisons remain to be recomputed. The title and abstract are provisional. Author details are retained from v1.4.

## Abstract

The value of flexible artificial intelligence computing depends on the service that must be preserved, the power boundary being measured and the electricity system that absorbs the response. We develop a framework that separates changes in operating mode from changes in job start time while retaining fixed work, GPU requirements and explicit completion benchmarks. In 108 paired conditions constructed from production traces, a fixed-start policy cannot slow jobs when no extra completion allowance is available; with longer allowances, mode changes account for a majority of the identified bill-reduction opportunity in most, but not all, conditions. These results concern a conditional GPU-power model rather than measured whole-node or grid savings. In an external same-system audit of 24 official 8-GPU H100 benchmark rows, capped operation retained 65.13–82.03% of standard performance, but the standard arm lacked AC system-power logs, so whole-node savings were not identifiable. Two analytical counterexamples show why translation to grid value requires additional care: inconsistent cohort accounting can reverse a capacity conclusion, and linear response endpoints need not bound supply costs with unit commitment. Audits of renewable profiles and generating assets reveal further limits to inference from annual agreement or unique database identifiers. Together, the results establish a testable framework for evaluating service-preserving computing flexibility. A complete provincial estimate requires common-hardware power measurements, matched demand and generation boundaries, historical decision-time information and fixed-investment annual validation.

## Introduction

AI-computing flexibility is already an empirical capability. A 256-GPU field demonstration reported a 25% power reduction for three hours while maintaining stated quality-of-service guarantees [1], and a later 130 kW deployment reported rapid and sustained curtailment, carbon-aware operation and spatial shifting while preserving priority-job service levels [2]. Trace-based quantification also exists: a study of more than one million Alibaba tasks used observed queue latency to classify deferrable work and reported up to 22% modeled load reduction during response windows [3]. These studies establish technical capability, but their service definitions, task cohorts, power boundaries and information sets differ.

Power-system planning studies already show that temporal flexibility can change investment, operating cost, emissions and resource adequacy [4–6]. Spatial migration and regional computing allocation have long been studied [7–9], while interconnection obligations, market remuneration and signal-based coordination have also been proposed [10–12]. We therefore make no claim of first demonstrating flexible AI computing, first using production traces, first modeling system value or first proposing a coordination mechanism. The unresolved question addressed here is narrower: whether operating-mode and start-time decisions can be attributed on the same fixed task cohort and completion benchmark, and what additional evidence is required before that attribution becomes a physical grid-value claim.

Our contribution is a controlled boundary test. We compare four policy cells that differ only in start-time and operating-mode permissions while retaining the same work, GPU requirements, background allocations, prices and completion benchmark. We then test translation to the electricity system with two analytical counterexamples and with audits of power, demand and supply inputs. The results below report only the portions supported by this chain. The former provincial benefit ranges and gas-capacity avoidance estimates remain historical scenario outputs and are not carried into this edition as revised findings.

## Results

### The completion benchmark changes the attribution

We retain the original GPU count and a work proxy equal to recorded GPU count multiplied by runtime. Every target job executes once in a continuous interval without preemption. Other recorded allocations remain fixed background. The task cohort is drawn from four public Helios production clusters [13]. The completion benchmark is the historical end time plus an analyst-defined allowance of 0, 6 or 24 hours. This is a retrospective comparison, not a contractual service-level agreement inferred from queueing time [E1].

Four policy cells differ only in start-time and operating-mode permissions. They share the task cohort, background allocations, prices, power assumptions and retrospective information. C10 retains the observed start but may finish later, so it is a fixed-start policy rather than a physically time-invariant energy-only policy.

| Cell | Start time | Operating mode |
|---|---|---|
| C00 | Observed start | Full reference speed |
| C10 | Observed start | Mode choice allowed |
| C01 | Adjustable within the fixed window | Full reference speed |
| C11 | Adjustable within the fixed window | Mode choice allowed |

The April comparison uses 28,716 distinct target jobs across four clusters, three curve assignments, three completion allowances and three tariff shapes. This yields 108 conditions and 432 constructed schedules. The conditions reuse jobs and correlated curves; they are not independent statistical replications. All schedules passed independent work, service-window and aggregate GPU-capacity checks [E2]. The construction is a feasible one-sweep improvement heuristic, not a global optimum certificate.

| Extra completion allowance | Conditions | Mode share of constructed bill savings | Optimal majority identified by bounds |
|---|---:|---:|---|
| 0 hours | 36 | 16.38–45.00% | Start-time majority in 36 |
| 6 hours | 36 | 54.04–84.41% | Mode majority in 34; unresolved in 2 |
| 24 hours | 36 | 58.98–83.76% | Mode majority in 33; unresolved in 3 |

Feasible policy costs and relaxed lower bounds define deterministic identification intervals for the optimal attribution (Fig. 1). A mode majority in a constructed schedule does not establish a majority in the global optimum: five conditions remain unresolved. The bill includes fixed background and assumed idle GPU consumption; it is neither an actual customer bill nor a system-cost estimate. Historical tariff shapes derive from published provincial documents [14–16] and are applied as declared hypothetical price conditions on the trace clock [E2].

There is a structural reason for the zero-allowance result. If recorded runtime defines full-speed work, every alternative mode is strictly slower, and the observed start and completion time are fixed, no slower mode can complete that work. Therefore C10 equals C00. For nested optimal policy sets with positive total savings, the symmetric mode attribution cannot exceed one half. The statement is specific to this decision matrix and work definition; it is not a universal bound on the contribution of hardware efficiency.

Across all tested conditions, 57 of 108 constructed joint policies have a higher hourly GPU peak than the reference, with a maximum increase of 11.37%, despite lower modeled GPU energy. These are synchronized cluster GPU peaks, not coincident system peaks or connection-capacity requirements. They demonstrate why energy reduction alone is insufficient to establish capacity value [E2].

### Fixed-service replay extends across time under stated assumptions

A separate calendar-fixed validation covers 12 cluster-week cohorts and 118,703 distinct job records across May, July and September 2020. Eight curve labels and three completion allowances produce 288 paired conditions. All constructed schedules passed independent raw-record work, window and event-capacity checks. The selected jobs account for 26.62–40.59% of recorded GPU occupation in the respective source weeks; the remaining occupation is preserved as background [E1].

All arms retain a 192-hour domain, including the observed tail after the source week. The successful replay validates a schedule under aggregate GPU capacity and assumed curve transfer. It does not establish device placement, model availability, network topology, output quality, actual service contracts, online control or whole-node energy savings. Those constraints are material in deployed demonstrations and inference-cluster studies [1,2,17,18]. The additional periods validate a frozen construction after earlier trace inspection; they are not a new prospective deployment experiment.

### Accounting boundaries can reverse a capacity comparison

A controlled cohort must be added exactly once. If a supplied demand series already contains its reference consumption, the reference cohort must first be removed to construct a common background. Otherwise every policy carries an extra copy of the reference load, which may alter capacity and commitment decisions [E3].

A two-hour example makes the consequence explicit. An observed total [8, 8] MW includes the reference cohort [4, 0] MW, so the common background is [4, 8] MW. A controlled cohort [0, 2] MW changes the true peak from 8 to 10 MW, whereas double counting changes the apparent peak from 12 to 10 MW. Under arbitrary investment and variable costs, the respective totals are 160 to 170 and 220 to 190. This proves a possible sign reversal, not its size in the provincial manuscript.

The implemented ledger supports both genuinely incremental and already embedded cohorts, preserves a common background and rejects incompatible clocks or negative reconstructed background. Four complete certified task-policy trajectories have entered the grid interface over all 192 hours. Their whole-node conversion and 3 MW background remain explicit test assumptions rather than calibrated Jiangsu demand [E3].

### Linear procurement bounds do not bound nonlinear supply costs

The revised mechanism comparison separates information available when a response is purchased from outcomes evaluated later. Earlier work already studies spatiotemporal remuneration and signal-based coordination [11,12]; our narrower test fixes the purchased response before realized grid outcomes are evaluated. Fixed responses enter the same grid model with the same installed assets and background demand. Commitment and dispatch can change in response to load, but the response is not reselected after seeing the realized system outcome [E4].

A continuous-response counterexample shows that the endpoints minimizing and maximizing a linear forecast objective need not bracket actual supply costs. If recovery can occur in either of two hours, each requiring a different initially offline generator, an endpoint activates one generator while an interior split activates both. With zero variable cost and a startup cost of 10 per generator, both endpoints cost 10 and all interior splits cost 20. These are synthetic units chosen for the proof. Evaluating only linear extremes can therefore miss the physical worst case when commitment is endogenous.

This result limits what can be concluded from the former event-contract comparison. A failed event rule does not show that event procurement is generally inferior. General pessimistic procurement over the full response set, an implementable selection rule, historical forecast vintages and strategic-provider behavior remain unresolved. Ex-post prices derived from the coordinated solution remain a benchmark, not evidence of a deployable tariff [E4].

### Physical supply inputs require more than aggregate agreement

The audited supply chain uses public reanalysis, weather, provincial-load, power-system and asset bundles [19–23], but source identity does not establish physical calibration. An exploratory offshore-wind diagnostic holds a 2022 annual calibration fixed and compares later company disclosures with modeled generation. In 2023, the NREL reference shape has an annual error of −0.551%, while the sum of absolute quarterly errors equals 13.075% of annual observed generation. The annual total hides offsetting seasonal errors. The reported scope is company-controlled offshore generation; its assignment to the H2 proxy remains an evidence-based inference, and the quarterly series is not hourly meter data [E5].

An inventory audit also separates record identity from physical asset identity. The selected oil/gas cohort initially comprises 109 source rows totaling 24,959 MW. Technical fields identify 97 combined-cycle records and 12 industrial by-product-gas steam-turbine records; applying one OCGT parameter set to all of them is unsupported. Two Funing entries share the same project source and match the operator's two-unit description. An explicit research alias adjudication maps the four rows to two candidate assets, giving 107 candidates totaling 24,759 MW. Original identifiers and metadata conflicts are retained [E6].

The revised view contains 95 CCGT candidates, including 80 reported CHP candidates and 15 with unresolved heat-service status, plus 12 industrial candidates. It is not a verified 2030 operating fleet. Heat obligations, industrial fuel sharing, net grid interfaces, commissioning and retirement, and unit operating limits still require evidence. Neither the 200 MW accounting correction nor a small annual renewable error can be converted directly into a corrected system-benefit percentage.

### Public same-system power evidence remains one-sided

Recent high-resolution training data include 32 sessions on 8-GPU H100 and B200 nodes at 20 ms resolution, but their node-power variable is the sum of GPU telemetry because whole-node access was unavailable [24]. These traces resolve fast device dynamics; they do not measure the AC input of the server or facility.

We separately extracted matched NVIDIA submissions from the official MLPerf Inference v4.0 repository at a fixed commit [25]. The standard and MaxQ system descriptions identify the same DGX H100 hardware and software fields apart from the system name. Across 24 matched benchmark–accuracy–scenario rows, both arms have valid performance and accuracy records. MaxQ retains 65.13–82.03% of standard performance, with a median of 74.57%. Its submitted Yokogawa measurements report mean system input of 3.777–5.377 kW, with at least 600 one-second samples per row. The rows include duplicated performance runs across some accuracy targets and are not independent repetitions.

MLPerf requires system-level AC measurement, inclusion of active host components and same-run power and performance [26]. However, the matched standard arm contains no submitted power logs. The public pair therefore supports a workload-dependent service-performance comparison and a measured MaxQ power level, but it cannot identify the change in whole-node power, energy per completed sample or energy savings. Common hardware is necessary but insufficient: both operating arms must cross the same measurement boundary while delivering matched useful work and quality [E8].

## Discussion

The supported conclusion is that attribution and system value depend on explicitly defined service, power and supply boundaries. The external benchmark audit makes the measurement requirement concrete: a valid capped-power run does not establish savings when its standard comparator lacks power measurement. The literature audit shows that capability, trace-based deferral and grid-value modeling are established research areas; novelty cannot rest on any one of them. Under the tested decision rights, the apparent contribution of mode choice changes with the completion allowance. Energy savings can coincide with a higher GPU peak, and a mathematically feasible task response can have an unfavorable grid consequence once recovery and commitment are represented. These findings motivate measurement and experimental design; they do not yet quantify the grid value of deployed AI clusters across the three provinces.

A complete empirical claim requires the same useful work and quality to be executed on common hardware while measuring idle, active and transition energy at a defined AC boundary. The demand series must identify whether the treated cohort is already included. Generation and transmission data must represent compatible vintages, fuel and heat obligations, water and storage balances, and physically available imports. Mechanisms must receive comparable information and be assessed against realized outcomes without retrospective choice.

The remaining system study should select investment once on a declared training information set, then operate that fixed portfolio through complete held-out periods, including failures, correlated outages, extreme conditions and unfinished terminal obligations. Previously inspected weather years cannot become an untouched test set merely by being downloaded again. Until this chain is completed, the former provincial reduction ranges, gigawatts of avoided generation and price-performance claims should remain in the historical submission rather than in a revised abstract.

## Methods overview

The supplementary review edition specifies the fixed-service cohort, policy objective, deterministic bounds, common-horizon power accounting, demand ledger and grid interfaces. Mathematical verification uses independent event scans, analytical cases, enumeration or scalar arithmetic where appropriate. Source validation records dates, scope, original identifiers, file hashes and unresolved interpretations. A hash demonstrates version identity, not source accuracy.

Current code includes unit commitment, energy-conserving storage and reservoirs, shared industrial fuel and a private-site grid interface, fixed-cohort demand construction and conditional mechanism evaluation. The external benchmark audit is a deterministic extraction from a pinned public result repository; it compares matched performance and accuracy records, submitted MaxQ AC power logs and system descriptions without fitting those data to the Helios schedules. These components have mathematical checks, but they have not been assembled into a fully calibrated provincial experiment. Reported check counts are implementation coverage, not scientific sample sizes or evidence of journal readiness.

## Data and code availability

The research repository is https://github.com/william19307/ai-grid-flexibility-research, branch codex/research-evidence-revision. The scheduling and physical-boundary results retain their frozen stage-specific evidence commits; the literature and novelty audit is anchored at commit 510780e9ead27698e33cedf24df5a5a171a8f11b, and the public power-boundary audit at commit b6da0c7. The package includes an evidence index and source-file hashes. External raw archives, prepared arrays and local environments require restoration through REPRODUCE.md; cloning alone does not reproduce the entire study. No new hardware measurements are claimed.

## References

1. Colangelo, P. et al. AI data centres as grid-interactive assets. Nat. Energy 11, 254–261 (2026). https://doi.org/10.1038/s41560-025-01927-1

2. Williams, C. et al. Power-flexible AI data centers: a new paradigm for grid-responsive compute. Preprint at https://arxiv.org/abs/2606.25098 (2026).

3. Caprara, A., Yu, Y., Teng, F., Junyent-Ferré, A., Bullich-Massagué, E. & Aragüés-Peñalba, M. Data center workload flexibility for power system demand response: evidence from Alibaba traces. Int. J. Electr. Power Energy Syst. 178, 111940 (2026). https://doi.org/10.1016/j.ijepes.2026.111940

4. Senga, J. R. L., Wang, S. & Knittel, C. R. Flexible data centers reduce power system costs but can increase emissions. iScience 29, 116497 (2026). https://doi.org/10.1016/j.isci.2026.116497

5. Chen, Y. & Zheng, X. To defer or to shift? The role of AI data center flexibility on grid interconnection. In Proc. 2026 ACM Sustainability Week 322–327 (ACM, 2026). https://doi.org/10.1145/3765611.3815593

6. Dunlap, C. Quantifying AI data center flexibility as a resource adequacy asset. Research Square preprint https://doi.org/10.21203/rs.3.rs-9829457/v1 (2026).

7. Zheng, J., Chien, A. A. & Suh, S. Mitigating curtailment and carbon emissions through load migration between data centers. Joule 4, 2208–2222 (2020). https://doi.org/10.1016/j.joule.2020.08.001

8. Fridgen, G., Keller, R., Thimmel, M. & Wederhake, L. Shifting load through space: the economics of spatial demand side management using distributed data centers. Energy Policy 109, 400–413 (2017). https://doi.org/10.1016/j.enpol.2017.07.018

9. Zhang, Y., Li, H. & Wang, S. Decarbonizing data centers through regional bits migration: a comprehensive assessment of China's “Eastern Data, Western Computing” initiative and its global implications. Appl. Energy 392, 126020 (2025). https://doi.org/10.1016/j.apenergy.2025.126020

10. Birahim, S. A. A net-grid-benefit test for interconnecting AI data centres. npj Environ. Soc. Sci. 1, 8 (2026). https://doi.org/10.1038/s44432-026-00013-5

11. Zhang, W. & Zavala, V. M. Remunerating space–time, load-shifting flexibility from data centers in electricity markets. Appl. Energy 326, 119930 (2022). https://doi.org/10.1016/j.apenergy.2022.119930

12. Dvorkin, V. Agent coordination via contextual regression (AgentCONCUR) for data center flexibility. Preprint at https://arxiv.org/abs/2309.16792 (2024).

13. Hu, Q., Sun, P., Yan, S., Wen, Y. & Zhang, T. Characterization and prediction of deep learning workloads in large-scale GPU datacenters. In Proc. Int. Conf. High Performance Computing, Networking, Storage and Analysis 1–15 (ACM, 2021). https://doi.org/10.1145/3458817.3476223

14. Jiangsu Provincial Development and Reform Commission. Notice on transmission–distribution and retail tariffs of the Jiangsu grid for 2020–2022, Su-Fa-Gai-Jia-Ge-Fa [2020] No. 1183, Annex 3 (2020). https://www.njqxq.gov.cn/qxqrmzf/qxqfzhggj/202011/P020201111396651530459.pdf

15. Gansu Provincial Development and Reform Commission. Notice on adjusting retail tariffs and optimising time-of-use tariffs, effective 1 January 2021 (2020). http://www.gansu.gov.cn/art/2020/12/3/art_10359_474921.html

16. Guizhou Provincial Development and Reform Commission. Notice on improving the time-of-use tariff mechanism, Qian-Fa-Gai-Jia-Ge [2023] No. 481 (2023). https://fgw.guizhou.gov.cn/zwgk/zcwj/zcwj/202306/t20230628_80566840.html

17. Du, B. et al. Spatial LLM workload shifting needs foresight: model commitment for AI data center operation under power grid constraints. Preprint at https://arxiv.org/abs/2609.09787 (2026).

18. Stojkovic, J., Zhang, C., Goiri, Í., Torrellas, J. & Choukse, E. DynamoLLM: designing LLM inference clusters for performance and energy efficiency. In Proc. IEEE Int. Symp. High-Performance Computer Architecture 1348–1362 (IEEE, 2025). https://arxiv.org/abs/2408.00741

19. Hersbach, H. et al. The ERA5 global reanalysis. Q. J. R. Meteorol. Soc. 146, 1999–2049 (2020). https://doi.org/10.1002/qj.3803

20. Zippenfenig, P. Open-Meteo.com Weather API. Zenodo https://doi.org/10.5281/zenodo.7970649 (2024).

21. Wu, H. & Kan, X. Hourly electric power load and transmission data at the provincial level in China. Zenodo https://doi.org/10.5281/zenodo.8322210 (2023).

22. Zhou, X. PyPSA-China: V3.0. Zenodo https://doi.org/10.5281/zenodo.13987282 (2024).

23. Potsdam Institute for Climate Impact Research. Data bundle PyPSA-China-PIK: rasters and basic cutout, v1.1. Zenodo https://doi.org/10.5281/zenodo.16810831 (2025).

24. Elsayed, A. A. E., Al-Obaidi, A. A. & Farag, H. E. Z. Characterization of high-resolution AI data center training workloads on single and multiple GPU nodes. Sci. Data 13, 1268 (2026). https://doi.org/10.1038/s41597-026-07496-6

25. MLCommons. MLPerf Inference v4.0 results. GitHub repository at commit 343c3d2cb03f2ae02b1023a44e4a45ba4b8422ef (2024). https://github.com/mlcommons/inference_results_v4.0

26. MLCommons. MLPerf Inference power measurement rules. https://github.com/mlcommons/inference_policies/blob/master/power_measurement.adoc (accessed 27 September 2026).

## Evidence register

E1. Revision stages 05–06 and service_replay_methods_draft.md: fixed-service construction and calendar-fixed temporal validation.

E2. Revision stage 07 and policy_attribution_methods_draft.md: 108-condition policy matrix, deterministic attribution bounds and Fig. 1.

E3. Revision stages 24–26 and demand_cohort_methods_draft.md: demand boundaries, analytical capacity counterexample and fixed-cohort controls.

E4. Revision stages 20–22 and mechanism_grid_methods_draft.md: information separation, procurement limits and commitment counterexample.

E5. Revision stages 18–19 and renewable_temporal_validation_methods_draft.md: annual and quarterly generation diagnostics.

E6. Revision stages 23 and 29–35 and asset_identity_methods_draft.md: technology, industrial boundaries and alias adjudication.

E7. Revision stage 36 and literature_20260927: current direct-literature registry, metadata checks, novelty matrix and claim–citation ledger.

E8. Revision stage 37 and mlperf_power_admission: pinned same-system performance, accuracy, MaxQ AC power, system-identity and admission audit.

The companion evidence index gives immutable repository links. These identifiers refer to research records, not peer-reviewed publications. Stages 36–37 verify the present bibliography, novelty boundary and the pinned public power extraction. Full-text checking remains incomplete for some literature entries, the literature audit is not systematic, and the MLPerf extraction does not create the missing standard-arm power measurement.

## Figure 1

![Conditional policy attribution](figures/fig1_policy_attribution.png)

**Figure 1. Service permissions change conditional GPU bill attribution.** Panel a reports symmetric allocations over feasible constructed policies. Panel b shows whether deterministic cost bounds identify an optimal majority. Each allowance contains 36 paired conditions; these are not independent statistical repetitions. Fixed background and assumed GPU idle power are included. The figure establishes neither whole-node savings nor provincial system cost or capacity value. Reproduced unchanged from revision stage 07.
