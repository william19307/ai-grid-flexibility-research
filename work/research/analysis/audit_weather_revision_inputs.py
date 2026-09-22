"""Read-only audit of cached weather inputs and legacy calendar/validation scope."""
from pathlib import Path
import ast
import csv
import hashlib
import json
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[3]
PREP=ROOT/'work/research/prepared'
OUT=ROOT/'outputs/research/revision/weather_input_audit'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    sites=pd.read_csv(PREP/'openmeteo_sites_three_provinces.csv')
    old=pd.read_csv(PREP/'re_profiles_2015_2024_three_provinces.csv.gz',index_col=0,parse_dates=True)
    original_audit=ROOT/'outputs/research/tables/multiyear_re_profiles_audit.json'
    levels=json.loads(original_audit.read_text())
    expected=pd.date_range('2015-01-01','2024-12-31 23:00',freq='h')
    assert old.index.equals(expected)
    sums={};weights={};records=[];used=set();missing_total=0;errors=[]
    for _,s in sites.iterrows():
        key=hashlib.md5(f'{s.lat:.3f},{s.lon:.3f},{(2015,2024)}'.encode()).hexdigest()
        path=PREP/'openmeteo_cache'/f'{key}.json'
        used.add(path.name)
        d=json.loads(path.read_text());h=d['hourly']
        t=pd.DatetimeIndex(h['time'])
        if not t.equals(expected):errors.append(f'Calendar mismatch: {path.name}')
        if d.get('utc_offset_seconds')!=28800 or d.get('timezone')!='Asia/Shanghai':
            errors.append(f'Timezone mismatch: {path.name}')
        units=d['hourly_units']
        expected_units={'wind_speed_100m':'km/h','shortwave_radiation':'W/m²','temperature_2m':'°C'}
        if any(units[k]!=v for k,v in expected_units.items()):errors.append(f'Unit mismatch: {path.name}')
        missing={k:int(np.sum(~np.isfinite(np.asarray(h[k],float)))) for k in expected_units}
        missing_total+=sum(missing.values())
        if s.tech=='wind':
            v=np.asarray(h['wind_speed_100m'],float)/3.6
            cf=.85*np.where(v<3,0,np.where(v<12,((v-3)/9)**3,np.where(v<25,1.,0)))
        else:
            radiation=np.asarray(h['shortwave_radiation'],float)
            temp=np.asarray(h['temperature_2m'],float)
            cf=np.clip(.85*radiation/1000*(1-.004*np.maximum(temp-25,0)),0,1)
        if not np.isfinite(cf).all():
            errors.append(f'Missing conversion inputs: {path.name}; no imputation performed by audit')
        group=f'{s.province}|{s.tech}'
        sums[group]=sums.get(group,np.zeros(len(expected)))+s.mw*cf
        weights[group]=weights.get(group,0.)+s.mw
        records.append(dict(province=s.province,technology=s.tech,plant=s['name'],capacity_mw=s.mw,
            requested_lat_rounded=float(f'{s.lat:.3f}'),requested_lon_rounded=float(f'{s.lon:.3f}'),
            returned_lat=d.get('latitude'),returned_lon=d.get('longitude'),
            utc_offset_seconds=d.get('utc_offset_seconds'),timezone=d.get('timezone'),
            cache_path=str(path.relative_to(ROOT)),sha256=sha(path),hours=len(t),
            missing_values=missing,model_identifier=d.get('model',d.get('models')),
            model_request_record_present=False,calendar_matches_expected=t.equals(expected)))
    reproduction=[]
    archive_path=PREP/'archive_2020_source_inputs_NOT_calibrated.npz'
    archive=np.load(archive_path,allow_pickle=False)
    for group,weighted in sums.items():
        scale=levels['scaling'][group]['level_scale']
        reconstructed=np.clip(weighted/weights[group]*scale,0,1)
        error=float(np.max(np.abs(reconstructed-old[group].to_numpy())))
        province,technology=group.split('|')
        col=list(archive['provinces']).index(province)
        target=float(np.mean(archive['onwind_pu' if technology=='wind' else 'solar_pu'][:,col]))
        mean_2020=float(np.mean(reconstructed[expected.year==2020]))
        reproduction.append(dict(group=group,max_abs_capacity_factor_error=error,
            selected_capacity_mw=float(weights[group]),selected_share=levels['sites'][group]['top_share'],
            scale=scale,clipped_fraction_all_years=float(np.mean(weighted/weights[group]*scale>1)),
            archive_2020_mean_target=target,post_clip_2020_mean=mean_2020,
            post_clip_mean_relative_difference_pct=100*(mean_2020/target-1)))
        if not error<1e-12:errors.append(f'Published profile mismatch: {group}: {error}')
    # Parse constants without importing runners, which can mutate frozen output.
    runner=ROOT/'work/research/analysis/run_regional_smoke_s0_s1_s2.py'
    tree=ast.parse(runner.read_text());starts=None
    for node in tree.body:
        if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='WEEK_STARTS' for t in node.targets):
            starts=ast.literal_eval(node.value)
    assert starts is not None
    calendars=[]
    for year in range(2015,2025):
        dates=pd.date_range(f'{year}-01-01',f'{year}-12-31 23:00',freq='h')
        # Exactly mirror the legacy ordinal-hour mapping, retaining provenance.
        fitted=dates if len(dates)==8784 else dates.append(dates[-24:])
        assert len(fitted)==8784
        for season,start in starts.items():
            reference=pd.Timestamp('2020-01-01')+pd.Timedelta(hours=start)
            actual=fitted[start]
            calendars.append(dict(weather_year=year,season=season,start_hour=start,
                reference_start=str(reference),source_start=str(actual),source_end=str(fitted[start+167]),
                source_weekday=actual.day_name(),reference_weekday=reference.day_name(),
                same_month_day=(actual.month,actual.day)==(reference.month,reference.day),
                source_year_hours=len(dates),legacy_padded_hours=8784-len(dates)))
    builder=ROOT/'work/research/analysis/build_multiyear_re_profiles.py'
    regional=ROOT/'work/research/analysis/run_regional_2030_s0_s3.py'
    weather=ROOT/'work/research/analysis/run_2030_multiweather.py'
    code=builder.read_text()
    urls=[line.strip() for line in code.splitlines() if 'url=' in line and 'archive-api' in line]
    assert len(urls)==1
    results_path=ROOT/'outputs/research/tables/regional_2030_multiweather.csv'
    legacy_results=pd.read_csv(results_path)
    expected_runs={(p,i,y) for p in ['Gansu','Jiangsu','Guizhou'] for i in [.25,.41] for y in range(2015,2025)}
    observed_runs=set(legacy_results[['province','idle','weather_year']].itertuples(index=False,name=None))
    pilot_manifest_path=OUT/'explicit_era5_pilot_manifest.json'
    pilot=None
    if pilot_manifest_path.exists():
        manifest=json.loads(pilot_manifest_path.read_text())
        path=ROOT/'work/research/sources/weather_revision_era5/gansu_solar_largest_site_2020_era5.json'
        assert sha(path)==manifest['sha256']
        raw=json.loads(path.read_text());h=raw['hourly']
        assert manifest['explicit_parameters']['models']=='era5'
        assert manifest['explicit_parameters']['wind_speed_unit']=='ms'
        assert pd.DatetimeIndex(h['time']).equals(pd.date_range('2020-01-01','2020-12-31 23:00',freq='h'))
        assert raw['utc_offset_seconds']==28800
        assert raw['hourly_units']['wind_speed_100m']=='m/s'
        # Some responses escape unit labels twice. Keep raw labels in the manifest;
        # accept only the two explicit spellings of the same units here.
        assert raw['hourly_units']['shortwave_radiation'] in ['W/m²',r'W/m\u00b2']
        assert raw['hourly_units']['temperature_2m'] in ['°C',r'\u00b0C']
        ranges={}
        for k in ['wind_speed_100m','shortwave_radiation','temperature_2m']:
            a=np.asarray(h[k],float);assert len(a)==8784 and np.isfinite(a).all()
            ranges[k]=dict(min=float(a.min()),max=float(a.max()),mean=float(a.mean()))
        assert min(h['wind_speed_100m'])>=0 and min(h['shortwave_radiation'])>=0
        canonical={k:v for k,v in raw.items() if k!='generationtime_ms'}
        pilot=dict(explicit_model='era5',hours=8784,all_values_finite=True,ranges=ranges,
            manifest_sha256=sha(pilot_manifest_path),raw_sha256=sha(path),
            scientific_content_sha256=hashlib.sha256(json.dumps(canonical,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
            scope='Single-site request/units/calendar ingestion check; no provincial reconstruction or historical-model difference attribution')
    summary=dict(status='audit_only_no_frozen_inputs_modified',site_rows=len(sites),
        unique_used_cache_files=len(used),all_cache_files=len(list((PREP/'openmeteo_cache').glob('*.json'))),
        expected_hours_2015_2024=len(expected),missing_values_across_site_variable_records=missing_total,
        source_model_identifiers_present=sum(r['model_identifier'] is not None for r in records),
        explicit_models_parameter_in_source_request='models=' in urls[0],
        source_request_expression=urls[0],reproduction=reproduction,
        calendar_season_records=len(calendars),month_day_mismatches=sum(not r['same_month_day'] for r in calendars),
        regional_dispatch_hours_per_weather_case=4*168,
        fixed_investment_out_of_sample_year_validation=False,
        jointly_varied_load_hydro_weather=False,
        legacy_result_rows=len(legacy_results),legacy_missing_configuration_keys=sorted(expected_runs-observed_runs),
        legacy_duplicate_configuration_rows=len(legacy_results)-len(observed_runs),
        explicit_era5_pilot=pilot,
        official_documentation_url='https://open-meteo.com/en/docs/historical-weather-api',
        official_documentation_checked='2026-09-22',
        documentation_finding='Default Best Match combines models; explicit ERA5 or ERA5-Land is advised for long-period consistency. This does not retrospectively identify each cached hour.',
        errors=errors,
        source_hashes={str(p.relative_to(ROOT)):sha(p) for p in [builder,regional,weather,runner,original_audit,
            PREP/'openmeteo_sites_three_provinces.csv',PREP/'re_profiles_2015_2024_three_provinces.csv.gz',results_path,archive_path]},
        audit_script_sha256=sha(Path(__file__)))
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'audit.json').write_text(json.dumps(summary,indent=2)+'\n')
    (OUT/'cache_manifest.json').write_text(json.dumps(records,indent=2)+'\n')
    with (OUT/'legacy_calendar_mapping.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(calendars[0]));w.writeheader();w.writerows(calendars)
    print(json.dumps({k:v for k,v in summary.items() if k!='source_hashes'},indent=2))
    if errors:raise ValueError(errors)


if __name__=='__main__':main()
