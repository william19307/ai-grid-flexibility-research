# Working methods: industrial captive generation and grid-interface accounting

Status: proposed model boundary informed by historical primary project evidence; not yet implemented in the provincial dispatch solver or validated against site measurements. See the stage-29 report and `captive_boundary/unit_admission_ledger.csv` for source qualification. No new provincial effect estimate is reported.

## Electrical boundary

For a single declared site meter boundary, let I and E denote public-grid import and export, L the non-generation site demand, A generator auxiliaries, and G_j gross generation. With all quantities in MW and consistently measured,

`I_t - E_t = L_t + A_t - sum_j G_j,t`.

Alternatively, use generation net of the same auxiliaries and remove A from the right-hand side. Mixed gross/net conventions are invalid. Distribution losses must be located explicitly within or outside this boundary. Import and export should reflect physical metering/contract rules, including any restriction on simultaneous transactions; no export assumption has been empirically admitted here.

A provincial gross-demand series may be balanced against captive generation if both include the same industrial activity and auxiliary boundary. A provincial series already net of that generation must not receive the same generation again. Reconstructing gross demand from net demand requires its historical captive output and the corresponding time resolution, rather than adding nameplate capacity. Unknown statistical scope is an unresolved input, not a license to select whichever convention improves the result.

## Shared process fuel

For one gas network and one calorific-value convention, use energy units for fuel flows Q and F and MWh for storage S:

`S_(t+1) = S_t + dt * (Q_produced,t - Q_process,t - sum_j F_j,t - Q_flared,t - Q_losses,t)`.

Gas availability is coupled to industrial production. Include storage limits, gas quality/mixing, allowable flaring, generator efficiency maps, minimum output, starts, ramps, maintenance and any heat obligations when evidenced. Multiple gas networks cannot be merged without justified compatibility and conversion. Historical documents describing retirement-to-backup or reduced output require explicit old/new equipment relationships, not independent addition of rated capacity. A methane combustion-turbine heat rate is not a substitute for a by-product-gas steam-cycle map.

## Response and emissions

For a declared feasible reference operation, interface response is

`R_t = (I_ref,t - E_ref,t) - (I_policy,t - E_policy,t)`.

This includes either reduced purchases or increased exports; neither is identified by nameplate capacity alone. Evaluate the entire delivery and recovery horizon with the same industrial service/production conditions, availability assumptions and gas-storage end condition. Do not claim firm capacity without relevant shortage hours, outages and a specified reliability criterion. Unknown export limits and firm response remain missing, not zero.

Emissions comparison must include the specified industrial process, alternative gas use/flaring, on-site combustion and displaced grid generation consistently. A historical project-appraisal regional average emission factor does not establish causal marginal savings for this study. Any proposed economic allocation of a co-product is distinct from its physical energy balance and must be declared.

## Required input record before operational admission

- Unique unit/project mapping: permit identifiers, unit numbering, capacity definition, commissioning/retirement and backup relationships with dates.
- Gross/net demand and generation meter boundary; timestamped site demand, auxiliary use and imports/exports; public-grid connection and contract limits.
- Process gas production/quality, competing uses, storage/flaring constraints and fuel-to-electricity map on the same basis.
- Heat/production service, start/ramp/minimum-output/availability data, and reproducible representative operating traces.
- Declared counterfactual, recovery/end-state rules and whether firm response or conditional energy shifting is estimated.

The stage-29 ledger is documentation only. It does not enforce these requirements in legacy entry points; legacy provincial runs remain prohibited as sources of revised empirical conclusions until a checked input bundle and model implementation are completed.
