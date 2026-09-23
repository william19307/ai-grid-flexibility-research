"""Explicit cohort accounting, not authentication of empirical demand scope.

No shifting, filling, clipping, task editing or energy normalization occurs here.
The verified bridge verifies schedules; its facility-power mapping remains assumed.
"""
import copy
import hashlib
import json
import numpy as np
import pandas as pd
from coupled_grid_compute import Scenario
from verified_power_bridge import load_verified_case, convert_power


def fingerprint(x):
    return hashlib.sha256(json.dumps(x, sort_keys=True, allow_nan=False).encode()).hexdigest()


def reconcile_demand(input_demand, policy_power, *, mode, reference_policy,
                     cohort_id, unit, dt_hours, provenance):
    """Return a self-contained, integrity-bound load ledger.

    Incremental mode interprets input_demand as background excluding the cohort.
    Embedded mode interprets it as total load already containing reference_policy.
    These interpretations are caller assertions, not independently acquired facts.
    """
    if mode not in ('incremental', 'embedded_reference') or unit != 'MW':
        raise ValueError('Explicit cohort interpretation and MW units required')
    if not isinstance(cohort_id, str) or not cohort_id.strip() or not isinstance(provenance, dict) or not provenance:
        raise ValueError('Cohort identity and explicit provenance/assumptions required')
    if isinstance(dt_hours, bool) or not np.isfinite(dt_hours) or dt_hours <= 0:
        raise ValueError('Positive finite interval duration required')
    if not isinstance(input_demand, pd.DataFrame):
        raise ValueError('Time-indexed nodal DataFrames required')
    clock = input_demand.index
    if not isinstance(clock, pd.DatetimeIndex) or clock.tz is None or not len(clock) or clock.hasnans or not clock.is_unique:
        raise ValueError('Nonempty unique timezone-aware interval starts required')
    step = pd.Timedelta(hours=dt_hours)
    if step <= pd.Timedelta(0) or not clock.equals(pd.date_range(clock[0], periods=len(clock), freq=step)):
        raise ValueError('Incomplete, unordered or nonuniform clock; no resampling')
    nodes = list(input_demand.columns)
    if not nodes or len(set(nodes)) != len(nodes) or any(not isinstance(n, str) or not n for n in nodes):
        raise ValueError('Distinct nonempty node names required')
    def values(frame):
        if not isinstance(frame, pd.DataFrame) or not frame.index.equals(clock) or list(frame.columns) != nodes:
            raise ValueError('All policy clocks and node columns must match exactly')
        a = frame.to_numpy(dtype=float, copy=True)
        if not np.isfinite(a).all() or (a < 0).any():
            raise ValueError('Finite nonnegative power required')
        return a
    demand = values(input_demand)
    if not isinstance(policy_power, dict) or not policy_power or reference_policy not in policy_power:
        raise ValueError('Nonempty policy mapping with explicit reference required')
    if any(not isinstance(k, str) or not k or k == 'NO_COHORT' for k in policy_power):
        raise ValueError('Invalid or reserved policy name')
    powers = {name: values(frame) for name, frame in policy_power.items()}
    background = demand if mode == 'incremental' else demand - powers[reference_policy]
    if (background < 0).any():
        raise ValueError('Reference cohort exceeds total demand; no clipping allowed')
    totals = {name: background + power for name, power in powers.items()}
    residual = float(np.max(np.abs(totals[reference_policy] - demand))) if mode == 'embedded_reference' else None
    if residual is not None and not np.allclose(totals[reference_policy], demand, rtol=1e-12, atol=1e-12):
        raise ValueError('Reference reconstruction failed')
    def nodal(a):
        return {node: a[:, i].tolist() for i, node in enumerate(nodes)}
    metrics = {}
    for name, total in totals.items():
        power = powers[name]
        system = total.sum(axis=1)
        cohort = power.sum(axis=1)
        peak = float(system.max())
        positions = np.flatnonzero(system == peak)
        energy = float(system.sum() * dt_hours)
        cohort_energy = float(cohort.sum() * dt_hours)
        metrics[name] = dict(total_energy_mwh=energy, cohort_energy_mwh=cohort_energy,
            background_energy_mwh=float(background.sum() * dt_hours), total_peak_mw=peak,
            cohort_peak_mw=float(cohort.max()), cohort_horizon_energy_share=cohort_energy / energy if energy else None,
            cohort_at_total_peak_min_mw=float(cohort[positions].min()),
            cohort_at_total_peak_max_mw=float(cohort[positions].max()))
    payload = dict(cohort_id=cohort_id, mode=mode, unit=unit, dt_hours=float(dt_hours), nodes=nodes,
        times=[t.isoformat() for t in clock], reference_policy=reference_policy,
        supplied_demand_mw=nodal(demand), background_mw=nodal(background),
        cohort_mw={name: nodal(a) for name, a in powers.items()},
        total_mw={name: nodal(a) for name, a in totals.items()}, metrics=metrics,
        reference_reconstruction_residual_mw=residual, provenance=copy.deepcopy(provenance),
        limitation='Scope assertions require external evidence; this ledger does not certify empirical demand or power calibration')
    return dict(payload=payload, sha256=fingerprint(payload))


