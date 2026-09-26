# Working methods: common-horizon energy and service admission

Status: conditional accounting argument and reanalysis of published means, not a new hardware experiment. This is an elementary accounting identity, not a claim of methodological novelty. It does not establish operational service compliance or power-system value.

Consider one fixed useful-work request executed on the same node with the same resource allocation and independently verified quality. Let the reference use total active energy E_r and time T_r, and the controlled mode use E_m and time T_m, with T_m >= T_r. All energies below are measured at the same whole-node AC boundary. Both policies start at the same time and finish within a common observation horizon H. After completion both enter the same constant idle state with power P_0 >= 0. No later work, shutdown or facility-cooling response is credited. Returning the controlled device to that common state must be included in measured overhead.

If additional, non-double-counted control overhead has energy K >= 0 and duration tau >= 0, the controlled total is

`E_total,m = E_m + K + P_0 (H - T_m - tau)`.

The reference total is `E_total,r = E_r + P_0 (H - T_r)`. These expressions use joules, watts and seconds throughout. Their difference is

`Delta E = E_r - E_m - K + P_0 (T_m + tau - T_r)`.

Consequently `E_r - E_m > K` suffices for positive energy reduction for every common nonnegative idle power, provided `T_m + tau <= H`. Unknown idle power need not prevent identification of the sign under these assumptions, although it still prevents an exact percentage estimate. If controlled and reference idle states differ, the cancellation fails. If an earlier finish permits shutdown or additional useful work, a different counterfactual is required. A time-varying price or power-system objective cannot be replaced by this energy difference.

For measured uncertainty intervals, a conservative sufficient condition is `E_r,lower - E_m,upper > K_upper` and `T_m,upper + tau_upper <= H`, along with nonnegative runtime difference throughout the uncertainty set. Every bound must have a documented interpretation. Bounds due only to table rounding are not confidence intervals, prediction intervals, instrument calibration bounds, or worst-case execution times. A mean runtime below a deadline does not certify an individual-run or tail-latency service requirement.

For a relative reference window `H = (1 + delta) T_r`, printed values rounded to 0.01 s and 0.01 kJ yield the conditional margins

`tau_margin = (1 + delta)(t_r - 0.005) - (t_m + 0.005)` seconds,

`K_margin = 1000[(e_r - 0.005) - (e_m + 0.005)]` joules.

The rounding convention is an explicit assumption, not a publisher-certified uncertainty model. The self-comparison reference is treated as the same quantity with correlated error, not two independent rounded measurements. At K = K_margin the worst-case energy difference is zero, so strict benefit requires K < K_margin. The margins concern reported means only. They cannot authorize production admission until variability, control transitions, quality and the actual service contract are measured.

We apply this screening to the same-node table published by [Koszczal et al.](https://link.springer.com/chapter/10.1007/978-3-031-48803-0_1). We keep activity counts separate and do not transfer their hardware to the original GPU-only curves. All 17 measured control points are retained per group. At each of seven declared reporting windows, we select the feasible printed-mean candidate with the largest rounding-adjusted energy margin. This exploratory rule is explicit; it is not a data-independent test or an optimum under a measured idle power. Numerical output and exact decimal endpoint checks are archived in `power_admission/`.
