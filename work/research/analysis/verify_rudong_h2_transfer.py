"""Independent scalar/Decimal reconstruction, temporal and capacity audit."""
from pathlib import Path
from datetime import datetime, timedelta, timezone
from decimal import Decimal as D
import csv
import gzip
import hashlib
import json
from verify_wind_reference_shapes import curve_rows, scalar

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT/'outputs/research/revision/rudong_h2_validation'
SRC = ROOT/'work/research/sources/wind_conversion_revision_20260923'
RAW = ROOT/'work/research/sources/rudong_h2_observations_20260923/weather'

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    audit=json.loads((OUT/'transfer_audit.json').read_text())
    assert sha(OUT/'site_weather_plan.json')==audit['plan_sha256']=='eba200c098e820096c9701afd0412e0a1a2496cde0ca74f14fdedc6ee77d13cd'
    assert sha(ROOT/'work/research/analysis/validate_rudong_h2_transfer.py')==audit['builder_sha256']
    assert sha(OUT/'annual_observations.csv')==audit['observations_sha256']
    plan=json.loads((OUT/'site_weather_plan.json').read_text())
    assert sha(OUT/'observation_audit.json')==plan['observation_audit_sha256']
    assert json.loads((OUT/'observation_audit.json').read_text())['output_sha256']==audit['observations_sha256']
    assert sha(ROOT/audit['profile_path'])==audit['profile_sha256']
    assert sha(OUT/'transfer_comparison.csv')==audit['summary_sha256']
    with (OUT/'annual_observations.csv').open() as f:obs={int(r['year']):D(r['gross_generation_mwh']) for r in csv.DictReader(f)}
    with (OUT/'transfer_comparison.csv').open() as f:summary={(int(r['year']),r['curve']):r for r in csv.DictReader(f)}
    with gzip.open(ROOT/audit['profile_path'],'rt') as f:profiles=list(csv.DictReader(f))
    curves={'legacy_generic':None}
    for name,digest in audit['curve_sources'].items():
        assert sha(SRC/name)==digest
        curves[name.removesuffix('.yaml')]=curve_rows(SRC/name)
    assert set(curves)=={'legacy_generic','Vestas_V112_3MW','NREL_ReferenceTurbine_5MW_offshore'}
    assert len(profiles)==8760*2+8784
    assert set(profiles[0])=={'interval_start_local'}|{k+'|'+suffix for k in curves for suffix in ['unscaled_pu','scaled_pu']}
    scales={}; offset=0;count=0;maxerr=D(0);cases=0; rounding=[]
    for source in audit['weather_sources']:
        year=source['year']; raw=RAW/(source['request_id']+'.json')
        assert sha(raw)==source['raw_sha256'] and sha(raw.with_suffix('.meta.json'))==source['meta_sha256']
        data=json.loads(raw.read_text(),parse_float=D,parse_int=D)
        begin=datetime(year,1,1);end=datetime(year+1,1,1)
        n=int((end-begin).total_seconds()/3600)
        assert data['hourly']['time']==[(begin+timedelta(hours=i)).strftime('%Y-%m-%dT%H:%M') for i in range(n+24)]
        assert data['hourly_units']['wind_speed_100m']=='m/s' and data['utc_offset_seconds']==28800
        local=begin.replace(tzinfo=timezone(timedelta(hours=8)))
        rows=profiles[offset:offset+n];offset+=n
        assert all(datetime.fromisoformat(r['interval_start_local'])==local+timedelta(hours=i) for i,r in enumerate(rows))
        for name,curve in curves.items():
            endpoints=[scalar(v,curve) for v in data['hourly']['wind_speed_100m'][:n+1]]
            hourly=[(a+b)/2 for a,b in zip(endpoints,endpoints[1:])]
            energy=sum(hourly)*350
            if year==2022:scales[name]=obs[year]/energy
            scaled=[v*scales[name] for v in hourly]
            for suffix,values in [('unscaled_pu',hourly),('scaled_pu',scaled)]:
                for row,v in zip(rows,values):
                    err=abs(D(row[name+'|'+suffix])-v);maxerr=max(maxerr,err);count+=1
                    assert err<D('1e-12')
            r=summary[(year,name)]
            for field,val,tol in [('unscaled_mwh',energy,D('1e-7')),('scaled_mwh',sum(scaled)*350,D('1e-7')),('frozen_2022_scale',scales[name],D('1e-12')),('scaled_error_pct',100*(sum(scaled)*350/obs[year]-1),D('1e-10')),('excess_above_nameplate_mwh',sum(max(v-1,D(0)) for v in scaled)*350,D('1e-7'))]:
                assert abs(D(r[field])-val)<tol, (year,name,field)
            assert int(r['scaled_hours_above_one'])==sum(v>1 for v in scaled)
            assert int(r['scaled_endpoint_samples_above_one'])==sum(v*scales[name]>1 for v in endpoints)
            # Rounded annual observations bound rounding effects only, not measurement uncertainty.
            if year!=2022:
                ratio=energy/(obs[2022]/scales[name])
                lo=100*((obs[2022]-500)*ratio/(obs[year]+500)-1)
                hi=100*((obs[2022]+500)*ratio/(obs[year]-500)-1)
                rounding.append(dict(year=year,curve=name,error_rounding_lower_pct=str(lo),error_rounding_upper_pct=str(hi)))
            cases+=1
    assert count==157824 and cases==9 and offset==len(profiles)
    assert audit['physically_rejected_curves']==['legacy_generic']
    result=dict(status='PASS',hourly_values=count,cases=cases,max_absolute_error=str(maxerr),
                analysis_sha256=sha(OUT/'transfer_audit.json'),verifier_sha256=sha(Path(__file__)),
                scalar_dependency_sha256=sha(ROOT/'work/research/analysis/verify_wind_reference_shapes.py'),
                observation_rounding_bounds=rounding,
                scope='Arithmetic and frozen transfer rule verified; not independent experimental replication, hourly calibration or provincial evidence.')
    (OUT/'independent_verification.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
