"""Frozen controlled sensitivity; no calibrated provincial benefit estimates."""
from pathlib import Path
import copy
import argparse
import hashlib
import json
import sys
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'work/research/models'))
from fixed_cohort_factorial import mean_preserving_shape, verified_factorial
from verified_power_bridge import load_verified_case, convert_power, CELLS
from demand_cohort import solver_inputs, fingerprint
from coupled_grid_compute import Generator, solve
parser = argparse.ArgumentParser()
parser.add_argument('--reviewed-tariff-version', action='store_true')
parser.add_argument('--output-dir', type=Path)
options = parser.parse_args()
if options.reviewed_tariff_version and options.output_dir is None:
    parser.error('Reviewed-source replay requires a separate --output-dir')
ADMISSION = dict(allow_reviewed_tariff_version=options.reviewed_tariff_version)
OUT = ROOT / options.output_dir if options.output_dir is not None else ROOT / 'outputs/research/revision/fixed_cohort_factorial'
OUT.mkdir(parents=True, exist_ok=True)
SOURCE = ROOT / 'work/research/prepared/load_2020_annual_anchored_hourly_shape_UNVALIDATED.npz'
def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()
source_before = sha(SOURCE)
archive = np.load(SOURCE)
clock = pd.to_datetime(archive['timestamps_UTC_ns'], utc=True).tz_convert('Asia/Shanghai')
assert len(clock) == 8784 and clock.is_unique
checks = []; metrics = []; contrasts = []; records = []; solves = []; maxima = []
def check(label, condition):
    if not condition:
        raise AssertionError(label)
    checks.append(label)
def rejects(label, action):
    try:
        action()
    except ValueError:
        checks.append(label)
    else:
        raise AssertionError(label)

for province in ('Jiangsu', 'Gansu', 'Guizhou'):
    case = 'Earth_ft_llama_8b_dolly_6_' + province
    bundle = load_verified_case(ROOT, case, **ADMISSION)
    converted = convert_power(bundle, replicas=1, full_active_kw_per_gpu=.5, node_idle_ratio=.41)
    full = pd.DataFrame({'grid': archive['load_MW'][:, list(archive['provinces']).index(province)]}, index=clock)
    background = full.loc[converted['times']]
    backgrounds = {str(alpha): mean_preserving_shape(background, alpha) for alpha in (0., .5, 1.)}
    kwargs = dict(**ADMISSION, replicas=[1, 1000], node='grid', full_active_kw_per_gpu=.5, node_idle_ratio=.41,
        background_provenance=dict(status='UNVALIDATED_CONDITIONAL_SCENARIO', path=str(SOURCE.relative_to(ROOT)),
            sha256=source_before, province_pairing=province, window='192h, no annual capacity inference',
            inclusion='Assumed incremental; observed cohort exclusion unknown'))
    ledgers = verified_factorial(ROOT, case, backgrounds, **kwargs)
    check(province + '_window_energy_preserved', all(np.allclose(b.sum(), background.sum(), rtol=1e-13, atol=1e-7) for b in backgrounds.values()))
    for r in (1, 1000):
        hashes = [ledgers[(shape, r)]['payload']['provenance']['fixed_cohort_sha256'] for shape in backgrounds]
        check(province + '_cohort_shape_invariant_R' + str(r), len(set(hashes)) == 1)
    for shape in backgrounds:
        one = ledgers[(shape, 1)]['payload']; many = ledgers[(shape, 1000)]['payload']
        check(province + '_background_replica_invariant_' + shape, one['background_mw'] == many['background_mw'])
        check(province + '_absolute_replica_scaling_' + shape, all(np.allclose(np.array(many['cohort_mw'][c]['grid']), 1000*np.array(one['cohort_mw'][c]['grid']), rtol=1e-13, atol=1e-9) for c in CELLS))
    for (shape, r), ledger in ledgers.items():
        p = ledger['payload']; b = np.array(p['background_mw']['grid'])
        records.append(dict(case=case, shape=shape, replicas=r, ledger_sha256=ledger['sha256'],
            cohort_sha256=p['provenance']['fixed_cohort_sha256'], background_sha256=fingerprint(p['background_mw']),
            start=p['times'][0], end=p['times'][-1], hours=len(p['times']), proof=p['provenance']['verified_case_proof']))
        for cell in (*CELLS, 'NO_COHORT'):
            a = np.array(p['cohort_mw'][cell]['grid']) if cell != 'NO_COHORT' else np.zeros(192)
            demand = b + a
            # Independent analytic oracle uses scalar Python arithmetic, not the ledger metrics or solver result.
            energy = sum(float(x) for x in demand); peak = max(float(x) for x in demand)
            analytic_cost = 10*peak + 5*energy
            row = dict(case=case, province=province, shape=float(shape), replicas=r, policy=cell,
                hours=len(demand), background_energy_mwh=float(b.sum()), cohort_energy_mwh=float(a.sum()),
                total_energy_mwh=energy, total_peak_mw=peak, analytic_diagnostic_cost=analytic_cost)
            metrics.append(row)
            if cell == 'NO_COHORT':
                continue
            inp = solver_inputs(ledger, cell, scenario_name='diagnostic')
            result = solve(**inp, generators=[Generator('g', 'grid', 0, 1e6, 10, 5)])
            assert result['feasible'] and result['expected_unserved_mwh'] < 1e-8
            generation = np.array(result['scenarios']['diagnostic']['generation']['g'])
            balance_error = float(np.max(abs(generation-demand)))
            cost_error = abs(result['total_cost']-analytic_cost)
            capacity_error = abs(result['new_generator_mw']['g']-peak)
            assert balance_error < 1e-7 and capacity_error < 1e-7 and cost_error < 1e-4
            assert np.isclose(p['metrics'][cell]['total_energy_mwh'], energy, rtol=1e-13)
            maxima.append((balance_error, capacity_error, cost_error))
            solves.append(dict(case=case, shape=float(shape), replicas=r, policy=cell,
                cost=result['total_cost'], capacity_mw=result['new_generator_mw']['g'],
                balance_error_mw=balance_error, capacity_error_mw=capacity_error, cost_error=cost_error))
    check(province + '_all_24_policy_solves_match_independent_oracle', len([x for x in solves if x['case']==case]) == 24)