def solver_inputs(ledger, policy, *, scenario_name):
    """Keep the cohort mandatory and add it exactly once at the shared nodes."""
    if fingerprint(ledger['payload']) != ledger['sha256']:
        raise ValueError('Demand ledger changed since reconciliation')
    p = ledger['payload']
    if not isinstance(scenario_name, str) or not scenario_name:
        raise ValueError('Nonempty scenario name required')
    if policy == 'NO_COHORT':
        cohort = {n: [0.] * len(p['times']) for n in p['nodes']}
    elif policy in p['cohort_mw']:
        cohort = copy.deepcopy(p['cohort_mw'][policy])
    else:
        raise ValueError('Unknown policy')
    return dict(nodes=list(p['nodes']), scenarios=[Scenario(scenario_name, 1., copy.deepcopy(p['background_mw']))],
                external_fixed_load={scenario_name: cohort}, dt=p['dt_hours'])


def verified_case_ledger(root, case, input_demand, *, node, mode, reference_policy,
                         replicas, full_active_kw_per_gpu, node_idle_ratio, background_provenance):
    """Load the frozen case; the electrical cohort is the entire replicated cluster.

    Untargeted jobs and server idle stay inside that electrical cohort. NO_COHORT
    removes the whole cluster, not merely the jobs whose policy was changed.
    """
    if not isinstance(background_provenance, dict) or not background_provenance:
        raise ValueError('Explicit background source or assumption record required')
    bundle = load_verified_case(root, case)
    converted = convert_power(bundle, replicas=replicas, full_active_kw_per_gpu=full_active_kw_per_gpu,
                              node_idle_ratio=node_idle_ratio)
    if node not in input_demand.columns or not input_demand.index.equals(converted['times']):
        raise ValueError('Verified trajectory must retain its complete original clock and target node')
    policies = {}
    for name, power in converted['power_mw'].items():
        frame = pd.DataFrame(0., index=converted['times'], columns=input_demand.columns)
        frame[node] = power
        policies[name] = frame
    return reconcile_demand(input_demand, policies, mode=mode, reference_policy=reference_policy,
        cohort_id=case, unit='MW', dt_hours=1., provenance=dict(
            background=background_provenance, verified_case_proof=bundle['proof'],
            power_assumptions=converted['assumptions'],
            electrical_cohort='Entire replicated cluster including untargeted GPU work and idle; policies change eligible jobs only',
            no_cohort_meaning='Remove that entire electrical cluster; not only eligible jobs and not all AI in the economy',
            scope='Certified fixed workload; assumed electrical mapping; background inclusion still requires evidence'))
