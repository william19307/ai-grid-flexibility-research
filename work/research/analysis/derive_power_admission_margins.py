"""Conditional overhead budgets from published means, with explicit rounding bounds.

Bounds cover printed precision only; they are not sampling or instrument uncertainty.
This derivation does not approve a deployment or certify task quality.
"""
from pathlib import Path
from decimal import Decimal as D
from itertools import product
import csv
import hashlib
import json

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT/'outputs/research/revision/whole_node_power'
OUT = ROOT/'outputs/research/revision/power_admission'


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    upstream = json.loads((SOURCE/'source_snapshot.json').read_text())
    for path, expected in upstream['source_hashes'].items():
        if sha(ROOT/path) != expected:
            raise ValueError(f'Changed primary source: {path}')
    script = ROOT/'work/research/analysis/audit_whole_node_power_source.py'
    if sha(script) != upstream['script_sha256']:
        raise ValueError('Changed source extraction implementation; re-audit first')
    source_csv = SOURCE/'published_means_and_derived.csv'
    # The input is the previously inspected, cross-engine-verified table.
    expected_csv = '68d99747f08a65aefab568252a9d11457a8282f75c1e45984d09ad2d7321e0b2'
    if sha(source_csv) != expected_csv:
        raise ValueError('Changed published table; re-audit before using this derivation')
    data = list(csv.DictReader(source_csv.open()))
    out = []
    selected = []
    checks = 0
    overhead_checks = 0
    half_unit = D('.005')  # Both energy [kJ] and runtime [s] have two printed decimals.
    for n in [1,2,4,8]:
        group = [r for r in data if int(r['active_gpus']) == n]
        ref = next(r for r in group if int(r['gpu_power_cap_w']) == 260)
        er,tr = D(ref['energy_kj']),D(ref['runtime_s'])
        for delta in map(D,['0','.025','.05','.1','.2','.5','1']):
            choices = []
            for row in group:
                em,tm = D(row['energy_kj']),D(row['runtime_s'])
                cap = int(row['gpu_power_cap_w'])
                is_ref = cap == 260
                # Reference errors are correlated with themselves: don't treat as two runs.
                tau = delta*(tr-half_unit) if is_ref else (1+delta)*(tr-half_unit)-(tm+half_unit)
                k_j = D(0) if is_ref else 1000*(er-em-2*half_unit)
                eligible = is_ref or (tau >= 0 and k_j > 0)
                record = dict(active_gpus=n, gpu_cap_w=cap, relative_reference_time_allowance=str(delta),
                    rounding_only_additional_time_margin_s=str(tau),
                    rounding_only_additional_energy_margin_j=str(k_j),
                    nominal_energy_reduction_pct=str(100*(1-em/er)),
                    rounding_only_energy_reduction_lower_pct=str(D(0) if is_ref else 100*(1-(em+half_unit)/(er-half_unit))),
                    mean_candidate_passes_rounding_and_zero_overhead_screen=eligible,
                    is_reference=is_ref)
                out.append(record)
                if eligible:
                    choices.append(record)
                if is_ref:
                    continue
                assert tm-half_unit > tr+half_unit
                # Independent endpoint enumeration of uncertain printed means and
                # several idle powers. The analytical all-P>=0 result follows from
                # the nonnegative runtime difference, not this finite grid.
                min_margin = None
                for es, ts, rs, us in product([-1,1], repeat=4):
                    e_actual=em+es*half_unit
                    t_actual=tm+ts*half_unit
                    e_ref=er+rs*half_unit
                    t_ref=tr+us*half_unit
                    time_margin=(1+delta)*t_ref-t_actual
                    assert time_margin >= tau
                    if eligible:
                        # Simultaneously spend both conservative overhead budgets.
                        # The worst corner has zero benefit, hence strict savings
                        # require energy overhead strictly below the reported margin.
                        assert t_actual+tau <= (1+delta)*t_ref
                        for idle in map(D,['0','433.58']):
                            end=max(t_actual+tau,t_ref)+D(100)
                            base=e_ref+idle*(end-t_ref)/1000
                            controlled=e_actual+k_j/1000+idle*(end-t_actual-tau)/1000
                            assert base-controlled >= 0
                            overhead_checks+=1
                    for idle in map(D,['0','100','433.58','1000000']):
                        horizon=max(t_actual,t_ref)+D(100)
                        base=e_ref+idle*(horizon-t_ref)/1000
                        candidate=e_actual+idle*(horizon-t_actual)/1000
                        difference=base-candidate
                        assert difference >= k_j/1000
                        assert difference == e_ref-e_actual+idle*(t_actual-t_ref)/1000
                        min_margin=difference if min_margin is None else min(min_margin,difference)
                        checks+=1
                assert min_margin == k_j/1000
            # Maximize the conservative absolute energy margin. This is one
            # declared selection rule, not an idle-dependent or global optimum.
            winner=max(choices,key=lambda r:D(r['rounding_only_additional_energy_margin_j']))
            selected.append(winner)
    OUT.mkdir(parents=True,exist_ok=True)
    for filename, rows in [('all_candidate_margins.csv',out),('selected_mean_candidates.csv',selected)]:
        with (OUT/filename).open('w',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=list(rows[0]))
            writer.writeheader();writer.writerows(rows)
    result=dict(configurations=68, candidate_deadline_conditions=len(out),
        selection_conditions=len(selected), endpoint_energy_checks=checks,
        joint_overhead_corner_checks=overhead_checks,
        checked_with_exact_decimal_arithmetic=True,
        statistical_confidence_claim=False, instrumental_uncertainty_covered=False,
        runtime_tail_or_quality_certified=False,
        assumptions=['Fixed identical useful work and quality must be established separately',
            'Common nonnegative constant idle power after completion',
            'One job in a common observation horizon; no subsequent work or shutdown',
            'Overhead is additional total AC energy and elapsed time not already included in the measured mode',
            'Printed rounding intervals only, assuming conventional rounding to nearest 0.01'],
        input_sha256=sha(source_csv),source_snapshot_sha256=sha(SOURCE/'source_snapshot.json'),
        script_sha256=sha(Path(__file__)))
    (OUT/'verification.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
    print('10% allowance candidates:')
    for r in selected:
        if r['relative_reference_time_allowance']=='.1' or D(r['relative_reference_time_allowance'])==D('.1'):
            print(r)


if __name__=='__main__':
    main()