check('all_prespecified_cells_reported', len(records)==18 and len(metrics)==90 and len(solves)==72)
df = pd.DataFrame(metrics)
for keys, group in df.groupby(['case', 'shape', 'replicas']):
    policies = group.set_index('policy')
    for policy in CELLS[1:]:
        contrasts.append(dict(case=keys[0], shape=keys[1], replicas=keys[2], policy=policy,
            energy_saved_mwh=policies.loc['C00','total_energy_mwh']-policies.loc[policy,'total_energy_mwh'],
            peak_reduction_mw=policies.loc['C00','total_peak_mw']-policies.loc[policy,'total_peak_mw'],
            diagnostic_cost_saved=policies.loc['C00','analytic_diagnostic_cost']-policies.loc[policy,'analytic_diagnostic_cost']))
contrast_df = pd.DataFrame(contrasts)
interactions = []
for (case, r, policy), group in contrast_df.groupby(['case','replicas','policy']):
    g = group.set_index('shape')
    check('policy_energy_difference_shape_invariant_' + case + '_' + str(r) + '_' + policy,
          float(g.energy_saved_mwh.max()-g.energy_saved_mwh.min()) < 1e-6)
    interactions.append(dict(case=case, replicas=r, policy=policy,
        peak_shape_interaction_mw=g.loc[1.,'peak_reduction_mw']-g.loc[0.,'peak_reduction_mw'],
        cost_shape_interaction=g.loc[1.,'diagnostic_cost_saved']-g.loc[0.,'diagnostic_cost_saved']))

for alpha in (-1, float('nan'), float('inf'), True):
    rejects('reject_shape_' + str(alpha), lambda alpha=alpha: mean_preserving_shape(background, alpha))
tiny = pd.DataFrame({'grid':[0., 2.]}, index=background.index[:2])
rejects('reject_negative_shaped_demand_without_clipping', lambda: mean_preserving_shape(tiny, 2.))
for label, bad in [('nonfinite', background*float('nan')), ('negative', -background)]:
    rejects('reject_background_' + label, lambda bad=bad: mean_preserving_shape(bad, 1.))
for rs in ([1,1], [0], [1.5], [True]):
    rejects('reject_replicas_' + str(rs), lambda rs=rs: verified_factorial(ROOT, case, backgrounds, **dict(kwargs, replicas=rs)))
for label, bad in [('truncated', background.iloc[:168]), ('shifted', background.set_axis(background.index+pd.Timedelta(hours=1))),
                   ('node', background.rename(columns={'grid':'other'}))]:
    rejects('reject_background_' + label, lambda bad=bad: verified_factorial(ROOT, case, {'bad':bad}, **kwargs))
changed = copy.deepcopy(ledger); changed['payload']['cohort_mw']['C00']['grid'][0] += 1
rejects('reject_changed_cohort', lambda: solver_inputs(changed,'C00',scenario_name='s'))
original = copy.deepcopy(ledger)
inp = solver_inputs(ledger,'C00',scenario_name='s'); inp['external_fixed_load']['s']['grid'][0] += 1
check('solver_input_mutation_detached', original==ledger)
result = solve(**solver_inputs(ledger,'C00',scenario_name='s'), generators=[Generator('g','grid',0,1,10,5)])
check('capacity_shortfall_reported_infeasible', result['proven_infeasible'])
check('legacy_background_source_unchanged', sha(SOURCE)==source_before)
report = dict(date='2026-09-23', frozen_design_commit='ddc24b8', checks=checks, number_of_checks=len(checks),
    ledger_count=len(records), metric_rows=len(metrics), policy_solves=len(solves), negative_capacity_solves=1,
    maximum_balance_error_mw=max(x[0] for x in maxima), maximum_capacity_error_mw=max(x[1] for x in maxima),
    maximum_cost_error=max(x[2] for x in maxima), background_source_sha256=source_before,
    scope='Controlled 192h input and mathematical solver check only; assumed power, unvalidated background, artificial fleet; no provincial empirical benefit')
if options.reviewed_tariff_version: report['source_admission_mode'] = 'explicit_reviewed_tariff_version'
for filename, data in [('validation.json',report), ('factor_ledger_manifest.json',records)]:
    (OUT/filename).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
for filename, table in [('demand_metrics.csv',df), ('policy_contrasts.csv',contrast_df),
                         ('shape_interactions.csv',pd.DataFrame(interactions)), ('solver_oracle_checks.csv',pd.DataFrame(solves))]:
    table.to_csv(OUT/filename,index=False)
print(json.dumps(report,ensure_ascii=False,indent=2))
