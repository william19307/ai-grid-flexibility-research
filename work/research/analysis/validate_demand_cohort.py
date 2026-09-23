"""Frozen analytic accounting example and verified 192h trajectory integration."""
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
from demand_cohort import reconcile_demand, solver_inputs, verified_case_ledger
from verified_power_bridge import load_verified_case, convert_power, CELLS
from coupled_grid_compute import solve, Generator
parser = argparse.ArgumentParser()
parser.add_argument('--reviewed-tariff-version', action='store_true')
parser.add_argument('--output-dir', type=Path)
options = parser.parse_args()
if options.reviewed_tariff_version and options.output_dir is None:
    parser.error('Reviewed-source replay requires a separate --output-dir')
ADMISSION = dict(allow_reviewed_tariff_version=options.reviewed_tariff_version)
OUT = ROOT / options.output_dir if options.output_dir is not None else ROOT / 'outputs/research/revision/demand_cohort'
OUT.mkdir(parents=True, exist_ok=True)
checks = []
clock = pd.date_range('2020-01-01', periods=2, freq='h', tz='Asia/Shanghai')
def frame(x, index=clock):
    return pd.DataFrame({'A': x}, index=index)
total = frame([8., 8.]); powers = {'reference': frame([4., 0.]), 'alternative': frame([0., 2.])}
args = dict(mode='embedded_reference', reference_policy='reference', cohort_id='artificial', unit='MW',
            dt_hours=1., provenance={'scope': 'Synthetic algebraic example, no empirical claim'})
correct = reconcile_demand(total, powers, **args)
naive = reconcile_demand(total, powers, **dict(args, mode='incremental'))
assert correct['payload']['background_mw']['A'] == [4, 8]
assert correct['payload']['total_mw']['reference']['A'] == [8, 8]
assert correct['payload']['total_mw']['alternative']['A'] == [4, 10]
checks.append('embedded_reference_exact_reconstruction_and_no_energy_renormalization')
case_results = {}
for label, ledger, expected in [('correct', correct, {'reference': (8, 160), 'alternative': (10, 170)}),
                                ('naive', naive, {'reference': (12, 220), 'alternative': (10, 190)})]:
    case_results[label] = {}
    for policy, (capacity, cost) in expected.items():
        r = solve(**solver_inputs(ledger, policy, scenario_name='two_hour'),
                  generators=[Generator('g', 'A', 0, 20, 10, 5)])
        assert r['feasible'] and abs(r['new_generator_mw']['g'] - capacity) < 1e-8
        assert abs(r['total_cost'] - cost) < 1e-8
        assert abs(sum(r['scenarios']['two_hour']['generation']['g']) - ledger['payload']['metrics'][policy]['total_energy_mwh']) < 1e-8
        case_results[label][policy] = dict(capacity_mw=r['new_generator_mw']['g'], cost=r['total_cost'])
    checks.append(label + '_capacity_and_cost_match_predefined_independent_formula')
assert case_results['correct']['reference']['cost'] - case_results['correct']['alternative']['cost'] == -10
assert case_results['naive']['reference']['cost'] - case_results['naive']['alternative']['cost'] == 30
checks.append('double_counting_reverses_capacity_and_net_cost_conclusion_in_counterexample')

no = solver_inputs(correct, 'NO_COHORT', scenario_name='s')
assert no['scenarios'][0].load_mw['A'] == [4, 8] and no['external_fixed_load']['s']['A'] == [0, 0]
checks.append('no_cohort_removes_only_treated_cohort_background_unchanged')
# A mandatory cohort cannot be hidden as shed background.
must = reconcile_demand(frame([0, 0]), {'reference': frame([1, 1])}, **dict(args, mode='incremental'))
r = solve(**solver_inputs(must, 'reference', scenario_name='s'), generators=[], expected_unserved_limit_mwh=100)
assert r['proven_infeasible']
checks.append('cohort_mandatory_even_with_large_background_shedding_allowance')

half = pd.date_range('2020-01-01', periods=2, freq='30min', tz='Asia/Shanghai')
b = pd.DataFrame({'A': [4, 6], 'B': [2, 2]}, index=half)
p = {'reference': pd.DataFrame({'A': [2, 0], 'B': [0, 2]}, index=half)}
multi = reconcile_demand(b, p, **dict(args, mode='incremental', dt_hours=.5))
m = multi['payload']['metrics']['reference']
assert m['total_energy_mwh'] == 9 and m['cohort_energy_mwh'] == 2 and m['background_energy_mwh'] == 7
assert m['total_peak_mw'] == 10
checks.append('multiple_nodes_half_hour_MW_to_MWh_conservation')
# Coincident-peak contribution is not the cohort's own maximum. Keep every tie.
tied = reconcile_demand(frame([8, 8]), {'reference': frame([4, 0])}, **args)
tm = tied['payload']['metrics']['reference']
assert tm['cohort_at_total_peak_min_mw'] == 0 and tm['cohort_at_total_peak_max_mw'] == 4
assert tm['cohort_horizon_energy_share'] == .25
checks.append('all_system_peak_ties_and_energy_denominator_preserved')

def rejects(label, call):
    try:
        call()
    except ValueError:
        checks.append(label)
    else:
        raise AssertionError(label)
