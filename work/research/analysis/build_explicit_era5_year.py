"""Build complete interval-aligned generic profiles from verified explicit ERA5.

No generation calibration is claimed. Wind uses endpoint-mean power factors;
solar uses trailing-hour irradiance at the right endpoint and mean endpoint air
temperature. These conversion assumptions require plant/observation validation.
"""
import argparse,csv,json
import numpy as np
import pandas as pd
from rebuild_explicit_era5 import ROOT,SRC,OUT,SITES,plan,existing,digest,canonical,save


def wind(v):
    return .85*np.where(v<3,0,np.where(v<12,((v-3)/9)**3,np.where(v<25,1.,0)))


def solar(ghi,temp):return np.clip(.85*ghi/1000*(1-.004*np.maximum(temp-25,0)),0,1)


def intervals(v,ghi,temp):
    v,ghi,temp=[np.asarray(x,float) for x in [v,ghi,temp]]
    if len(v)<2 or v.ndim!=1 or v.shape!=ghi.shape or v.shape!=temp.shape:raise ValueError('Need matching endpoint observations')
    if not all(np.isfinite(x).all() for x in [v,ghi,temp]) or (v<0).any() or (ghi<0).any():raise ValueError('Invalid input values')
    return .5*(wind(v[:-1])+wind(v[1:])),solar(ghi[1:],.5*(temp[:-1]+temp[1:]))


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--year',type=int,required=True);args=parser.parse_args()
    p=plan();requests=[r for r in p['requests'] if r['year']==args.year]
    if len(requests)!=p['unique_requested_coordinates']:raise ValueError('Incomplete year plan')
    boundary_path=OUT/f'boundary_plan_{args.year}.json'
    boundaries=json.loads(boundary_path.read_text())
    boundary_by_point={(r['parameters']['latitude'],r['parameters']['longitude']):r for r in boundaries}
    series={};provenance=[];clock=None
    for req in requests:
        point=(req['parameters']['latitude'],req['parameters']['longitude'])
        br=boundary_by_point[point];meta=existing(req);bm=existing(br)
        if meta is None or bm is None:raise ValueError(f'Incomplete year or boundary: {point}; no partial-year profile emitted')
        h=json.loads((SRC/(req['id']+'.json')).read_text())['hourly']
        next_h=json.loads((SRC/(br['id']+'.json')).read_text())['hourly']
        t=pd.DatetimeIndex(h['time']).tz_localize('Asia/Shanghai')
        next_time=pd.Timestamp(next_h['time'][0]).tz_localize('Asia/Shanghai')
        if next_time!=t[-1]+pd.Timedelta(hours=1):raise ValueError('Boundary is not next consecutive hour')
        if clock is None:clock=t
        elif not clock.equals(t):raise ValueError('Site calendars differ')
        v,ghi,temp=[np.r_[h[k],next_h[k][0]] for k in ['wind_speed_100m','shortwave_radiation','temperature_2m']]
        wc,sc=intervals(v,ghi,temp)
        series[point]=dict(wind=wc,solar=sc,legacy_wind=wind(v[:-1]),legacy_solar=solar(ghi[:-1],temp[:-1]))
        provenance.append(dict(point=point,year_request=req['id'],boundary_request=br['id'],
            year_raw_sha256=meta['validation']['raw_sha256'],boundary_raw_sha256=bm['validation']['raw_sha256']))
    sites=pd.read_csv(SITES);aligned={};legacy={};weights={}
    for _,s in sites.iterrows():
        point=(f'{s.lat:.3f}',f'{s.lon:.3f}');group=f'{s.province}|{s.tech}';values=series[point]
        aligned[group]=aligned.get(group,np.zeros(len(clock)))+s.mw*values[s.tech]
        legacy[group]=legacy.get(group,np.zeros(len(clock)))+s.mw*values['legacy_'+s.tech]
        weights[group]=weights.get(group,0)+s.mw
    old=pd.read_csv(ROOT/'work/research/prepared/re_profiles_2015_2024_three_provinces.csv.gz',index_col=0,parse_dates=True)
    old=old[old.index.year==args.year]
    if not old.index.tz_localize('Asia/Shanghai').equals(clock):raise ValueError('Legacy comparison calendar differs')
    levels=json.loads((ROOT/'outputs/research/tables/multiyear_re_profiles_audit.json').read_text())
    summary=[]
    for group in aligned:
        aligned[group]/=weights[group];legacy[group]/=weights[group]
        updated_legacy=np.clip(legacy[group]*levels['scaling'][group]['level_scale'],0,1)
        orig=old[group].to_numpy()
        summary.append(dict(group=group,aligned_unscaled_mean=float(aligned[group].mean()),
            same_conversion_fixed_legacy_scale_mean=float(updated_legacy.mean()),old_profile_mean=float(orig.mean()),
            source_refresh_diagnostic_rmse=float(np.sqrt(np.mean((updated_legacy-orig)**2))),
            source_refresh_diagnostic_correlation=float(np.corrcoef(updated_legacy,orig)[0,1]),
            interval_rule_change_unscaled_rmse=float(np.sqrt(np.mean((aligned[group]-legacy[group])**2)))))
    # Independent tiny integration example: preceding-hour radiation must move
    # into the interval that ends at its timestamp; the first value is unused.
    w,s=intervals([3,12,25],[999,1000,500],[25,25,25])
    assert np.allclose(w,[.425,.425]) and np.allclose(s,[.85,.425])
    expected=pd.date_range(f'{args.year}-01-01',f'{args.year+1}-01-01',inclusive='left',freq='h',tz='Asia/Shanghai')
    assert clock.equals(expected)
    df=pd.DataFrame(aligned,index=clock);df.index.name='interval_start_local'
    assert np.isfinite(df.to_numpy()).all() and ((df.to_numpy()>=0)&(df.to_numpy()<=1)).all()
    dest=OUT/f'profiles_{args.year}_generic_INTERVAL_ALIGNED_UNCALIBRATED.csv.gz'
    df.to_csv(dest,compression=dict(method='gzip',mtime=0))
    diagnostic=OUT/f'source_refresh_diagnostic_{args.year}.csv'
    diagnostic_rows=[dict(group=x['group'],old_mean_cf=x['old_profile_mean'],
        new_source_same_conversion_and_fixed_scale_mean_cf=x['same_conversion_fixed_legacy_scale_mean'],
        relative_mean_difference_pct=100*(x['same_conversion_fixed_legacy_scale_mean']/x['old_profile_mean']-1),
        correlation=x['source_refresh_diagnostic_correlation']) for x in summary]
    with diagnostic.open('w') as f:
        writer=csv.DictWriter(f,fieldnames=list(diagnostic_rows[0]),lineterminator='\n');writer.writeheader();writer.writerows(diagnostic_rows)
    report=dict(year=args.year,hours=len(clock),source_sites=len(sites),source_coordinates=len(series),
        complete_year_and_boundary_verified=True,interpolation_or_day_padding=False,
        generic_conversion_not_generation_calibration=True,
        wind_rule='Mean of endpoint generic power factors; assumes linear power interpolation within hour',
        solar_rule='Preceding-hour GHI at interval right endpoint; average endpoint air-temperature derating',
        calibration='None; no archive-level scaling applied to exported aligned profile',
        comparison_scope='Exploratory compound source refresh, API/unit rounding and grid-selection differences; not isolated causal model effect',
        summaries=summary,sources=provenance,
        output_sha256=digest(dest.read_bytes()),diagnostic_sha256=digest(diagnostic.read_bytes()),
        builder_sha256=digest(__import__('pathlib').Path(__file__).read_bytes()),
        plan_sha256=digest((OUT/'request_plan.json').read_bytes()),boundary_plan_sha256=digest(boundary_path.read_bytes()))
    save(OUT/f'profile_audit_{args.year}.json',report)
    print(json.dumps({k:v for k,v in report.items() if k!='sources'},indent=2))


if __name__=='__main__':main()
