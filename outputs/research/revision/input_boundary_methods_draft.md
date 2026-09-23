# Input-boundary reconciliation — methods working draft

This is a source-audit and revision specification, not a replacement description of an already executed provincial experiment.

## Technology and vintage

We reconstructed the legacy fleet selection without rerunning its optimization: units recorded as operating or under construction, with a known start year no later than 2030 and no recorded retirement by 2030. All 18 province–technology aggregates matched the frozen input table. The criterion describes a conditional scenario assembled from the July 2025 inventory; a missing retirement date does not establish availability in 2030. Planned commissioning, replacements, retirement and coverage require separate treatment. Capacity thresholds alone do not make the selected stock a rigorous lower bound on actual 2030 capacity.

The legacy mapping collapsed the entire oil/gas category into open-cycle gas turbine parameters. In the selected three-province inventory, 97 units (23,834 MW) are labelled combined cycle with natural gas or LNG fuel, and 12 units (1,125 MW) are steam turbines using industrial by-product gas. Of the 109 units, 82 (17,853 MW) are labelled CHP; industrial-use and CHP fields may overlap. Unknown heat obligations are not zero obligations. Technology, fuel, heat coupling and export rights must remain separate input dimensions. The unit-level candidate table preserves these labels and does not certify operational availability.

Using only the archived scenario cost table, OCGT efficiency 0.41 versus CCGT efficiency 0.58 yields marginal fuel-plus-variable costs of 53.5244 versus 38.8552 EUR/MWh and fuel emissions of 0.487805 versus 0.344828 tCO₂/MWh. These are conditional parameter comparisons, not measured plant performance or estimated biases in total system benefits. Industrial by-product gas requires its own fuel and process boundary. Investment and dispatch must be recomputed jointly after input admission.

## Demand cohort

Let Aᵖ be the electrical trajectory of one fixed treated workload cohort under policy p, including its defined idle, auxiliary and recovery boundaries. For a genuinely incremental cohort, the background B must explicitly exclude that cohort and total demand is Dᵖ = B + Aᵖ. If a reference total L already contains this cohort under reference execution r, define B = L − Aʳ once, and use Dᵖ = B + Aᵖ for all policies. The reference must reconstruct L and background demand must remain nonnegative. A negative residual identifies incompatible inputs; it must not be clipped. Efficient trajectories must not be renormalized to the original energy total.

The no-treated-cohort counterfactual is B. It is not a no-AI economy unless cohort coverage is established. A nameplate ratio A_full / max(B) is distinct from annual energy share and from the AI contribution to the coincident system peak. Each quantity requires an explicit denominator and common hourly boundary.

The legacy 2030 growth multipliers preserve normalized hourly shapes. Annual all-society consumption must first be reconciled with dispatch demand, including plant own-use and losses. Archived renewable capacity and the GEM candidate stock have different coverage and vintages; their difference is not an identified capacity gap.

## Network and evidence limits

An interconnector capacity does not establish exporting-system surplus. The legacy fixed-price external generator and high-cost neighbour backstop each allow 10,000,000 MW of notional generation, subject to the modeled network. These are boundary assumptions, not observed adequacy. Revised studies require simultaneous sending- and receiving-system balances, explicitly bounded backstops and correlated weather/outage scenarios.

Independent OOXML extraction checked 1,417 fields for the selected oil/gas units against the spreadsheet-reader extraction. The audit checks source transcription and legacy selection; it does not establish physical completeness, operational parameters or any new provincial outcome. The submitted manuscript and frozen results remain unchanged.
