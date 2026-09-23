"""Rebuild the pre-industrial solver and compare no-site regression reports."""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
BASE = 'e936ef6bbce7e8a4ef32c19149a9cad0aa2a759b'
parser = argparse.ArgumentParser()
parser.add_argument('--scratch', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True)
parser.add_argument('--compare-existing', action='store_true', help='Compare existing reports without rerunning; requires retained baseline/current outputs')
args = parser.parse_args()
scratch = args.scratch.resolve()
suites = ['coupled_grid_compute', 'thermal_commitment', 'reservoir_coupling']
if not args.compare_existing:
    scratch.mkdir(parents=True, exist_ok=False)
    baseline = scratch / 'baseline_checkout'
    paths = ['work/research/models/coupled_grid_compute.py', 'work/research/models/thermal_commitment.py']
    paths += [f'work/research/analysis/validate_{s}.py' for s in suites]
    for path in paths:
        target = baseline / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(subprocess.check_output(['git', 'show', f'{BASE}:{path}'], cwd=ROOT))
    for version, root in [('baseline', baseline), ('current', ROOT)]:
        for suite in suites:
            subprocess.run([sys.executable, str(root / f'work/research/analysis/validate_{suite}.py'),
                            '--output-dir', str(scratch / f'{version}_outputs' / suite)], check=True, cwd=ROOT)
comparisons = []
for suite, name, excluded in [
    ('coupled_grid_compute', 'coupled_grid_compute_validation.json', ['model_sha256']),
    ('coupled_grid_compute', 'coupled_grid_compute_analytic_examples.json', []),
    ('thermal_commitment', 'thermal_commitment_validation.json', ['source_sha256']),
    ('reservoir_coupling', 'reservoir_coupling_validation.json', ['model_sha256']),
]:
    raw = [(scratch / f'{v}_outputs' / suite / name).read_bytes() for v in ('baseline', 'current')]
    objects = [json.loads(b) for b in raw]
    for obj in objects:
        for key in excluded:
            if key not in obj:
                raise ValueError(f'Missing expected provenance field: {name}:{key}')
            del obj[key]
    if objects[0] != objects[1]:
        raise AssertionError(f'No-site behaviour changed: {name}')
    comparisons.append(dict(suite=suite, file=name, baseline_sha256=hashlib.sha256(raw[0]).hexdigest(),
                            current_sha256=hashlib.sha256(raw[1]).hexdigest(), excluded_provenance_fields=excluded,
                            all_other_content_equal=True, byte_identical=raw[0] == raw[1]))
report = dict(baseline_commit=BASE, baseline_source='git show into separate temporary source tree',
              environment='same Python executable, fresh subprocesses for each source/suite',
              comparison_only=args.compare_existing, comparisons=comparisons,
              scope='No-industrial-site behaviour regression; not empirical validation or second-machine reconstruction')
args.output.parent.mkdir(parents=True, exist_ok=True)
args.output.write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
