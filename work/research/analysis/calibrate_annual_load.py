"""Anchor annual energy, then evaluate unused Jiangsu temporal aggregates.

This does not create independently measured 2020 hourly demand or validate peaks.
Original source arrays remain immutable. No synthetic mock data are consumed.
"""
from pathlib import Path
import hashlib
import json
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / 'work/research/sources'
PREP = ROOT / 'work/research/prepared'
OUT = ROOT / 'outputs/research/tables'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    observation_path = SRC/'nbs_2021/province_electricity_2020_transcription.csv'
    source_path = PREP/'archive_2020_source_inputs_NOT_calibrated.npz'
    observations = pd.read_csv(observation_path).set_index('province')
    with np.load(source_path, allow_pickle=False) as a:
        names = a['provinces'].copy()
        power = a['load_MW'].copy()
        timestamps = a['timestamps_UTC_ns'].copy()
    assert len(observations)==31 and observations.index.is_unique
    assert set(names)==set(observations.index)
    assert power.shape==(8784,31) and np.isfinite(power).all() and (power>=0).all()
    dates = pd.to_datetime(timestamps,unit='ns',utc=True).tz_convert('Asia/Shanghai')
    expected = pd.date_range('2020-01-01',periods=8784,freq='h',tz='Asia/Shanghai',unit='ns')
    assert dates.equals(expected)
    observations = observations.loc[names].copy()
    target = observations.electricity_2020_100million_kWh.to_numpy(dtype=float)/10
    annual = power.sum(axis=0)/1e6
    factors = target/annual
    adjusted = power*factors[None,:]
    assert np.allclose(adjusted.sum(axis=0)/1e6,target,rtol=0,atol=1e-9)
    assert np.allclose(adjusted/adjusted.mean(axis=0),power/power.mean(axis=0),atol=1e-12)
    # Preserve observation precision (0.1 TWh), not spurious exact-meter precision.
    observations['official_2020_TWh']=target
    observations['source_model_2020_TWh']=annual
    observations['source_minus_official_TWh']=annual-target
    observations['source_relative_difference_pct']=100*(annual/target-1)
    observations['annual_scaling_factor']=factors
    observations['adjusted_annual_TWh']=adjusted.sum(axis=0)/1e6
    observations['source_peak_hourly_average_MW']=power.max(axis=0)
    observations['adjusted_peak_hourly_average_MW']=adjusted.max(axis=0)
    observations['hourly_shape_status']='reconstructed_2018_shape_reused_in_source_2020_not_observed_2020'
    observations['source_url']='https://www.stats.gov.cn/sj/ndsj/2021/html/C09-14.jpg'
    observations['source_table']='China Statistical Yearbook 2021, table 9-14; underlying source CEC'
    observations.to_csv(OUT/'provincial_load_2020_annual_calibration.csv')
    np.savez_compressed(PREP/'load_2020_annual_anchored_hourly_shape_UNVALIDATED.npz',
        timestamps_UTC_ns=timestamps, provinces=names,load_MW=adjusted,
        annual_targets_TWh=target,annual_scaling_factors=factors,
        status=np.array('Annual energy anchored; hourly shape NOT independently validated'))

    # These observations are not used to estimate any factor. The cumulative rows
    # overlap monthly rows and one another; they are not independent samples.
    # Full-society electricity matches annual table concept, but report revisions
    # may differ. The grid-dispatch peak is deliberately excluded from error tests.
    period_specs=[
        ('July',7,7,578.53,'js_jul.html','https://jsb.nea.gov.cn/dtyw/jgdt/202309/t20230910_29496.html'),
        ('September',9,9,568.17,'js_sep.html','https://jsb.nea.gov.cn/dtyw/jgdt/202309/t20230910_29528.html'),
        ('October',10,10,524.06,'js_oct.html','https://jsb.nea.gov.cn/dtyw/jgdt/202309/t20230910_29554.html'),
        ('November',11,11,543.73,'js_nov.html','https://jsb.nea.gov.cn/dtyw/jgdt/202309/t20230910_29575.html'),
        ('January-July',1,7,3391.30,'js_jul.html','https://jsb.nea.gov.cn/dtyw/jgdt/202309/t20230910_29496.html'),
        ('January-September',1,9,4662.47,'js_sep.html','https://jsb.nea.gov.cn/dtyw/jgdt/202309/t20230910_29528.html'),
        ('January-October',1,10,5186.53,'js_oct.html','https://jsb.nea.gov.cn/dtyw/jgdt/202309/t20230910_29554.html'),
        ('January-November',1,11,5730.26,'js_nov.html','https://jsb.nea.gov.cn/dtyw/jgdt/202309/t20230910_29575.html'),
    ]
    j = list(names).index('Jiangsu')
    checks=[]
    for label,first,last,obs,filename,url in period_specs:
        local_file=SRC/'official_provincial_2020'/filename
        raw=local_file.read_text()
        assert f'{obs:.2f}' in raw
        mask=(dates.month>=first)&(dates.month<=last)
        actual=obs/10
        initial=power[mask,j].sum()/1e6
        estimate=adjusted[mask,j].sum()/1e6
        checks.append(dict(province='Jiangsu',period=label,year=2020,
            official_electricity_TWh=actual,source_model_TWh=initial,
            annual_anchored_model_TWh=estimate,
            source_error_pct=100*(initial/actual-1),
            annual_anchored_error_pct=100*(estimate/actual-1),
            used_for_calibration=False,annual_calibration_total_overlaps_this_period=True,
            overlapping_evidence_not_independent_samples=True,
            source_url=url,source_local_file=str(local_file),source_sha256=sha(local_file)))
    pd.DataFrame(checks).to_csv(OUT/'jiangsu_2020_unused_temporal_checks.csv',index=False)
    errors=observations.source_relative_difference_pct
    summary={
      'status':'annual_energy_anchored; temporal_diagnostics_do_not_validate_hourly_shape',
      'year':2020,'hours':8784,'provinces':31,
      'annual_source_total_TWh':float(annual.sum()),
      'official_provincial_sum_TWh':float(target.sum()),
      'previous_national_comparator_TWh':7511.0,
      'provincial_sum_minus_previous_national_TWh':float(target.sum()-7511),
      'national_relative_difference_pct_using_province_sum':float(100*(annual.sum()/target.sum()-1)),
      'province_unweighted_mean_absolute_difference_pct':float(abs(errors).mean()),
      'province_energy_weighted_absolute_difference_pct':float(100*np.abs(annual-target).sum()/target.sum()),
      'province_min_relative_difference_pct':float(errors.min()),
      'province_max_relative_difference_pct':float(errors.max()),
      'province_count_absolute_difference_over_5pct':int((abs(errors)>5).sum()),
      'largest_absolute_difference_province':str(abs(errors).idxmax()),
      'calibration_max_annual_residual_TWh':float(abs(adjusted.sum(axis=0)/1e6-target).max()),
      'annual_fit_is_validation':False,
      'source_table_resolution_TWh':0.1,
      'rounding_note':'Provincial cells and national value are reported in units of 0.1 TWh. Under nearest rounding, 31 cells plus one national value could differ by at most 1.6 TWh; observed 10.4 TWh cannot be attributed solely to that rounding. Revision/scope discrepancy remains unresolved; preserve both sources.',
      'unused_temporal_checks':checks,
      'limitations':[
        'Annual targets are calibration inputs, not held-out validation evidence.',
        'Original hourly shapes are reconstructed and almost identical to 2018, not contemporaneous 2020 measurements.',
        'The four unused months are limited temporal diagnostics, not a full-year hourly or peak validation.',
        'Cumulative checks overlap the monthly checks and may share underlying utility data with the yearbook.',
        'The fitted annual total contains these months, so these checks are not strict out-of-sample prediction tests; the monthly values were not separate fitting targets.',
        'No statistical confidence intervals are inferred from eight overlapping aggregates.',
        'Annual all-society electricity requires auxiliary-consumption and grid-loss reconciliation before dispatch balance.',
        'AI base-year load is already embedded in all-society demand; adding a future AI total would double count without a consistent incremental-demand construction.',
      ],
      'provenance':{
        'official_table_image_url':'https://www.stats.gov.cn/sj/ndsj/2021/html/C09-14.jpg',
        'official_table_image_sha256':sha(SRC/'nbs_2021/C09-14.jpg'),
        'transcription_sha256':sha(observation_path),
        'source_array_sha256':sha(source_path),
        'script_sha256':sha(Path(__file__)),
        'transcription_method':'Manual transcription of 2019 and 2020 columns; original full image visually inspected.',
      },
    }
    (OUT/'provincial_load_2020_calibration_audit.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2))
    print(json.dumps(summary,ensure_ascii=False,indent=2))

if __name__=='__main__':
    main()
