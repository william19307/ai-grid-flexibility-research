# From technical flexibility to realised power-system value in AI computing: service constraints, recovery limits and incentives in China's compute–power coordination

**Working English draft v0.3 (2026-09-15). Structure follows a Nature Energy Article. Every bracketed item `[PENDING: ...]` marks a result that does not yet exist; no number in this file may be cited until the corresponding evidence tier in `论文工作稿` is "regional result" or higher.**

## Abstract (≤150 words, to be written last)

`[PENDING: one-sentence problem; what we did (task-level service constraints + joint planning + firm behaviour + mechanism); headline quantitative finding from calibrated regional runs; policy implication.]`

## Main

AI computing load can modulate power and shift execution in time, and grid-interactive operation of AI clusters has been demonstrated experimentally [1]. Whether such technical capability translates into power-system value depends on three links that are usually studied separately: the service constraints under which tasks must still complete, the system conditions that give shifted energy any value, and the incentives that make an operator deliver what it technically could. We connect the three in a single framework and quantify, for Chinese provincial systems, how much of the technical flexibility envelope becomes realised system value under (i) rigid operation, (ii) autonomous firm optimisation against tariffs and (iii) system-coordinated operation, and what verifiable commitment and compensation designs narrow the gap.

### Service constraints bound the power envelope

`[Fig. 1a: measured GPU power–throughput modes (Colangelo et al. re-analysis, 8 configurations × 6 caps). Fig. 1b: observed scheduling wait and run-time distributions from three public production traces (Helios, Alibaba PAI, Philly), GPU-hour weighted. Fig. 1c: task-conserving response envelope vs. relaxed-window upper bound.]`

Text points established so far: throughput-conserving power reduction of 11–29% at ≥90% throughput exists in measured configurations; production traces show that most GPU-hours sit in jobs longer than one day (Helios 68%, Alibaba 30%) while observed queueing waits exceeding one hour cover 18% of GPU-hours in Helios and ~0% in Alibaba; these waits are lower bounds on tolerated delay, not deadlines. `[PENDING: calibrated deadline distributions by workload class; recovery/checkpoint costs.]`

### Value of flexibility depends on system slack, not on flexibility alone

`[Fig. 2: incremental system cost and emissions per AI MWh under S0/S0b/S1/S2 for three calibrated provinces, 2030 main scenario, multiple weather years.]`

Public-data 2030 scenario (documented assumptions; hourly load shape not independently validated; see Methods): when interprovincial exchange is represented by an unconstrained external market at a fixed price, the rigid-to-coordinated gap in incremental system cost per AI MWh is below 1% in all three provinces, i.e. the exchange proxy removes local scarcity. With exchange constrained, the gap is 1–2% in Gansu (wind/solar-rich, coal-heavy), 8–11% in Guizhou (hydro–renewable mix) and 2–15% in Jiangsu, rising with the AI share of peak. At an AI share of 20% of the 2030 Jiangsu peak, rigid operation requires 8518 MW of new gas peakers and 1950 MW of batteries, whereas system-coordinated operation requires 1103 MW of gas (0 MW with longer deadlines) and no batteries. `[PENDING: validated hourly load; multi-province network; unit commitment; multi-weather adequacy.]`

### Decomposing the delivery gap

`[Fig. 3: gap decomposition.]` Firm-autonomous operation under official provincial time-of-use tariffs realises a province-dependent share of the coordination value: roughly 40–80% in Gansu, 10–40% in Guizhou and near 100% in Jiangsu at AI shares of 5–10% but only 30–80% at 20%. In Guizhou the tariff's valley (00:00–08:00) does not coincide with the system's surplus hours, so autonomous shifting can even raise system cost relative to rigid operation. Longer deadline slack lowers coordinated cost substantially but improves autonomous outcomes much less, because the tariff gives firms no reason to use the extra slack.

### Incentives that close the gap

`[Fig. 4: commitment–compensation frontier.]` A first event-based commitment mechanism (events = the top 5% hours whose marginal cost exceeds the weekly median by more than 20%; the firm commits the maximum deliverable reduction relative to its own autonomous schedule and is compensated at least its opportunity cost) yields zero or negative system savings relative to autonomous operation in most settings while its compensation floor is positive, and leaves the gap to coordinated operation essentially unchanged. Coordination value arises from continuous intra-day shifting and avoided investment, not from a few event hours; event-based demand-response contracts therefore capture only a small fraction of it. When the firm instead optimises against the shape of the system's own hourly marginal cost (the dual prices of the coordinated solution, rescaled to the tariff's mean level), its outcome is within 3.14% of the coordinated optimum in every setting, with either exchange representation. The delivery gap is therefore almost entirely a property of the price signal the firm faces, not of autonomous operation as such. Replacing the fixed-price external market by an aggregate node of directly connected provinces (their own load, GEM 2030 fleets and renewables) restores local scarcity: with exchange allowed, rigid-to-coordinated gaps become 0.8–1.0% in Gansu, 0.1–0.2% in Jiangsu and 0.4–0.8% in Guizhou. `[PENDING: validated hourly load; explicit multi-node network; verification and baseline rules for continuous signals.]`

### Robustness and transferability

`[Fig. 5: multi-weather years, outage samples, external test system.]`

## Methods

- Task–power model: batch arrivals, deadlines, measured modes, idle power, backlog conservation (implemented; see `联合模型方法与验证_v0.1`).
- Joint planning–operation LP with shared investment, chronological dispatch, transport network with losses, storage, water-conserving cascades (implemented; 118 + 74 verification checks).
- Regional inputs: 2020 base year, official annual anchors; peak-load plausibility check against public reports: Jiangsu consistent (>100 GW), Gansu anchored peak ~11% above the 2021 official peak, Guizhou anchored peak above the 2026 record, so the 2018-derived hourly shape overstates peak-to-mean ratios in Gansu and Guizhou and biases scarcity upward. `[PENDING: validated hourly shapes, reconciled capacities and vintages]`.
- Scenarios S0/S0b/S1/S2/S3 and metrics (equal service, equal reliability, system cost, investment, emissions, delivery gap, participation).
- Data and code availability: registry `data_registry.csv`; all public sources with checksums.

## References (to be completed)
1. Colangelo et al., Nature Energy (2025/2026). 2. Zhang & Zavala, Applied Energy 2022. 3. Knittel, Senga & Wang, iScience 2026. 4. Zhang, Li & Wang, Applied Energy 2025. 5. Dunlap et al., preprint 2026. 6. Weng et al., NSDI 2022. 7. Hu et al., SC 2021. 8. Jeon et al., ATC 2019. 9. Stojkovic et al., HPCA 2025.
