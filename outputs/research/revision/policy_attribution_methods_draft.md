# Fixed-service policy attribution — working manuscript section

Status: method and analytical claim draft. Conditional GPU tariff-bill attribution; not a new estimate of power-system value or a deployment experiment.

## A common task set and two explicit decision rights

All cells retain the same production cohort, work proxy, original GPU count, completion benchmark and immutable background allocations. Every job executes once in a continuous interval on its complete GPU gang. The cells differ only in whether they may choose a speed mode and whether they may change the observed start time. C00 retains the observed start and full reference speed. C10 permits a mode change while retaining that start; its end time can change. C01 permits start changes at full reference speed. C11 permits both choices. C10 is therefore a fixed-start policy, not an assertion that the physical load timing is unchanged.

All cells minimize the same GPU tariff-bill functional and have the same complete retrospective information about arrivals, background allocations, capacities and prices. A price path imported from the joint optimum is not supplied to only one cell. Historical tariff shapes are hypothetical relative-price conditions applied to the trace clock; they do not establish cluster geography, applicable historical customer tariffs or real-time market prices. The comparison does not remove foresight or certify online deployment.

The normalized power boundary is the same in all cells: idle GPUs consume 0.10 of full-reference GPU power, background allocations consume full-reference power, and target allocations follow the selected curve. The constant idle/background contribution is included in total-bill and energy denominators and cancels from absolute policy differences. There is no whole-node or cooling calibration in this experiment.

## Feasible policy costs and bounds on optimal capability value

The constructive algorithm retains reservations for every other job and improves one whole job at a time, in observed-start order. C10 and C01 each use one sweep from C00. C11 uses one sweep from the cheaper parent policy. Accepting only strict improvements keeps each result feasible and prevents an expanded policy from discarding an already available lower-cost parent. This construction is a declared heuristic, not a solver certificate of global optimality. Its seed and one-sweep search procedure remain part of the policy definition.

For a job and a mode, feasible start intervals are continuous blocks with sufficient unreserved capacity. Under a piecewise-constant price, the interval bill is F(s+d)−F(s), where F integrates price and d is the mode-dependent runtime. Candidate minima occur at feasible-block endpoints, price breakpoints, or price breakpoints shifted by −d. Enumerating these points gives an exact single-job update for the current reservations. It does not resolve the combinatorial order dependence across jobs.

Separately, each job is optimized with shared-capacity competition removed but with its original GPU count, non-preemption, speed restriction, release, completion benchmark and fixed-start restriction where applicable. Summing these independent minima provides a lower cost bound L_ab; the feasible schedule supplies an upper bound U_ab. The reference C00 is exact. These bounds retain the same job-mode model and objective as the corresponding cell.

For reported feasible policies, the symmetric mode allocation is M = [(C00−C10)+(C01−C11)]/2; the start-time allocation is T = [(C00−C01)+(C10−C11)]/2. They add to C00−C11. We report both orders and their interaction. This is an allocation under the defined policy matrix, not a unique physical division of energy and flexibility.

For globally optimal capability values, the unknown cell costs lie between L and U and obey the nested feasible-set inequalities C11 ≤ C10,C01 ≤ C00. A linear-fractional optimization finds the extrema of the mode share M/(C00−C11) over this bounded cost region. A Charnes–Cooper transformation yields two small LPs, independently checked by enumerating the cost-region vertices. The resulting interval is a deterministic identification bound conditional on the model, not a confidence interval. It can differ from the allocation over constructed policies, which is a different object. A broad interval means the evidence does not identify a precise optimal contribution share.

## A service-boundary result independent of the scheduling heuristic

Suppose the baseline job uses g GPUs for duration d at the unique full-reference mode q=1, all other available modes satisfy q<1, and its work proxy is W=gd. If its start is fixed and its completion benchmark is its historical end with zero extra allowance, any slower mode requires W/(gq)>d. It is infeasible. Consequently C10=C00 for this matrix, regardless of price and shared-capacity competition. Slowing a job then requires an earlier start (if its release and capacity permit it) and the value arises only after that decision right is available.

For globally optimal nested cells with positive total savings, 0≤C01−C11≤C00−C11. Therefore the symmetric mode share is at most one half. If full-speed start changes cannot reduce the bill either—for example, a flat price with the same completed work—both single-decision gains are zero and any joint gain is split equally by the symmetric allocation. These are algebraic properties of this matrix, not evidence that modes contribute at most one half under every service standard or policy definition. They specifically show why allowing start changes inside an “energy-only” reference alters what its attributed value means.

The result depends on the assumed full-speed runtime as the work reference. It does not describe a job with unused speed headroom, another full-throughput lower-power mode, mode-dependent output quality or unmeasured useful-work changes. Real service contracts and common-hardware power/throughput measurements remain necessary before transferring this claim to deployed systems.
