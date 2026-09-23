"""Independent background-shape and absolute-cohort factors, no empirical calibration."""
import copy
import numpy as np
import pandas as pd
from demand_cohort import fingerprint, reconcile_demand
from verified_power_bridge import load_verified_case, convert_power


def mean_preserving_shape(background, alpha):
    """Preserve energy on the supplied clock only; never clip negative power."""
    if isinstance(alpha, bool) or not np.isscalar(alpha) or not np.isfinite(alpha) or alpha < 0:
        raise ValueError('Finite nonnegative shape parameter required')
    if not isinstance(background, pd.DataFrame) or background.empty:
        raise ValueError('Nonempty nodal background required')
    a = background.to_numpy(float)
    if not np.isfinite(a).all() or (a < 0).any():
        raise ValueError('Finite nonnegative background required')
    shaped = a.mean(axis=0) + float(alpha) * (a - a.mean(axis=0))
    if (shaped < 0).any():
        raise ValueError('Shape would create negative demand; no clipping')
    return pd.DataFrame(shaped, index=background.index, columns=background.columns)


def verified_factorial(root, case, backgrounds, *, replicas, node,
                       full_active_kw_per_gpu, node_idle_ratio, background_provenance,
                       allow_reviewed_tariff_version=False):
    """Certify once and convert once per replica level, outside the shape loop.

    Backgrounds are asserted to exclude this entire electrical cohort. The
    function does not infer or authenticate that real-world inclusion relation.
    """
    if not isinstance(backgrounds, dict) or not backgrounds or any(not isinstance(k, str) or not k for k in backgrounds):
        raise ValueError('Named backgrounds required')
    if not isinstance(background_provenance, dict) or not background_provenance:
        raise ValueError('Explicit background provenance required')
    if not isinstance(replicas, (tuple, list)) or not replicas or any(
        isinstance(r, bool) or not isinstance(r, (int, np.integer)) or r < 1 for r in replicas
    ) or len(set(replicas)) != len(replicas):
        raise ValueError('Distinct positive integer replica levels required')
    bundle = load_verified_case(root, case, allow_reviewed_tariff_version=allow_reviewed_tariff_version)
    ledgers = {}
    first = next(iter(backgrounds.values()))
    if not isinstance(first, pd.DataFrame) or node not in first.columns:
        raise ValueError('Explicit target node required')
    columns = list(first.columns)
    for r in replicas:
        conversion = convert_power(bundle, replicas=r, full_active_kw_per_gpu=full_active_kw_per_gpu,
                                   node_idle_ratio=node_idle_ratio)
        policies = {cell: pd.DataFrame(0., index=conversion['times'], columns=columns)
                    for cell in conversion['power_mw']}
        for cell, power in conversion['power_mw'].items():
            policies[cell][node] = power
        cohort_hash = fingerprint({c: f.to_dict(orient='list') for c, f in policies.items()})
        for shape, background in backgrounds.items():
            if not isinstance(background, pd.DataFrame) or not background.index.equals(conversion['times']) or list(background.columns) != columns:
                raise ValueError('All backgrounds must retain the complete certified clock and same nodes')
            provenance = dict(background=copy.deepcopy(background_provenance),
                verified_case_proof=bundle['proof'], power_assumptions=conversion['assumptions'],
                factors=dict(shape=shape, replicas=int(r)), fixed_cohort_sha256=cohort_hash,
                electrical_cohort='Entire replicated cluster, including idle and untargeted work',
                no_cohort_meaning='Remove the entire electrical cluster, not only eligible jobs',
                inclusion='Incremental cohort is a scenario assumption, not authenticated observed exclusion')
            ledger = reconcile_demand(background, policies, mode='incremental', reference_policy='C00',
                cohort_id=case, unit='MW', dt_hours=1., provenance=provenance)
            ledgers[(shape, int(r))] = ledger
    return ledgers
