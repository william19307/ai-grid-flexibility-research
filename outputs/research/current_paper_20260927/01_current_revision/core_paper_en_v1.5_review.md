# Service constraints and power boundaries shape the grid value of flexible AI computing

William Wei¹ ² and Lanlan Liu³

¹ School of Computer Science, Faculty of Engineering and Physical Sciences, University of Leeds, Leeds, UK

² Spatial Computing (Fujian) Technology Co., Ltd., Fuzhou, China

³ School of Public Administration, Fujian Normal University, Fuzhou, China

Correspondence: qkfp0742@leeds.ac.uk

Revision v1.5 review edition | 27 September 2026 | Evidence consolidated through revision stage 35 (23 September 2026)

**Manuscript status.** This edition assembles the supported revision findings and methods. It is not submission-ready and does not replace the submitted v1.4. Provincial system-benefit estimates, annual firm-capacity results and implementable market comparisons remain to be recomputed. The title and abstract are provisional. Author details are retained from v1.4.

## Abstract

The value of flexible artificial intelligence computing depends on the service that must be preserved, the power boundary being measured and the electricity system that absorbs the response. We develop a framework that separates changes in operating mode from changes in job start time while retaining fixed work, GPU requirements and explicit completion benchmarks. In 108 paired conditions constructed from production traces, a fixed-start policy cannot slow jobs when no extra completion allowance is available; with longer allowances, mode changes account for a majority of the identified bill-reduction opportunity in most, but not all, conditions. These results concern a conditional GPU-power model rather than measured whole-node or grid savings. Two analytical counterexamples show why translation to grid value requires additional care: inconsistent cohort accounting can reverse a capacity conclusion, and linear response endpoints need not bound supply costs with unit commitment. Audits of renewable profiles and generating assets reveal further limits to inference from annual agreement or unique database identifiers. Together, the results establish a testable framework for evaluating service-preserving computing flexibility. A complete provincial estimate requires common-hardware power measurements, matched demand and generation boundaries, historical decision-time information and fixed-investment annual validation.

## Introduction

Flexible computing offers at least two decisions: how fast a job runs and when it starts. A lower-power mode can extend execution, while a different start time changes the load experienced by the grid. Calling one decision “efficiency” and the other “flexibility” does not by itself produce a physical decomposition of their value. The comparison also depends on the completion requirement, fixed background work, idle consumption, and the investment or dispatch decisions available to the electricity system.

Our research asks when each decision contributes to lower resource use and when firms have incentives to deliver the response. We distinguish four evidence levels: recorded workload and infrastructure observations; counterfactual schedules under explicit assumptions; mathematical properties of the electricity model; and empirical system outcomes. Agreement at one level does not certify the next. In particular, reconstructing a task allocation is not a measurement of its counterfactual electrical power, and solving representative weeks does not establish annual resource adequacy.

The present revision replaces an unconditional attribution claim with a service-dependent question. It brings the scheduling comparison, whole-node accounting, supply model and procurement information set into a common framework. The results below report the portions currently supported by the revision evidence. The former provincial benefit ranges and gas-capacity avoidance estimates remain historical scenario outputs and are not carried into this edition as revised findings.

## Results

### The completion benchmark changes the attribution

We retain the original GPU count and a work proxy equal to recorded GPU count multiplied by runtime. Every target job executes once in a continuous interval without preemption. Other recorded allocations remain fixed background. The completion benchmark is the historical end time plus an analyst-defined allowance of 0, 6 or 24 hours. This is a retrospective comparison, not a contractual service-level agreement inferred from queueing time [E1].

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

Feasible policy costs and relaxed lower bounds define deterministic identification intervals for the optimal attribution (Fig. 1). A mode majority in a constructed schedule does not establish a majority in the global optimum: five conditions remain unresolved. The bill includes fixed background and assumed idle GPU consumption; it is neither an actual customer bill nor a system-cost estimate. Historical tariff shapes are applied as declared hypothetical price conditions on the trace clock [E2].

There is a structural reason for the zero-allowance result. If recorded runtime defines full-speed work, every alternative mode is strictly slower, and the observed start and completion time are fixed, no slower mode can complete that work. Therefore C10 equals C00. For nested optimal policy sets with positive total savings, the symmetric mode attribution cannot exceed one half. The statement is specific to this decision matrix and work definition; it is not a universal bound on the contribution of hardware efficiency.

