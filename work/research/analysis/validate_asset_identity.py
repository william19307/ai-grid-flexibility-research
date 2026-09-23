"""Independent grouping/accounting checks and explicit invalid merge cases."""
import argparse
from collections import Counter
import copy
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'work/research/inputs'))
from asset_identity import resolve_aliases, resolve_pinned_file
from thermal_technology import require_dispatch_ready


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input-dir', type=Path, default=ROOT / 'outputs/research/revision/asset_identity')
    args = parser.parse_args()
    output = args.input_dir
    decision = json.loads((ROOT / 'outputs/research/revision/asset_identity/adjudication.json').read_text())
    staging = json.loads((ROOT / 'outputs/research/revision/thermal_technology/fleet_staging.json').read_text())
    actual = json.loads((output / 'asset_candidates.json').read_text())
    by_id = {r['unit_id']: r for r in staging['stock']}
    checks = []

    def check(label, condition):
        if not condition:
            raise AssertionError(label)
        checks.append(label)

    def rejected(label, fn):
        try:
            fn()
        except ValueError:
            checks.append(label)
        else:
            raise AssertionError('Accepted: ' + label)

    # Independently compute equivalence components using a union-find traversal.
    parent = {uid: uid for uid in by_id}

    def root(uid):
        while parent[uid] != uid:
            uid = parent[uid]
        return uid

    for d in decision['decisions']:
        for group in d['groups']:
            ids = group['source_unit_ids']
            for uid in ids[1:]:
                parent[root(uid)] = root(ids[0])
    expected = {}
    for uid in by_id:
        expected.setdefault(root(uid), set()).add(uid)
    groups = actual['asset_candidates']
    check('independent_equivalence_components', {frozenset(g['source_unit_ids']) for g in groups} == {frozenset(v) for v in expected.values()})
    check('complete_nonoverlapping_provenance', Counter(uid for g in groups for uid in g['source_unit_ids']) == Counter(by_id.keys()))
    independent_total = sum(max(Decimal(by_id[uid]['capacity_mw']) for uid in members) for members in expected.values())
    check('independent_once_per_asset_capacity', independent_total == Decimal(actual['resolved_candidate_capacity_mw']) == 24759 and len(groups) == 107)
    check('counting_difference_not_new_capacity', Decimal(actual['source_capacity_mw']) - independent_total == Decimal(actual['alias_counting_difference_mw']) == 200)
    totals = {}
    for g in groups:
        key = (g['candidate_technology'], g['chp_evidence'])
        totals.setdefault(key, [0, Decimal(0)])
        totals[key][0] += 1
        totals[key][1] += Decimal(g['capacity_mw'])
    check('technology_and_heat_preserved', totals == {
        ('CCGT_fossil_gas', 'reported_yes'): [80, Decimal(17653)],
        ('CCGT_fossil_gas', 'unknown'): [15, Decimal(5981)],
        ('industrial_byproduct_steam', 'unknown'): [12, Decimal(1125)]})
    check('investment_and_conditional_parameters_unchanged', actual['investment_options'] == staging['investment_options'] and actual['conditional_parameters'] == staging['conditional_parameters'])
    check('no_operational_admission', actual['qualified_operational_parameter_sets'] == 0 and all(not g['dispatch_ready'] and g['unresolved_requirements'] and Decimal(g['new_build_capacity_mw']) == 0 for g in groups))
    check('source_hashes_and_vintage_retained', actual['source_units'] == [dict(unit_id=r['unit_id'], source_record_sha256=r['source_record_sha256']) for r in staging['stock']]
          and actual['vintage'] == staging['vintage'] and all(
              all(g['source_unit_label_status_vintage'][k] == by_id[uid]['source_record'][k]
                  for k in g['source_unit_label_status_vintage']) for g in groups for uid in g['source_unit_ids']))
    original = copy.deepcopy(staging)
    decision_original = copy.deepcopy(decision)
    result = resolve_aliases(staging, decision)
    check('inputs_not_mutated', staging == original and decision == decision_original)
    reversed_decision = copy.deepcopy(decision)
    reversed_decision['decisions'][0]['groups'].reverse()
    for g in reversed_decision['decisions'][0]['groups']:
        g['source_unit_ids'].reverse()
    check('merge_order_independent', result == resolve_aliases(staging, reversed_decision))
    no_decisions = copy.deepcopy(decision)
    no_decisions['decisions'] = []
    untouched = resolve_aliases(staging, no_decisions)
    check('no_automatic_name_or_proximity_merge', len(untouched['asset_candidates']) == 109 and Decimal(untouched['resolved_candidate_capacity_mw']) == 24959)
    for key, value in [('capacity_mw', '101.0'), ('province', 'Gansu'), ('chp_evidence', 'reported_no'), ('new_build_capacity_mw', '100')]:
        mutated = copy.deepcopy(staging)
        next(r for r in mutated['stock'] if r['unit_id'] == 'G100000412495')[key] = value
        rejected('reject_conflict:' + key, lambda: resolve_aliases(mutated, decision))
    mutated = copy.deepcopy(decision)
    mutated['decisions'][0]['groups'][0]['source_unit_ids'][1] = 'G100000412494'
    rejected('reject_cross_unit_number_merge', lambda: resolve_aliases(staging, mutated))
    mutated = copy.deepcopy(decision)
    mutated['decisions'][0]['groups'][1]['source_unit_ids'].append('G100000405489')
    rejected('reject_source_used_twice', lambda: resolve_aliases(staging, mutated))
    mutated = copy.deepcopy(decision)
    mutated['decisions'][0]['groups'][0]['source_unit_ids'][1] = 'ABSENT'
    rejected('reject_unknown_source_identity', lambda: resolve_aliases(staging, mutated))
    mutated = copy.deepcopy(decision)
    mutated['decisions'][0]['relation'] = 'nearby_coordinates_only'
    rejected('reject_unreviewed_matching_rule', lambda: resolve_aliases(staging, mutated))
    mutated = copy.deepcopy(decision)
    mutated['decisions'][0]['evidence_refs'] = []
    rejected('reject_no_source_references', lambda: resolve_aliases(staging, mutated))
    mutated = copy.deepcopy(staging)
    mutated['stock'].append(copy.deepcopy(mutated['stock'][0]))
    rejected('reject_repeated_inventory_id', lambda: resolve_aliases(mutated, decision))
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / 'changed.json'
        path.write_text(json.dumps(staging))
        rejected('reject_unreviewed_staging_bytes', lambda: resolve_pinned_file(path, decision))
    rejected('resolved_candidates_are_not_dispatch_input', lambda: require_dispatch_ready(actual))
    report = dict(passed=len(checks), checks=checks, candidate_assets=107, candidate_capacity_mw='24759',
                  alias_counting_difference_mw='200',
                  asset_manifest_sha256=hashlib.sha256((output / 'asset_candidates.json').read_bytes()).hexdigest(),
                  scope='Grouping and accounting implementation only; no external confirmation of identity or empirical operating validation.')
    (output / 'validation.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k: v for k, v in report.items() if k != 'checks'}))


if __name__ == '__main__':
    main()
