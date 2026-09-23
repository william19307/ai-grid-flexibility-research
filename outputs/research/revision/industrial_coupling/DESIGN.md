# Stage 31 design: shared process gas and a captive electrical interface

Frozen before implementation/results. This adds the stage-29 accounting boundary to the existing coupled-grid model. No measured parameter set is currently qualified; every numerical validation below is synthetic and labelled as such. It does not replace the province input bundle or submitted manuscript.

## Model contract

- A site is an explicit private electrical node and one lossless signed grid interface. Imports are positive, exports negative; finite, scenario-specific limits apply to each direction. Ordinary lines cannot bypass the interface. The site's declared gross process demand excludes generator auxiliaries and is mandatory, even when other grid demand may be shed.
- Existing generators at a site must all belong to its declared single, common-calorific-basis gas system. No new captive capacity is optimized. Their electrical ratings and dispatch are gross. Variable, online and start-event auxiliary electricity is deducted from gross output at the site balance.
- Each generator has an affine fuel relation: heat-rate times gross output, plus explicit online fuel and start-event fuel. Online/start terms require the existing commitment model. All six fuel/auxiliary coefficients must be explicitly supplied; unknown is not zero.
- Fuel production, other process use, flare limits and grid-interface limits cover every scenario and hour. A finite gas store conserves fuel energy, obeys charge/discharge limits and ends at its initial energy. Gas mixes, pressure, gas-network transport and heat-service coupling are not inferred.
- Count generator-fuel combustion, flaring and the supplied other-process-use emission coefficient within the declared gas boundary. Captive `Generator.emissions_t_per_mwh` must be zero to avoid double counting. Generator marginal cost is declared non-fuel operating cost; separate generation-fuel-use and flare costs are explicit. Upstream production/chemical process emissions and process fuel cost are outside the reported incremental cost boundary.
- Empty industrial-site input must retain previous solver behaviour and result schema. New runs write only the stage directory.

## Before/after comparisons and independent verification

1. Two captive units compete for one fuel stream: the higher-efficiency unit is dispatched first, and neither can exceed the shared hourly or horizon fuel budget. Compare with the existing unconstrained case and report both.
2. Gross versus net generation: auxiliary electricity increases required grid imports by a hand-calculated amount. A zero export limit still permits reducing grid purchases, and positive export is capped.
3. Gas storage shifts surplus to a later shortage with explicit terminal restoration and rate limits. Reducing its rate must alter imports as predicted; insufficient process fuel or zero flare capacity can make a case infeasible.
4. Integrate startup/no-load fuel and auxiliary energy with existing commitment at one-hour and half-hour time steps, with hand-computed event energy and emissions. Test a binding emissions limit and a lower infeasible limit.
5. Reconstruct each accepted solution independently from returned flows: site and grid electricity, affine fuel, gas stock changes, interface/storage bounds, fuel cost and emissions, including scenario probabilities. Do not rely only on optimizer residuals.
6. Reject inconsistent meters, unknown/multiple unit ownership, interface bypass, capacity expansion, duplicate emission accounting, missing/nonfinite/negative inputs, and online/start coefficients without commitment.
7. Run the existing grid, commitment and reservoir validation suites into separate directories. Compare no-site results where stable numeric outputs permit; no frozen result file may be overwritten.

Report every prespecified case and failure. Passing these checks proves the stated mathematical implementation, not industrial flexibility, firm capacity, a real fuel curve or provincial benefit. Empirical admission remains subject to site data and unit identity, heat/process service and net purchase/export evidence.
