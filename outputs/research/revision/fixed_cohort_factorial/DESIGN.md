# Stage 26: frozen fixed-cohort factorial diagnostic

2026-09-23. Freeze this design before computing outputs. This is an input-control and solver-integration diagnostic, not provincial capacity or reliability evidence.

## Inputs and factors

- Three previously certified `Earth_ft_llama_8b_dolly_6_{Jiangsu,Gansu,Guizhou}` cases. Retain all four policies and the full 192-hour clock, including recovery and untargeted work. Province labels are scenario pairings, not cluster locations.
- Read the existing `load_2020_annual_anchored_hourly_shape_UNVALIDATED.npz` as an explicitly unvalidated background scenario. The cohort is assumed incremental; actual inclusion is unknown. No 2030 growth or official peak fitting.
- Select the exact 192-hour case window, then form B_alpha = mean(B) + alpha*(B-mean(B)), alpha in {0, 0.5, 1}. These preserve each node's **window** energy, not an annual calendar experiment. They are imposed perturbations, not estimates of forecast uncertainty.
- Independently choose integer synchronous cluster replicas R in {1, 1000}, assumed full-active power 0.5 kW/GPU and node idle ratio 0.41. Never derive R or power from background peak, energy, or alpha. Both replica levels are illustrative, not estimated regional adoption.
- Keep task certificates and electrical conversion invariant across shapes at fixed R. Keep each background invariant across policies and R. NO_COHORT removes the complete electrical cluster, including idle and untargeted work.

## Prespecified verification and reporting

Build 3 x 3 x 2 = 18 ledgers with four policies each. Store factor and source hashes, all five demand metrics (four policies plus NO_COHORT), paired differences and interaction contrasts. A cohort hash must be identical across alpha at fixed case/R, and the R=1000 curves must equal 1000 times R=1, independently of alpha. All backgrounds have the same energy within their case, and all clocks have 192 hours.

Use an artificial single-node expandable generator, zero existing capacity, capacity upper bound above every supplied demand, capacity cost 10 and marginal cost 5 in arbitrary diagnostic monetary units, with zero unserved energy. Compare 72 policy solves to the independent formula K=max(B+A), C=10*K+5*sum(B+A). This is a 192-hour perfect-foresight mathematical check; no annualization, real fleet, uncertainty, or physical reserve inference. NO_COHORT's analytic demand metrics are reported without an extra solve.

Reject mismatched clocks/nodes, negative or nonfinite shape parameters, nonfinite/negative backgrounds, duplicate/invalid replicas, changed ledger hashes and truncated certified trajectories. Check that infeasible expansion limits remain infeasible and that returned input mutation cannot alter the frozen ledger. Run the existing cohort validation as regression.

All selected cases and all factor cells must be reported, including failures; no selection on benefit sign. No hypothesis-test p-values or independent-sample claims. Fixed-cohort sensitivity may differ from the legacy confounded experiment, but this diagnostic will not estimate the old paper's numerical bias or replace its provincial results.
