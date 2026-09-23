"""Frozen exploratory annual transfer; never silently clip calibrated power."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
from compare_wind_reference_shapes import ROOT, SRC, read_curve, convert, sha

OUT = ROOT/'outputs/research/revision/rudong_h2_validation'
WEATHER = ROOT/'work/research/sources/rudong_h2_observations_20260923/weather'
PLAN_SHA = 'eba200c098e820096c9701afd0412e0a1a2496cde0ca74f14fdedc6ee77d13cd'


def main():
    if sha(OUT/'site_weather_plan.json') != PLAN_SHA:
        raise ValueError('Changed frozen plan')
    plan = json.loads((OUT/'site_weather_plan.json').read_text())
    if sha(OUT/'observation_audit.json') != plan['observation_audit_sha256']:
        raise ValueError('Changed observation audit')
    observation_audit = json.loads((OUT/'observation_audit.json').read_text())
    if sha(OUT/'annual_observations.csv') != observation_audit['output_sha256']:
        raise ValueError('Changed audited observations')
    observations = pd.read_csv(OUT/'annual_observations.csv').set_index('year')
    manifest = json.loads((ROOT/'outputs/research/revision/wind_conversion_v1/source_manifest.json').read_text())
    curves = {'legacy_generic': None}
    for name in ['Vestas_V112_3MW.yaml', 'NREL_ReferenceTurbine_5MW_offshore.yaml']:
        if sha(SRC/name) != manifest[name]['sha256']:
            raise ValueError('Changed curve')
        curves[name.removesuffix('.yaml')] = read_curve(SRC/name)
    scales, records, frames, sources = {}, [], [], []
    for req in plan['requests']:
        year = req['year']
        raw = WEATHER/(req['id']+'.json')
        meta = json.loads(raw.with_suffix('.meta.json').read_text())
        if sha(raw) != meta['validation']['raw_sha256'] or req != meta['request']:
            raise ValueError('Changed weather')
        data = json.loads(raw.read_text())
        expected = pd.date_range(f'{year}-01-01', f'{year+1}-01-01 23:00', freq='h')
        if data['hourly']['time'] != expected.strftime('%Y-%m-%dT%H:%M').tolist():
            raise ValueError('Calendar mismatch')
        if data['hourly_units']['wind_speed_100m'] != 'm/s' or data['utc_offset_seconds'] != 28800:
            raise ValueError('Units/timezone mismatch')
        clock = pd.date_range(f'{year}-01-01', f'{year+1}-01-01', inclusive='left', freq='h', tz='Asia/Shanghai')
        speed = np.asarray(data['hourly']['wind_speed_100m'][:len(clock)+1], float)
        obs = float(observations.loc[year, 'gross_generation_mwh'])
        columns = {}
        for name, curve in curves.items():
            endpoint = convert(speed, curve)
            cf = (endpoint[:-1]+endpoint[1:])/2
            energy = float(cf.sum()*350)
            if year == 2022:
                scales[name] = obs/energy
            scaled = cf*scales[name]
            columns[name+'|unscaled_pu'] = cf
            columns[name+'|scaled_pu'] = scaled
            records.append(dict(year=year, curve=name, hours=len(cf), observed_gross_mwh=obs,
                                unscaled_mwh=energy, unscaled_error_pct=100*(energy/obs-1),
                                frozen_2022_scale=scales[name], scaled_mwh=float(scaled.sum()*350),
                                scaled_error_pct=float(100*(scaled.sum()*350/obs-1)),
                                scaled_min_pu=float(scaled.min()), scaled_max_pu=float(scaled.max()),
                                scaled_hours_above_one=int((scaled>1+1e-12).sum()),
                                scaled_endpoint_samples_above_one=int((endpoint*scales[name]>1+1e-12).sum()),
                                excess_above_nameplate_mwh=float(np.maximum(scaled-1,0).sum()*350),
                                temporal_role='fit' if year==2022 else 'exploratory_transfer'))
        frames.append(pd.DataFrame(columns, index=clock))
        sources.append(dict(year=year, request_id=req['id'], raw_sha256=sha(raw),
                            meta_sha256=sha(raw.with_suffix('.meta.json')),
                            returned_latitude=data['latitude'], returned_longitude=data['longitude']))
    frame = pd.concat(frames)
    frame.index.name = 'interval_start_local'
    dest = ROOT/'work/research/prepared/rudong_h2_2022_2024_EXPLORATORY.csv.gz'
    frame.to_csv(dest, compression=dict(method='gzip', mtime=0))
    summary = pd.DataFrame(records)
    summary.to_csv(OUT/'transfer_comparison.csv', index=False)
    audit = dict(plan_sha256=PLAN_SHA, builder_sha256=sha(Path(__file__)),
                 observations_sha256=sha(OUT/'annual_observations.csv'), weather_sources=sources,
                 curve_sources={k: manifest[k]['sha256'] for k in manifest if k.endswith('.yaml')},
                 profile_path=str(dest.relative_to(ROOT)), profile_sha256=sha(dest),
                 summary_sha256=sha(OUT/'transfer_comparison.csv'),
                 cases=len(records), hourly_values=int(frame.size),
                 admission='EXPLORATORY_ANNUAL_TRANSFER_ONLY; hourly or provincial validation not established',
                 physically_rejected_curves=summary.loc[(summary.scaled_hours_above_one>0)|(summary.scaled_endpoint_samples_above_one>0),'curve'].unique().tolist(),
                 assumptions=['Fixed 100m wind and common 0.85 multiplier; no actual manufacturer curve',
                              'Trapezoidal power endpoints are an integration approximation, not measured hourly means',
                              'Company offshore aggregate mapped to H2 by documentary inference',
                              'All observed years were seen before freezing plan; not blind holdout',
                              'No clipping, model selection or flat time-availability energy correction'])
    (OUT/'transfer_audit.json').write_text(json.dumps(audit, indent=2)+'\n')
    print(summary.to_string(index=False))


if __name__ == '__main__':
    main()
