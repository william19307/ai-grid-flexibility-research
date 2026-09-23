"""Frozen, same-weather curve-shape diagnostic; no generation calibration."""
from pathlib import Path
import ast
import hashlib
import json
import re
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'outputs/research/revision/wind_conversion_v1'
SRC = ROOT / 'work/research/sources/wind_conversion_revision_20260923'
WEATHER = ROOT / 'work/research/sources/weather_fleet_revision_v2/pilot'
PLAN_SHA = '0e63f094829af82f8545a4954880bd75e9bc7ec73b3ddaa6b10e35097ef083e0'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_curve(path):
    text = path.read_text()
    values = {key: ast.literal_eval(re.search(r'^' + key + r': (.+)$', text, re.M)[1])
              for key in ['V', 'POW', 'HUB_HEIGHT']}
    v, power = np.asarray(values['V'], float), np.asarray(values['POW'], float)
    if len(v) != len(power) or (np.diff(v) < 0).any() or power.min() < 0 or power[-1] != 0:
        raise ValueError('Invalid reference curve')
    return v, power, values['HUB_HEIGHT']


def convert(speed, curve=None):
    speed = np.asarray(speed, float)
    if not np.isfinite(speed).all() or (speed < 0).any():
        raise ValueError('Invalid speed')
    if curve is None:
        return .85 * np.where(speed < 3, 0, np.where(speed < 12, ((speed-3)/9)**3,
                                                   np.where(speed < 25, 1., 0)))
    v, power, _ = curve
    return .85 * np.interp(speed, v, power / max(power), left=0, right=0)


def main():
    if sha(OUT/'conversion_plan.json') != PLAN_SHA:
        raise ValueError('Changed conversion plan')
    manifest = json.loads((OUT/'source_manifest.json').read_text())
    for name, m in manifest.items():
        if sha(SRC/name) != m['sha256']:
            raise ValueError('Changed source ' + name)
    plan = json.loads((OUT/'conversion_plan.json').read_text())
    curves = {'legacy_generic': None}
    curves.update({name.removesuffix('.yaml'): read_curve(SRC/name) for name in plan['curves']})
    p = ROOT/'outputs/research/revision/weather_fleet_v2/pilot_plan.json'
    if sha(p) != plan['weather_plan_sha256']:
        raise ValueError('Changed weather plan')
    weather_plan = json.loads(p.read_text())
    records, columns, sources = [], {}, []
    clock = pd.date_range('2020-01-01', '2021-01-01', inclusive='left', freq='h', tz='Asia/Shanghai')
    expected = pd.date_range('2020-01-01', '2021-01-01 23:00', freq='h').strftime('%Y-%m-%dT%H:%M').tolist()
    for req in weather_plan['pilot_requests']:
        if req['parameters']['cell_selection'] != 'nearest':
            continue
        raw = WEATHER/(req['id']+'.json')
        meta = json.loads(raw.with_suffix('.meta.json').read_text())
        if sha(raw) != meta['validation']['raw_sha256'] or meta['request'] != req:
            raise ValueError('Changed weather response')
        data = json.loads(raw.read_text())
        if data['hourly']['time'] != expected or data['hourly_units']['wind_speed_100m'] != 'm/s':
            raise ValueError('Calendar or units mismatch')
        speed = np.asarray(data['hourly']['wind_speed_100m'][:8785], float)
        group = req['province']+'|'+req['technology_group']
        baseline = None
        for name, curve in curves.items():
            points = convert(speed, curve)
            cf = (points[:-1]+points[1:])/2
            if len(cf) != 8784 or not np.isfinite(cf).all() or cf.min() < 0 or cf.max() > .85+1e-12:
                raise ValueError('Invalid output')
            if baseline is None:
                baseline = cf
            columns[group+'|'+name] = cf
            records.append(dict(group=group, unit_id=req['unit_id'], curve=name,
                                input_height_m=100, applied_hub_extrapolation=False,
                                reference_hub_height_m=curve[2] if curve else None,
                                normalization_mw=float(max(curve[1])) if curve else None,
                                common_assumed_multiplier=.85, mean_pu=float(cf.mean()),
                                equivalent_hours=float(cf.sum()),
                                mean_difference_from_generic=float((cf-baseline).mean()),
                                relative_mean_difference_pct=float(100*(cf.mean()/baseline.mean()-1)),
                                max_hourly_difference_from_generic=float(np.max(abs(cf-baseline)))))
        sources.append(dict(group=group, request_id=req['id'], raw_sha256=sha(raw),
                            meta_sha256=sha(raw.with_suffix('.meta.json'))))
    if len(columns) != 12:
        raise ValueError('Missing comparison condition')
    dest = ROOT/'work/research/prepared/wind_reference_shapes_2020_UNCALIBRATED.csv.gz'
    frame = pd.DataFrame(columns, index=clock)
    frame.index.name='interval_start_local'
    frame.to_csv(dest, compression=dict(method='gzip', mtime=0))
    pd.DataFrame(records).to_csv(OUT/'shape_comparison.csv', index=False)
    result = dict(plan_sha256=PLAN_SHA, builder_sha256=sha(Path(__file__)),
                  source_manifest_sha256=sha(OUT/'source_manifest.json'),
                  output_path=str(dest.relative_to(ROOT)), output_sha256=sha(dest),
                  summary_sha256=sha(OUT/'shape_comparison.csv'), weather_sources=sources,
                  conditions=len(records), interval_hours=8784, results=records,
                  admission='UNVALIDATED_CURVE_SHAPE_DIAGNOSTIC_ONLY')
    (OUT/'comparison_audit.json').write_text(json.dumps(result, indent=2)+'\n')
    print(pd.DataFrame(records)[['group','curve','mean_pu','equivalent_hours','relative_mean_difference_pct']].to_string(index=False))


if __name__ == '__main__':
    main()
