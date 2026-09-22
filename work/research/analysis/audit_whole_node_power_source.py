"""Extract published means, cross-check PDF engines, and analyse explicit energy boundaries.

No imputation of idle power, SD units, quality, or hardware transfer is permitted.
"""
from pathlib import Path
import argparse
import csv
import hashlib
import json
import re
import subprocess
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / 'work/research/sources/whole_node_power_20260922'
OUT = ROOT / 'outputs/research/revision/whole_node_power'
FIELDS = {
    'Average power [W]': 'whole_node_power_w',
    'Total time [s]': 'runtime_s',
    'Standard deviation of time [-]': 'reported_time_sd_unit_unresolved',
    'Total energy [kJ]': 'energy_kj',
    'Standard deviation of energy [-]': 'reported_energy_sd_unit_unresolved',
    'EDP [MJs]': 'edp_mjs',
    'EDS (k = 1.5)': 'eds_1_5',
    'EDS (k = 2)': 'eds_2',
}
URL = 'https://cdn.files.pg.edu.pl/eti/KASK/RAW2023-paper-supplementary-data/Supplementary_data_Performance_and_power_analysis_of_training_and_performance_quality.pdf'
SOURCE_HASHES = {
    'supplementary.pdf': 'b8f2b792a349a6a0193d34d9b9648d536d65c49237c072eb3e1172d95655a492',
    'main.pdf': 'e3a5dd1c251cb21d15516c6586e2e2291723b0aa6dcee38c4eb8dc6526d7fa8e',
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_csv(name, rows):
    with (OUT / name).open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--pdf-python', required=True, help='Python with pdfplumber for independent extraction')
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    for filename, expected in SOURCE_HASHES.items():
        if sha(SRC / filename) != expected:
            raise ValueError(f'Source changed: {filename}; review before extracting a new version')
    pdf = SRC / 'supplementary.pdf'
    assert pdf.read_bytes().startswith(b'%PDF-')
    text = subprocess.check_output(['pdftotext', '-layout', str(pdf), '-'], text=True)
    cap_line = next(line for line in text.splitlines() if re.search(r'power cap\s+100', line))
    assert [int(v) for v in cap_line.split('power cap')[1].split()] == list(range(100,261,10))
    blocks = {}
    n = None
    for line in text.splitlines():
        m = re.fullmatch(r'\s*(1|2|4|8) GPUs?\s*', line)
        if m:
            n = int(m[1])
            blocks[n] = {}
        for label, key in FIELDS.items():
            if label in line:
                assert n is not None
                values = line.split(label, 1)[1].split()
                assert len(values) == 17, (n, key, values)
                blocks[n][key] = [float(x) for x in values]
    assert set(blocks) == {1, 2, 4, 8}
    assert all(set(b) == set(FIELDS.values()) for b in blocks.values())

    # A different PDF engine reads rotated row geometry and numeric words.
    independent = r'''
import json, re, sys, pdfplumber
with pdfplumber.open(sys.argv[1]) as doc:
    assert len(doc.pages) == 2
    words = doc.pages[1].extract_words(x_tolerance=.5, y_tolerance=.5)
    rows = {}
    for w in words:
        if not w['upright'] and w['top'] > 240 and re.fullmatch(r'\d+\.\d+', w['text']):
            rows.setdefault(round(w['x0'], 3), []).append((w['top'], float(w['text'])))
    result = [[v for _, v in sorted(row)] for _, row in sorted(rows.items(), reverse=True)]
    assert len(result) == 32 and all(len(row) == 17 for row in result)
    print(json.dumps({'rows':result, 'pdfplumber_version':pdfplumber.__version__}))
'''
    alt = json.loads(subprocess.check_output([args.pdf_python, '-c', independent, str(pdf)], text=True))
    canonical = [blocks[n][k] for n in [1, 2, 4, 8] for k in FIELDS.values()]
    assert canonical == alt['rows'], 'Independent PDF extraction mismatch'
    idle_upper_screen = min(v for b in blocks.values() for v in b['whole_node_power_w'])
    rows, summaries, frontiers = [], [], []
    for n, b in blocks.items():
        p = np.array(b['whole_node_power_w'])
        t = np.array(b['runtime_s'])
        e = np.array(b['energy_kj'])
        caps = np.arange(100, 261, 10)
        assert np.all(p > 0) and np.all(t > 0) and np.all(e > 0)
        assert t[-1] == min(t)
        residual = (p * t / 1000 - e) / e
        j = int(np.argmin(e))
        summaries.append(dict(active_gpus=n, energy_min_cap_w=int(caps[j]),
            active_energy_reduction_pct=float(100*(1-e[j]/e[-1])),
            runtime_extension_pct=float(100*(t[j]/t[-1]-1)),
            whole_node_power_reduction_pct=float(100*(1-p[j]/p[-1])),
            max_abs_energy_vs_mean_power_time_relative_error=float(max(abs(residual))),
            mean_runtime_nonmonotonic_caps_w=[int(caps[k]) for k in range(1,17) if t[k]>t[k-1]],
            hypothetical_idle_upper_screen_w=float(idle_upper_screen)))
        for k, cap in enumerate(caps):
            row = dict(active_gpus=n, installed_gpus=8, gpu_power_cap_w=int(cap),
                       **{key:b[key][k] for key in FIELDS.values()})
            row.update(relative_throughput=float(t[-1]/t[k]),
                relative_whole_node_power=float(p[k]/p[-1]),
                relative_active_energy=float(e[k]/e[-1]),
                energy_vs_mean_power_time_relative_error=float(residual[k]),
                idle_break_even_w=(float(1000*(e[k]-e[-1])/(t[k]-t[-1])) if k!=16 else None))
            rows.append(row)
        # Constant idle is an explicitly hypothetical screen, not a measured fit.
        # H is the same for both policies. Extra-work, shutdown and switching absent.
        for slack in [0, .05, .1, .2, .5, 1., float(max(t)/t[-1]-1)]:
            horizon = t[-1]*(1+slack)
            eligible = np.flatnonzero(t <= horizon+1e-10)
            for fraction in [0, .25, .5, .75, 1.]:
                idle = fraction*idle_upper_screen
                total = e[eligible]+idle*(horizon-t[eligible])/1000
                base = e[-1]+idle*(horizon-t[-1])/1000
                best = int(np.argmin(total))
                selected = int(eligible[best])
                # Independently compare delta-energy algebra with common horizon.
                delta = e[-1]-e[selected]+idle*(t[selected]-t[-1])/1000
                assert abs(delta-(base-total[best])) < 1e-10
                assert base-total[best] >= -1e-10
                frontiers.append(dict(active_gpus=n, relative_runtime_allowance=slack,
                    hypothetical_idle_fraction_of_global_min_measured_active_power=fraction,
                    hypothetical_idle_w=float(idle), common_horizon_s=float(horizon),
                    selected_cap_w=int(caps[selected]), energy_reduction_pct=float(100*delta/base)))
    write_csv('published_means_and_derived.csv', rows)
    write_csv('common_horizon_sensitivity.csv', frontiers)
    audit = dict(source_doi='10.1007/978-3-031-48803-0_1', configurations=68,
        independent_extraction_equal_numeric_cells=544, common_horizon_algebra_checks=len(frontiers),
        reported_replicates_per_configuration=10, individual_replicates_available=False,
        raw_meter_series_available=False, sd_units_resolved=False, idle_calibrated=False,
        curve_transfer_to_helios_validated=False, uncertainty_intervals_estimated=False,
        idle_screen_definition='One common hypothetical idle range, 0 to the smallest measured active power across all 68 points; not an empirical idle bound or estimate',
        measured_quantity='Whole-machine AC input including unused GPUs; fixed five-epoch XCeption training',
        selection='Exploratory discrete minimum of reported means; not an independently tested optimum',
        summaries=summaries)
    (OUT/'audit.json').write_text(json.dumps(audit, indent=2)+'\n')
    manifest = dict(accessed='2026-09-22', supplementary_url=URL,
        main_url='https://link.springer.com/chapter/10.1007/978-3-031-48803-0_1',
        correction_url='https://link.springer.com/chapter/10.1007/978-3-031-48803-0_41',
        correction_scope='Open-access status; no numerical correction identified in official notice',
        source_hashes={str(p.relative_to(ROOT)):sha(p) for p in [pdf, SRC/'main.pdf']},
        script_sha256=sha(Path(__file__)), independent_pdfplumber_version=alt['pdfplumber_version'],
        numpy_version=np.__version__, matplotlib_version=matplotlib.__version__,
        pdftotext_version=subprocess.run(['pdftotext','-v'],capture_output=True,text=True).stderr.splitlines()[0],
        visual_review='Supplement page 2 table inspected, including units and endpoints. SD [-] unresolved.',
        scope='Independent measured active-state example, not calibration of original GPU-only curves.')
    (OUT/'source_snapshot.json').write_text(json.dumps(manifest,indent=2)+'\n')
    plot(blocks, idle_upper_screen)
    print(json.dumps(audit, indent=2))


def plot(blocks, idle_upper_screen):
    plt.rcParams.update({'font.family':'DejaVu Sans', 'font.size':10, 'axes.spines.top':False,
                         'axes.spines.right':False, 'pdf.fonttype':42, 'svg.fonttype':'none'})
    fig, axes = plt.subplots(1, 3, figsize=(13, 4.3))
    colors = ['#386cb0','#008878','#dd8c24','#a44c86']
    caps = np.arange(100,261,10)
    for (n,b), color in zip(blocks.items(),colors):
        p,t,e = (np.array(b[k]) for k in ['whole_node_power_w','runtime_s','energy_kj'])
        axes[0].plot(caps,p,'o-',ms=3,color=color,label=f'{n} active GPU'+('s' if n>1 else ''))
        axes[1].plot(caps,100*(1-e/e[-1]),'o-',ms=3,color=color)
        idle=np.linspace(0,idle_upper_screen,151)
        horizon=max(t)
        totals=e[:,None]+idle[None,:]*(horizon-t[:,None])/1000
        best=caps[np.argmin(totals,axis=0)]
        axes[2].step(idle,best,where='mid',color=color)
    axes[0].set(xlabel='GPU power cap (W per active GPU)',ylabel='Measured whole-node power (W)',title='a  Whole-machine measurement')
    axes[0].legend(frameon=False,fontsize=9)
    axes[1].set(xlabel='GPU power cap (W per active GPU)',ylabel='Active-interval energy reduction (%)',title='b  Relative to 260 W in each group')
    axes[1].axhline(0,color='.6',lw=.7)
    axes[2].set(xlabel='Hypothetical constant node idle power (W)',ylabel='Selected cap (W per active GPU)',title='c  Common-horizon sensitivity')
    fig.text(.05,.025,'One server and workload; published means. Panel c: hypothetical constant idle; horizon = slowest measured mode in each group.',fontsize=9)
    fig.tight_layout(rect=[0,.08,1,1])
    for ext in ['png','pdf','svg']:
        fig.savefig(OUT/f'whole_node_boundary_diagnostic.{ext}',dpi=180)
    plt.close(fig)


if __name__ == '__main__':
    main()
