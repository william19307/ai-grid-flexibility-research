# From technical flexibility to realised power-system value in AI computing: service constraints, recovery limits and incentives in China's compute–power coordination

**Working English draft v0.1 (2026-09-15). Structure follows a Nature Energy Article. Every bracketed item `[PENDING: ...]` marks a result that does not yet exist; no number in this file may be cited until the corresponding evidence tier in `论文工作稿` is "regional result" or higher.**

## Abstract (≤150 words, to be written last)

`[PENDING: one-sentence problem; what we did (task-level service constraints + joint planning + firm behaviour + mechanism); headline quantitative finding from calibrated regional runs; policy implication.]`

## Main

AI computing load can modulate power and shift execution in time, and grid-interactive operation of AI clusters has been demonstrated experimentally [1]. Whether such technical capability translates into power-system value depends on three links that are usually studied separately: the service constraints under which tasks must still complete, the system conditions that give shifted energy any value, and the incentives that make an operator deliver what it technically could. We connect the three in a single framework and quantify, for Chinese provincial systems, how much of the technical flexibility envelope becomes realised system value under (i) rigid operation, (ii) autonomous firm optimisation against tariffs and (iii) system-coordinated operation, and what verifiable commitment and compensation designs narrow the gap.

### Service constraints bound the power envelope

`[Fig. 1a: measured GPU power–throughput modes (Colangelo et al. re-analysis, 8 configurations × 6 caps). Fig. 1b: observed scheduling wait and run-time distributions from three public production traces (Helios, Alibaba PAI, Philly), GPU-hour weighted. Fig. 1c: task-conserving response envelope vs. relaxed-window upper bound.]`

Text points established so far: throughput-conserving power reduction of 11–29% at ≥90% throughput exists in measured configurations; production traces show that most GPU-hours sit in jobs longer than one day (Helios 68%, Alibaba 30%) while observed queueing waits exceeding one hour cover 18% of GPU-hours in Helios and ~0% in Alibaba; these waits are lower bounds on tolerated delay, not deadlines. `[PENDING: calibrated deadline distributions by workload class; recovery/checkpoint costs.]`

### Value of flexibility depends on system slack, not on flexibility alone

`[Fig. 2: incremental system cost and emissions per AI MWh under S0/S0b/S1/S2 for three calibrated provinces, 2030 main scenario, multiple weather years.]`

Smoke-test observation (uncalibrated, not citable): in a coal-slack provincial system with no surplus hours the four scenarios coincide; in a hydro–renewable-mixed system the rigid-to-coordinated gap is several percent of incremental cost and avoided peaker investment appears only when export is constrained. `[PENDING: calibrated results.]`

### Decomposing the delivery gap

`[Fig. 3: gap decomposition — efficiency-mode effect (S0→S0b), temporal shifting under tariffs (S0b→S1), coordination (S1→S2); dependence on deadline length W, spare capacity, tariff structure and interconnection.]`

### Incentives that close the gap

`[Fig. 4: commitment–compensation frontier; participation condition; delivered vs. committed reduction under verification rules; cost bearers.]`

### Robustness and transferability

`[Fig. 5: multi-weather years, outage samples, external test system.]`

## Methods

- Task–power model: batch arrivals, deadlines, measured modes, idle power, backlog conservation (implemented; see `联合模型方法与验证_v0.1`).
- Joint planning–operation LP with shared investment, chronological dispatch, transport network with losses, storage, water-conserving cascades (implemented; 118 + 74 verification checks).
- Regional inputs: 2020 base year, official annual anchors, `[PENDING: validated hourly shapes, reconciled capacities and vintages]`.
- Scenarios S0/S0b/S1/S2/S3 and metrics (equal service, equal reliability, system cost, investment, emissions, delivery gap, participation).
- Data and code availability: registry `data_registry.csv`; all public sources with checksums.

## References (to be completed)
1. Colangelo et al., Nature Energy (2025/2026). 2. Zhang & Zavala, Applied Energy 2022. 3. Knittel, Senga & Wang, iScience 2026. 4. Zhang, Li & Wang, Applied Energy 2025. 5. Dunlap et al., preprint 2026. 6. Weng et al., NSDI 2022. 7. Hu et al., SC 2021. 8. Jeon et al., ATC 2019. 9. Stojkovic et al., HPCA 2025.
