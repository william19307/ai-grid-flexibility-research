# Stage 33: retain unit technology and separate existing assets from investment

Design frozen before implementation/results. This is an input-staging boundary, not a rerun of the legacy provincial model or a claim of measured CCGT performance.

1. Read the already audited stage-23 cohort and preserve every original field and unique unit ID, with per-row and source hashes. Validate membership against the frozen 109-row source. No unsupported fuel or technology may silently become OCGT. No industrial record may disappear as zero capacity.
2. Separate technological category, CHP evidence and captive-use evidence. `not found` is unknown, not a no-heat assertion. A bare CCGT label does not establish an extraction-condensing or backpressure heat envelope. Preserve mixed industrial gas as a distinct fuel declaration.
3. Keep existing candidate stock separate from prospective investment options. Existing records do not acquire new-build permissions. An OCGT option has zero existing capacity and no presumed construction limit. Investment permissions/caps require an explicit scenario policy, not technology substitution in the installed stock.
4. Read the archive OCGT/CCGT/gas price, fuel intensity, efficiency, VOM, investment, FOM and lifetime with exact year/unit/source checks. Preserve archive descriptions including annual-average efficiency and heat coefficients. Report conditional arithmetic only; do not infer actual Chinese unit heat rates, gross/net power or dispatch.
5. Emit a complete machine-readable staging manifest, parameter provenance and missing-input requirements. Compilation as an empirically qualified fleet must reject unresolved heat, meter, fuel, chronology, availability and operating boundaries rather than silently drop entries or fill defaults. This stage does not create a field-data approval mechanism.
6. Independently reconcile technology/CHP/industrial subtotals, recompute energy and annualized cost formulas, and test duplicate/missing IDs, capacity changes, unknown technology, source hash changes and cost unit/year/duplicate errors. Keep expected rejection separate from solver infeasibility.

No province dispatch is authorized by this stage. Parameter sets remain conditional references; keep old manuscript and output files intact. Report remaining gaps and sync code, records and handoff to the revision branch.
