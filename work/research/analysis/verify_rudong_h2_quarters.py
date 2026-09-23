"""Rebuild all quarter sums directly from raw weather with Decimal scalar curves."""
from pathlib import Path
from datetime import datetime,timedelta
from decimal import Decimal as D
import csv,hashlib,json
from verify_wind_reference_shapes import scalar,curve_rows
ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'outputs/research/revision/rudong_h2_quarterly'
BASE=ROOT/'outputs/research/revision/rudong_h2_validation'
RAW=ROOT/'work/research/sources/rudong_h2_observations_20260923/weather'
CURVE=ROOT/'work/research/sources/wind_conversion_revision_20260923'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def csvrows(p):
 with p.open() as f:return list(csv.DictReader(f))
def main():
 plan=json.loads((OUT/'analysis_plan.json').read_text());audit=json.loads((OUT/'comparison_audit.json').read_text())
 assert sha(OUT/'analysis_plan.json')==audit['plan_sha256']=='ce972c86eb621db2a3fd7afcef71dc003ba154e7ddf8b3720586a75aaa02467f'
 assert sha(BASE/'transfer_audit.json')==plan['input_transfer_audit_sha256']==audit['prior_transfer_audit_sha256']
 assert sha(ROOT/'work/research/analysis/analyze_rudong_h2_quarters.py')==audit['script_sha256']
 for name,key in [('quarterly_comparison.csv','quarterly_comparison_sha256'),('annual_cancellation.csv','annual_cancellation_sha256'),('observation_audit.json','observation_audit_sha256')]:assert sha(OUT/name)==audit[key]
 oa=json.loads((OUT/'observation_audit.json').read_text())
 assert sha(OUT/'source_manifest.json')==oa['source_manifest_sha256']
 assert sha(BASE/'annual_observations.csv')==oa['annual_observations_sha256']
 assert sha(OUT/'quarterly_observations.csv')==oa['quarterly_sha256']
 assert sha(OUT/'cumulative_disclosures.csv')==oa['cumulative_sha256']
 # Separately reconstruct the differences from cumulative disclosures and annual totals.
 cumul={}
 for r in csvrows(OUT/'cumulative_disclosures.csv'):
  key=(int(r['year']),int(r['cumulative_quarter']))
  value=(D(r['gross_mwh']),D(r['export_mwh']))
  if key in cumul:assert cumul[key]==value
  cumul[key]=value
 annual={int(r['year']):D(r['gross_generation_mwh']) for r in csvrows(BASE/'annual_observations.csv')}
 for r in csvrows(BASE/'annual_observations.csv'):cumul[(int(r['year']),4)]=(D(r['gross_generation_mwh']),D(r['grid_export_mwh']))
 obs={}
 for r in csvrows(OUT/'quarterly_observations.csv'):
  year,q=int(r['year']),int(r['quarter']);prev=cumul[(year,q-1)] if q>1 else (D(0),D(0))
  expected=tuple(a-b for a,b in zip(cumul[(year,q)],prev))
  assert expected==(D(r['gross_mwh']),D(r['export_mwh']))
  assert int(r['rounding_halfwidth_mwh'])==(500 if q==1 else 1000)
  obs[(year,q)]=expected[0]
 compare={(int(r['year']),int(r['quarter']),r['curve']):r for r in csvrows(OUT/'quarterly_comparison.csv')}
 cancellations={(int(r['year']),r['curve']):r for r in csvrows(OUT/'annual_cancellation.csv')}
 prior=json.loads((BASE/'transfer_audit.json').read_text());curves={'legacy_generic':None}
 assert sha(BASE/'annual_observations.csv')==prior['observations_sha256']
 for name,digest in prior['curve_sources'].items():
  assert sha(CURVE/name)==digest;curves[name.removesuffix('.yaml')]=curve_rows(CURVE/name)
 scales={};maxerr=D(0);quarter_checks=0;year_checks=0
 for source in prior['weather_sources']:
  year=source['year'];raw=RAW/(source['request_id']+'.json');assert sha(raw)==source['raw_sha256']
  data=json.loads(raw.read_text(),parse_float=D,parse_int=D)
  start=datetime(year,1,1);n=int((datetime(year+1,1,1)-start).total_seconds()/3600)
  assert data['hourly']['time']==[(start+timedelta(hours=i)).strftime('%Y-%m-%dT%H:%M') for i in range(n+24)]
  for name,curve in curves.items():
   endpoint=[scalar(v,curve) for v in data['hourly']['wind_speed_100m'][:n+1]]
   hourly=[(a+b)/2 for a,b in zip(endpoint,endpoint[1:])]
   if year==2022:scales[name]=annual[2022]/(sum(hourly)*350)
   sums={q:D(0) for q in range(1,5)};hours={q:0 for q in range(1,5)};violations={q:0 for q in range(1,5)}
   for i,value in enumerate(hourly):
    q=((start+timedelta(hours=i)).month-1)//3+1
    sums[q]+=value*350;hours[q]+=1;violations[q]+=int(value*scales[name]>1)
   errors=[]
   for q,total in sums.items():
    r=compare[(year,q,name)];scaled=total*scales[name];delta=scaled-obs[(year,q)];errors.append(delta)
    err=abs(D(r['scaled_mwh'])-scaled);maxerr=max(maxerr,err)
    assert err<D('1e-7')
    assert abs(D(r['unscaled_mwh'])-total)<D('1e-7')
    assert abs(D(r['scaled_error_pct'])-100*delta/obs[(year,q)])<D('1e-10')
    assert abs(D(r['frozen_2022_scale'])-scales[name])<D('1e-12')
    assert int(r['hours'])==hours[q] and int(r['scaled_hours_above_one'])==violations[q]
    h=D(500 if q==1 else 1000)
    assert abs(D(r['scaled_error_lower_rounding_pct'])-100*(scaled/(obs[(year,q)]+h)-1))<D('1e-10')
    assert abs(D(r['scaled_error_upper_rounding_pct'])-100*(scaled/(obs[(year,q)]-h)-1))<D('1e-10')
    quarter_checks+=1
   absolute=sum(map(abs,errors));signed=sum(errors);r=cancellations[(year,name)]
   assert abs(D(r['quarterly_absolute_error_sum_mwh'])-absolute)<D('1e-7')
   assert abs(D(r['annual_signed_error_mwh'])-signed)<D('1e-7')
   assert abs(D(r['quarterly_absolute_error_over_annual_generation_pct'])-100*absolute/annual[year])<D('1e-10')
   assert abs(D(r['cancellation_fraction'])-(1-abs(signed)/absolute))<D('1e-10')
   year_checks+=1
 assert quarter_checks==36 and year_checks==9
 result=dict(status='PASS',independent_quarterly_cases=quarter_checks,independent_annual_cancellation_cases=year_checks,derived_observation_quarters_checked=len(obs),max_quarterly_energy_difference_mwh=str(maxerr),analysis_sha256=sha(OUT/'comparison_audit.json'),verifier_sha256=sha(Path(__file__)),scalar_dependency_sha256=sha(ROOT/'work/research/analysis/verify_wind_reference_shapes.py'),scope='Raw-weather arithmetic and quarterly aggregation; PDF records checked separately. Does not establish actual turbine curves or hourly accuracy.')
 (OUT/'independent_verification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
