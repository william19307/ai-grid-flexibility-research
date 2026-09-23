# Stage 21 design — frozen mechanism responses in fixed-capacity grids

2026-09-23. Exploratory mathematical integration; no provincial estimates or empirical preregistration.

1. Reconstruct task work, windows, resource fractions, service costs and power from each frozen response before passing mandatory nodal demand to the existing grid solver.
2. Forbid asset expansion and voluntary load shedding. Use identical grid data, initial states, horizon and information for all response evaluations. Do not select new offers or reschedule tasks after seeing grid outcomes.
3. Retain infeasible and unresolved grid solves. Compare resource costs only when the baseline and response both solve; report terminal minimum-time obligations separately.
4. Separate grid resource cost from bill/transfer accounting. Full-horizon dispatch has perfect foresight conditional on each frozen response; it is not online dispatch or a market equilibrium.
5. Test startup-cost and congestion effects with independent hand calculations. Crucially, check whether linear-forecast follower endpoints bound nonlinear grid cost. They must never be labelled physical best/worst without proof.
6. Verify a finite sweep of follower mixtures against a separately derived startup formula; do not call a sampled sweep a continuous global optimization.
7. Preserve original models and results. Re-run relevant pre-existing grid/commitment validation into a new directory.