Across all tested conditions, 57 of 108 constructed joint policies have a higher hourly GPU peak than the reference, with a maximum increase of 11.37%, despite lower modeled GPU energy. These are synchronized cluster GPU peaks, not coincident system peaks or connection-capacity requirements. They demonstrate why energy reduction alone is insufficient to establish capacity value [E2].

### Fixed-service replay extends across time under stated assumptions

A separate calendar-fixed validation covers 12 cluster-week cohorts and 118,703 distinct job records across May, July and September 2020. Eight curve labels and three completion allowances produce 288 paired conditions. All constructed schedules passed independent raw-record work, window and event-capacity checks. The selected jobs account for 26.62–40.59% of recorded GPU occupation in the respective source weeks; the remaining occupation is preserved as background [E1].

All arms retain a 192-hour domain, including the observed tail after the source week. The successful replay validates a schedule under aggregate GPU capacity and assumed curve transfer. It does not establish device placement, network topology, output quality, actual service contracts, online control or whole-node energy savings. The additional periods validate a frozen construction after earlier trace inspection; they are not a new prospective deployment experiment.

### Accounting boundaries can reverse a capacity comparison

A controlled cohort must be added exactly once. If a supplied demand series already contains its reference consumption, the reference cohort must first be removed to construct a common background. Otherwise every policy carries an extra copy of the reference load, which may alter capacity and commitment decisions [E3].

A two-hour analytical example makes the consequence explicit. The observed total is [8, 8] MW, including a reference cohort [4, 0] MW. The controlled cohort is [0, 2] MW, so the common background is [4, 8] MW. Correct accounting gives a peak change from 8 to 10 MW. Adding both cohorts to the already inclusive total instead gives an apparent change from 12 to 10 MW. With an investment cost of 10 per MW and a variable cost of 5 per MWh, the correct cost comparison is 160 to 170, whereas the duplicated comparison is 220 to 190. The monetary units are arbitrary and the example is synthetic. It proves a possible sign reversal, not the size or sign of an error in the provincial manuscript.

The implemented ledger supports both genuinely incremental and already embedded cohorts, preserves a common background and rejects incompatible clocks or negative reconstructed background. Four complete certified task-policy trajectories have entered the grid interface over all 192 hours. Their whole-node conversion and 3 MW background remain explicit test assumptions rather than calibrated Jiangsu demand [E3].

### Linear procurement bounds do not bound nonlinear supply costs

The revised mechanism comparison separates information available when a response is purchased from outcomes evaluated later. Fixed responses enter the same grid model with the same installed assets and background demand. Commitment and dispatch can change in response to load, but the response is not reselected after seeing the realized system outcome [E4].

A continuous-response counterexample shows that the endpoints minimizing and maximizing a linear forecast objective need not bracket actual supply costs. If recovery can occur in either of two hours, each requiring a different initially offline generator, an endpoint activates one generator while an interior split activates both. With zero variable cost and a startup cost of 10 per generator, both endpoints cost 10 and all interior splits cost 20. These are synthetic units chosen for the proof. Evaluating only linear extremes can therefore miss the physical worst case when commitment is endogenous.

This result limits what can be concluded from the former event-contract comparison. A failed event rule does not show that event procurement is generally inferior. General pessimistic procurement over the full response set, an implementable selection rule, historical forecast vintages and strategic-provider behavior remain unresolved. Ex-post prices derived from the coordinated solution remain a benchmark, not evidence of a deployable tariff [E4].

### Physical supply inputs require more than aggregate agreement

An exploratory offshore-wind diagnostic holds a 2022 annual calibration fixed and compares later company disclosures with modeled generation. In 2023, the NREL reference shape has an annual error of −0.551%, while the sum of absolute quarterly errors equals 13.075% of annual observed generation. The annual total hides offsetting seasonal errors. The reported scope is company-controlled offshore generation; its assignment to the H2 proxy remains an evidence-based inference, and the quarterly series is not hourly meter data [E5].

An inventory audit also separates record identity from physical asset identity. The selected oil/gas cohort initially comprises 109 source rows totaling 24,959 MW. Technical fields identify 97 combined-cycle records and 12 industrial by-product-gas steam-turbine records; applying one OCGT parameter set to all of them is unsupported. Two Funing entries share the same project source and match the operator's two-unit description. An explicit research alias adjudication maps the four rows to two candidate assets, giving 107 candidates totaling 24,759 MW. Original identifiers and metadata conflicts are retained [E6].

