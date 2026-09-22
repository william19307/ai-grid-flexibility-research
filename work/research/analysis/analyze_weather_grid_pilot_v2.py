"""Independently audit the frozen eight-response pilot, without acquisition imports.

This verifies downloaded records and describes paired grid selection. It does
not infer generation, fit a correction, or release the full acquisition gate.
"""
from collections import defaultdict
from datetime import datetime, timedelta
from fractions import Fraction
from hashlib import sha256
from pathlib import Path
import csv
import json
import math
import statistics

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'outputs/research/revision/weather_fleet_v2'
SRC = ROOT / 'work/research/sources/weather_fleet_revision_v2/pilot'
FROZEN_PLAN = '679acfd3aa2d5acdd38e860f3b1000a8a07edbe6a511f3153f64c51e58539583'
UNITS = {
    'wind_speed_100m': 'm/s', 'wind_speed_10m': 'm/s',
    'shortwave_radiation': 'W/m²', 'direct_radiation': 'W/m²',
    'diffuse_radiation': 'W/m²', 'temperature_2m': '°C',
    'surface_pressure': 'hPa',
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(content):
    return sha256(content).hexdigest()


def nearest_quarter(value):
    return float(Fraction(math.floor(Fraction(str(value)) * 4 + Fraction(1, 2)), 4))


def main():
    plan_bytes = (OUT / 'pilot_plan.json').read_bytes()
    require(digest(plan_bytes) == FROZEN_PLAN, 'Plan differs from pre-acquisition freeze')
    plan = json.loads(plan_bytes)
    acquisition = json.loads((OUT / 'pilot_acquisition.json').read_text())
    require(acquisition['plan_sha256'] == FROZEN_PLAN, 'Acquisition plan mismatch')
    require(acquisition['completed'] == 8 and acquisition['pending'] == 0, 'Incomplete pilot')
    require(digest((ROOT / 'work/research/analysis/acquire_weather_grid_pilot_v2.py').read_bytes())
            == acquisition['acquirer_sha256'], 'Acquisition source changed')
    require(len(plan['pilot_requests']) == 8, 'Unexpected pilot size')
    require(plan['full_grid_acquisition_authorized_by_this_plan'] is False, 'Scope changed')
    acquisitions = {r['request']['id']: r for r in acquisition['records']}
    require(len(acquisitions) == 8, 'Duplicate acquisition IDs')
    first = datetime(2020, 1, 1)
    calendar = [(first + timedelta(hours=i)).isoformat(timespec='minutes') for i in range(8808)]
    groups = defaultdict(list)
    records = []
    numeric_checks = 0
    for req in plan['pilot_requests']:
        rid, params = req['id'], req['parameters']
        require(set(params['hourly'].split(',')) == set(UNITS), 'Variable selection changed')
        require(params['models'] == 'era5' and params['elevation'] == 'nan', 'Model boundary changed')
        canonical_params = json.dumps(params, sort_keys=True, separators=(',', ':')).encode()
        require(digest(canonical_params)[:24] == rid, 'Request ID mismatch')
        raw = (SRC / (rid + '.json')).read_bytes()
        meta_bytes = (SRC / (rid + '.meta.json')).read_bytes()
        meta = json.loads(meta_bytes)
        require(meta['request'] == req and meta == acquisitions[rid], 'Metadata mismatch')
        require(digest(raw) == meta['validation']['raw_sha256'], 'Raw response changed')
        require(len(raw) == meta['validation']['bytes'], 'Response length mismatch')
        data = json.loads(raw)
        scientific = {k: v for k, v in data.items() if k != 'generationtime_ms'}
        scientific_hash = digest(json.dumps(scientific, sort_keys=True, separators=(',', ':')).encode())
        require(scientific_hash == meta['validation']['scientific_content_sha256'], 'Scientific hash mismatch')
        require(data['timezone'] == 'Asia/Shanghai' and data['utc_offset_seconds'] == 28800, 'Timezone mismatch')
        require(data['hourly']['time'] == calendar, 'Missing, duplicate or shifted hour')
        require(meta['validation']['hours'] == len(calendar) == req['expected_hours'], 'Hour count mismatch')
        require(data['hourly_units']['time'] == 'iso8601', 'Time encoding mismatch')
        for variable, unit in UNITS.items():
            require(data['hourly_units'][variable] == unit, 'Unit mismatch: ' + variable)
            values = data['hourly'][variable]
            require(len(values) == 8808, 'Length mismatch: ' + variable)
            for value in values:
                require(type(value) in (int, float) and math.isfinite(value), 'Missing/nonfinite value')
                if variable != 'temperature_2m':
                    require(value >= 0, 'Negative physical input: ' + variable)
                if variable == 'surface_pressure':
                    require(value > 0, 'Nonpositive pressure')
                numeric_checks += 1
        expected_grid = [nearest_quarter(params['latitude']), nearest_quarter(params['longitude'])]
        returned_grid = [data['latitude'], data['longitude']]
        records.append(dict(id=rid, raw_sha256=digest(raw), meta_sha256=digest(meta_bytes),
                            scientific_content_sha256=scientific_hash, hours=8808,
                            returned_grid=returned_grid, expected_nearest_grid=expected_grid,
                            nearest_grid_matches=returned_grid == expected_grid))
        groups[(req['province'], req['technology_group'], req['unit_id'])].append((req, data))
    require(len(groups) == 4 and all(len(v) == 2 for v in groups.values()), 'Broken pair design')
    pairs, differences = [], []
    for key, entries in groups.items():
        selections = {r['parameters']['cell_selection']: (r, d) for r, d in entries}
        preference = 'sea' if key[1] == 'wind_offshore' else 'land'
        require(set(selections) == {'nearest', preference}, 'Unexpected paired selection')
        req, base = selections['nearest']
        other_req, other = selections[preference]
        require({k: v for k, v in req['parameters'].items() if k != 'cell_selection'} ==
                {k: v for k, v in other_req['parameters'].items() if k != 'cell_selection'},
                'Parameters other than selection differ')
        all_equal = True
        for variable in UNITS:
            delta = [b - a for a, b in zip(base['hourly'][variable], other['hourly'][variable])]
            changed = sum(x != 0 for x in delta)
            all_equal = all_equal and changed == 0
            differences.append(dict(province=key[0], technology=key[1], unit_id=key[2],
                                    preference=preference, variable=variable, unit=UNITS[variable],
                                    compared_hours=len(delta), changed_hours=changed,
                                    maximum_absolute_difference=max(map(abs, delta)),
                                    mean_signed_difference=statistics.fmean(delta)))
        # Descriptive instantaneous 100 m wind; excludes the extra Jan 1 boundary day.
        wind = base['hourly']['wind_speed_100m'][:8784]
        pairs.append(dict(province=key[0], technology=key[1], unit_id=key[2],
                          nearest_request=req['id'], preference_request=other_req['id'],
                          same_returned_coordinates=all(base[k] == other[k] for k in ('latitude', 'longitude')),
                          same_returned_elevation=base['elevation'] == other['elevation'],
                          all_seven_hourly_arrays_identical=all_equal,
                          returned_latitude=base['latitude'], returned_longitude=base['longitude'],
                          returned_elevation_m=base['elevation'],
                          year2020_mean_100m_wind_ms=statistics.fmean(wind),
                          year2020_fraction_100m_wind_below_3ms=sum(v < 3 for v in wind) / len(wind)))
    with (OUT / 'pilot_paired_differences.csv').open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(differences[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(differences)
    result = dict(status='PASS', plan_sha256=FROZEN_PLAN,
                  acquisition_sha256=digest((OUT / 'pilot_acquisition.json').read_bytes()),
                  analyzer_sha256=digest(Path(__file__).read_bytes()),
                  responses_checked=len(records), scalar_values_checked=numeric_checks,
                  independent_hourly_pair_comparisons=4 * 7 * 8808,
                  response_checks=records, pair_results=pairs,
                  limits=[
                      'Frozen largest-unit selection is a four-location methodological pilot, not a representative sample.',
                      'Equality concerns these requests with elevation=nan; it does not establish equality for other sites or old elevation settings.',
                      'Checking all returned numbers is not independent validation of ERA5 or the API implementation.',
                      'No turbine conversion, generated electricity, uncertainty interval or calibrated regional profile is inferred.',
                      'Full-grid acquisition gate remains closed pending coordinates and technology-specific physical conversion.'
                  ])
    (OUT / 'pilot_independent_analysis.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k: result[k] for k in ('status', 'responses_checked', 'scalar_values_checked',
                                          'independent_hourly_pair_comparisons', 'pair_results')}, indent=2))


if __name__ == '__main__':
    main()