rejects('negative_background_not_clipped', lambda: reconcile_demand(frame([3, 8]), powers, **args))
for key, value in [('unit', 'kW'), ('dt_hours', 0), ('dt_hours', .5), ('mode', 'unknown'), ('reference_policy', 'missing')]:
    rejects('reject_' + key + '_' + str(value), lambda k=key, v=value: reconcile_demand(total, powers, **dict(args, **{k: v})))
for label, f in [('naive_clock', frame([8, 8], clock.tz_localize(None))), ('reverse_clock', total.iloc[::-1]),
                 ('nan', frame([8, np.nan])), ('negative', frame([-1, 8]))]:
    rejects('reject_' + label, lambda f=f: reconcile_demand(f, powers, **args))
bad = dict(powers, alternative=frame([0, 2], clock + pd.Timedelta(hours=1)))
rejects('no_silent_policy_clock_shift', lambda: reconcile_demand(total, bad, **args))
bad = dict(powers, alternative=powers['alternative'].rename(columns={'A': 'B'}))
rejects('no_silent_node_remapping', lambda: reconcile_demand(total, bad, **args))
changed = copy.deepcopy(correct); changed['payload']['background_mw']['A'][0] += 1
rejects('mutated_ledger_rejected', lambda: solver_inputs(changed, 'reference', scenario_name='s'))
# Returned solver inputs do not alias the ledger.
before = copy.deepcopy(correct)
detached = solver_inputs(correct, 'reference', scenario_name='s'); detached['scenarios'][0].load_mw['A'][0] = 999
assert before == correct
checks.append('solver_mutation_does_not_change_frozen_ledger')

case = 'Earth_ft_llama_8b_dolly_6_Jiangsu'
bundle = load_verified_case(ROOT, case, **ADMISSION)
converted = convert_power(bundle, replicas=1, full_active_kw_per_gpu=.5, node_idle_ratio=.41)
# Construct a synthetic total containing the exact certified C00 trajectory.
synthetic_background = np.full(192, 3.)
reference_total = pd.DataFrame({'A': synthetic_background + converted['power_mw']['C00']}, index=converted['times'])
real = verified_case_ledger(ROOT, case, reference_total, **ADMISSION, node='A', mode='embedded_reference', reference_policy='C00',
    replicas=1, full_active_kw_per_gpu=.5, node_idle_ratio=.41,
    background_provenance={'status': 'SYNTHETIC', 'description': 'Constant 3 MW background; not provincial measured demand'})
real_results = {}; residuals = []
for cell in CELLS:
    inputs = solver_inputs(real, cell, scenario_name='verified_192h')
    expected = synthetic_background + converted['power_mw'][cell]
    assert len(inputs['scenarios'][0].load_mw['A']) == 192
    assert np.allclose(inputs['scenarios'][0].load_mw['A'], synthetic_background, atol=1e-12, rtol=0)
    assert inputs['external_fixed_load']['verified_192h']['A'] == converted['power_mw'][cell].tolist()
    r = solve(**inputs, generators=[Generator('analytic', 'A', float(expected.max() + 1), 0, 0, 5)])
    assert r['feasible']
    rr = r['scenarios']['verified_192h']; error = float(np.max(np.abs(np.asarray(rr['generation']['analytic']) - expected)))
    assert error < 1e-9 and abs(r['total_cost'] - 5 * expected.sum()) < 1e-7
    assert rr['task_allocations'] == {} and r['expected_unserved_mwh'] < 1e-9
    residuals.append(error)
    real_results[cell] = dict(energy_mwh=float(expected.sum()), cost=r['total_cost'], hours=192, balance_error_mw=error)
checks.append('four_real_certified_192h_trajectories_with_synthetic_background_match_analytic_dispatch')
removed = solver_inputs(real, 'NO_COHORT', scenario_name='removed_cluster')
assert np.allclose(removed['scenarios'][0].load_mw['A'], synthetic_background, atol=1e-12, rtol=0)
assert sum(removed['external_fixed_load']['removed_cluster']['A']) == 0
assert 'entire electrical cluster' in real['payload']['provenance']['no_cohort_meaning']
checks.append('real_bridge_no_cohort_explicitly_removes_entire_cluster_including_idle_and_background_jobs')
rejects('verified_recovery_tail_cannot_be_truncated', lambda: verified_case_ledger(ROOT, case, reference_total.iloc[:168], **ADMISSION,
    node='A', mode='embedded_reference', reference_policy='C00', replicas=1, full_active_kw_per_gpu=.5, node_idle_ratio=.41,
    background_provenance={'status': 'SYNTHETIC'}))

report = dict(date='2026-09-23', checks=checks, number_of_checks=len(checks),
    frozen_design_commit='d3af59d', counterexample=case_results, certified_case=case,
    maximum_real_trace_balance_error_mw=max(residuals), real_trace_results=real_results,
    scope='Accounting and conditional integration only; synthetic background and assumed power; not new provincial estimates')
if options.reviewed_tariff_version: report['source_admission_mode'] = 'explicit_reviewed_tariff_version'
for name, obj in [('validation.json', report), ('synthetic_counterexample_ledgers.json', {'correct': correct, 'naive': naive}),
                  ('verified_trace_synthetic_background_ledger.json', real)]:
    (OUT / name).write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n')
print(json.dumps(report, ensure_ascii=False, indent=2))
