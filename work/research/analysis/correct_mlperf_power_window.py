#!/usr/bin/env python3
"""Stage 38: source-derived caps and LoadGen-window AC sample means.

This is a secondary extraction, not an official MLPerf certification or paired
energy experiment. Preserve stage 37 for correction provenance.
"""
import ast
import csv
import json
import statistics
import subprocess
from datetime import datetime
from pathlib import Path
from audit_mlperf_power_pair import CAPS, EXPECTED_COMMIT, STANDARD_SYSTEM, MAXQ_SYSTEM, sha256

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / 'work/tmp/mlperf-inference-v40'
OUT = ROOT / 'outputs/research/revision/mlperf_power_corrected'


def resolve_cap(path, name):
    classes = {n.name: n for n in ast.parse(path.read_text()).body if isinstance(n, ast.ClassDef)}
    def walk(key, seen):
        if key in seen or key not in classes:
            raise ValueError(f'Unresolved inheritance: {key}')
        node = classes[key]
        for stmt in node.body:
            if isinstance(stmt, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'power_limit' for t in stmt.targets):
                value = ast.literal_eval(stmt.value)
                if not isinstance(value, (int, float)) or value <= 0:
                    raise ValueError('Invalid power limit')
                return value, ' -> '.join([*seen, key])
        if len(node.bases) != 1 or not isinstance(node.bases[0], ast.Name):
            raise ValueError('Unsupported inheritance; manual review required')
        return walk(node.bases[0].id, [*seen, key])
    return walk(name, [])


def stamp(value):
    return datetime.strptime(value, '%m-%d-%Y %H:%M:%S.%f')


def window_mean(run):
    events = [json.loads(x.split(':::MLLOG ', 1)[1]) for x in (run/'mlperf_log_detail.txt').read_text().splitlines() if x.startswith(':::MLLOG ')]
    boundaries = {}
    for key in ('power_begin', 'power_end'):
        values = [e['value'] for e in events if e['key'] == key]
        if len(values) != 1:
            raise ValueError(f'Ambiguous {key}')
        boundaries[key] = stamp(values[0])
    start, end = boundaries['power_begin'], boundaries['power_end']
    samples = []
    for row in csv.reader((run/'spl.txt').open()):
        if not row:
            continue
        if row[0] != 'Time' or row[2] != 'Watts':
            raise ValueError('Unexpected SPL layout')
        samples.append((stamp(row[1]), float(row[3])))
    if not (samples[0][0] <= start < end <= samples[-1][0]):
        raise ValueError('Window not covered; no extrapolation allowed')
    gaps = [(b[0]-a[0]).total_seconds() for a,b in zip(samples,samples[1:])]
    if min(gaps) <= 0 or max(gaps) > 2:
        raise ValueError('Nonmonotonic or gapped samples')
    selected = [(t,p) for t,p in samples if start <= t <= end]
    if not selected or any(p <= 0 for _,p in selected):
        raise ValueError('Invalid power samples')
    return dict(power_begin=start.isoformat(), power_end=end.isoformat(),
        window_duration_s=(end-start).total_seconds(), window_samples=len(selected),
        window_ac_sample_mean_w=statistics.mean(p for _,p in selected),
        window_ac_sample_min_w=min(p for _,p in selected),
        window_ac_sample_max_w=max(p for _,p in selected), max_sample_gap_s=max(gaps))


def main():
    assert subprocess.check_output(['git','-C',str(SOURCE),'rev-parse','HEAD'],text=True).strip() == EXPECTED_COMMIT
    OUT.mkdir(parents=True,exist_ok=True)
    old = list(csv.DictReader((ROOT/'outputs/research/revision/mlperf_power_admission/matched_results.csv').open()))
    rows, manifest, changes = [], {}, []
    for r in old:
        bench, scenario = r['benchmark'], r['scenario']
        _, config, cls = CAPS[bench]
        cp = SOURCE/'closed/NVIDIA/configs'/config.format(scenario=scenario)
        cap, chain = resolve_cap(cp, cls)
        run = SOURCE/'closed/NVIDIA/results'/MAXQ_SYSTEM/bench/scenario/'performance/run_1'
        w = window_mean(run)
        row = {k:r[k] for k in ('benchmark','scenario','performance_metric','standard_performance','maxq_performance','maxq_to_standard_ratio')}
        row.update(gpu_power_limit_w_each=cap, cap_inheritance=chain, **w,
            stage37_session_mean_w=float(r['maxq_measured_system_power_mean_w']),
            standard_ac_power_status='not_submitted', whole_node_energy_saving_computable=False,
            accuracy_status='record_present_threshold_not_revalidated')
        rows.append(row)
        if cap != int(r['gpu_power_limit_w_each']):
            changes.append(dict(benchmark=bench,scenario=scenario,old_cap_w=int(r['gpu_power_limit_w_each']),corrected_cap_w=cap))
        paths = [cp,run/'spl.txt',run/'mlperf_log_detail.txt',run/'mlperf_log_summary.txt',run.parent/'power/server.json',run.parent/'power/client.json']
        for system in (STANDARD_SYSTEM,MAXQ_SYSTEM):
            base=SOURCE/'closed/NVIDIA/results'/system/bench/scenario
            paths.extend([base/'accuracy/accuracy.txt',base/'performance/run_1/mlperf_log_summary.txt',SOURCE/'closed/NVIDIA/systems'/f'{system}.json'])
        for p in paths:
            manifest[str(p.relative_to(SOURCE))] = sha256(p)
    tree = subprocess.check_output(['git','-C',str(SOURCE),'ls-tree','-r','--name-only','HEAD',f'closed/NVIDIA/results/{STANDARD_SYSTEM}'],text=True).splitlines()
    normal_power = [x for x in tree if '/power/' in x or x.endswith('/spl.txt')]
    assert not normal_power
    with (OUT/'matched_results.csv').open('w') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator="\n");writer.writeheader();writer.writerows(rows)
    summary=dict(source_commit=EXPECTED_COMMIT, matched_rows=len(rows), corrected_cap_rows=changes,
        window_ac_sample_mean_w_min=min(r['window_ac_sample_mean_w'] for r in rows),
        window_ac_sample_mean_w_max=max(r['window_ac_sample_mean_w'] for r in rows),
        minimum_window_samples=min(r['window_samples'] for r in rows),
        standard_power_files_in_git_tree=normal_power,
        method='Arithmetic mean of aggregate SPL Watts samples within inclusive LoadGen power_begin/power_end timestamps as supplied; no clock transformation or extrapolation.',
        scope='Secondary extraction; not an official recertification. Accuracy thresholds, clock synchronization and same physical serial number not independently established. No paired AC energy saving.',
        whole_node_energy_saving_computable=False)
    (OUT/'audit_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    (OUT/'source_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps(summary,indent=2))


if __name__ == '__main__':
    main()