The revised view contains 95 CCGT candidates, including 80 reported CHP candidates and 15 with unresolved heat-service status, plus 12 industrial candidates. It is not a verified 2030 operating fleet. Heat obligations, industrial fuel sharing, net grid interfaces, commissioning and retirement, and unit operating limits still require evidence. Neither the 200 MW accounting correction nor a small annual renewable error can be converted directly into a corrected system-benefit percentage.

## Discussion

The supported conclusion is that attribution and system value depend on explicitly defined service, power and supply boundaries. Under the tested decision rights, the apparent contribution of mode choice changes with the completion allowance. Energy savings can coincide with a higher GPU peak, and a mathematically feasible task response can have an unfavorable grid consequence once recovery and commitment are represented. These findings motivate measurement and experimental design; they do not yet quantify the grid value of deployed AI clusters across the three provinces.

A complete empirical claim requires the same useful work and quality to be executed on common hardware while measuring idle, active and transition energy at a defined AC boundary. The demand series must identify whether the treated cohort is already included. Generation and transmission data must represent compatible vintages, fuel and heat obligations, water and storage balances, and physically available imports. Mechanisms must receive comparable information and be assessed against realized outcomes without retrospective choice.

The remaining system study should select investment once on a declared training information set, then operate that fixed portfolio through complete held-out periods, including failures, correlated outages, extreme conditions and unfinished terminal obligations. Previously inspected weather years cannot become an untouched test set merely by being downloaded again. Until this chain is completed, the former provincial reduction ranges, gigawatts of avoided generation and price-performance claims should remain in the historical submission rather than in a revised abstract.

## Methods overview

The supplementary review edition specifies the fixed-service cohort, policy objective, deterministic bounds, common-horizon power accounting, demand ledger and grid interfaces. Mathematical verification uses independent event scans, analytical cases, enumeration or scalar arithmetic where appropriate. Source validation records dates, scope, original identifiers, file hashes and unresolved interpretations. A hash demonstrates version identity, not source accuracy.

Current code includes unit commitment, energy-conserving storage and reservoirs, shared industrial fuel and a private-site grid interface, fixed-cohort demand construction and conditional mechanism evaluation. These components have mathematical checks, but they have not been assembled into a fully calibrated provincial experiment. Reported check counts are implementation coverage, not scientific sample sizes or evidence of journal readiness.

## Data and code availability

The research repository is https://github.com/william19307/ai-grid-flexibility-research, branch codex/research-evidence-revision. This edition is based on evidence commit f4bd66b564e50d0a7e30d5f4cca6ebe522b5df33. The package includes an evidence index and source-file hashes. External raw archives, prepared arrays and local environments require restoration through REPRODUCE.md; cloning alone does not reproduce the entire study. No new hardware measurements are claimed.

## Evidence register

E1. Revision stages 05–06 and service_replay_methods_draft.md: fixed-service construction and calendar-fixed temporal validation.

E2. Revision stage 07 and policy_attribution_methods_draft.md: 108-condition policy matrix, deterministic attribution bounds and Fig. 1.

E3. Revision stages 24–26 and demand_cohort_methods_draft.md: demand boundaries, analytical capacity counterexample and fixed-cohort controls.

E4. Revision stages 20–22 and mechanism_grid_methods_draft.md: information separation, procurement limits and commitment counterexample.

E5. Revision stages 18–19 and renewable_temporal_validation_methods_draft.md: annual and quarterly generation diagnostics.

E6. Revision stages 23 and 29–35 and asset_identity_methods_draft.md: technology, industrial boundaries and alias adjudication.

The companion evidence index gives immutable repository links. These identifiers refer to research records, not peer-reviewed publications. The complete historical bibliography is retained with v1.4; a final literature review and citation audit remain required before submission.

## Figure 1

![Conditional policy attribution](figures/fig1_policy_attribution.png)

**Figure 1. Service permissions change conditional GPU bill attribution.** Panel a reports symmetric allocations over feasible constructed policies. Panel b shows whether deterministic cost bounds identify an optimal majority. Each allowance contains 36 paired conditions; these are not independent statistical repetitions. Fixed background and assumed GPU idle power are included. The figure establishes neither whole-node savings nor provincial system cost or capacity value. Reproduced unchanged from revision stage 07.
