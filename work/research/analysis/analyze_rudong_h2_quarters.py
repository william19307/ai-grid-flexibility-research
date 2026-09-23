"""Quarterly aggregation of previously frozen hourly profiles; no refitting."""
from pathlib import Path
import hashlib,json
import pandas as pd
ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'outputs/research/revision/rudong_h2_quarterly'
BASE=ROOT/'outputs/research/revision/rudong_h2_validation'
PLAN_SHA='ce972c86eb621db2a3fd7afcef71dc003ba154e7ddf8b3720586a75aaa02467f'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 assert sha(OUT/'analysis_plan.json')==PLAN_SHA
 plan=json.loads((OUT/'analysis_plan.json').read_text())
 assert sha(BASE/'transfer_audit.json')==plan['input_transfer_audit_sha256']
 prior=json.loads((BASE/'transfer_audit.json').read_text())
 assert sha(ROOT/prior['profile_path'])==plan['input_profile_sha256']==prior['profile_sha256']
 assert sha(BASE/'transfer_comparison.csv')==prior['summary_sha256']
 obs_audit=json.loads((OUT/'observation_audit.json').read_text())
 assert sha(OUT/'quarterly_observations.csv')==obs_audit['quarterly_sha256']
 obs=pd.read_csv(OUT/'quarterly_observations.csv').set_index(['year','quarter'])
 profile=pd.read_csv(ROOT/prior['profile_path'],index_col=0,parse_dates=True)
 annual=pd.read_csv(BASE/'transfer_comparison.csv').set_index(['year','curve'])
 curves=sorted({c.split('|')[0] for c in profile})
 rows=[]
 for (year,q),frame in profile.groupby([profile.index.year,profile.index.quarter]):
  observed=float(obs.loc[(year,q),'gross_mwh']);halfwidth=float(obs.loc[(year,q),'rounding_halfwidth_mwh'])
  for curve in curves:
   raw=float(frame[curve+'|unscaled_pu'].sum()*350)
   scaled=float(frame[curve+'|scaled_pu'].sum()*350)
   rows.append(dict(year=year,quarter=q,curve=curve,hours=len(frame),observed_gross_mwh=observed,observed_export_mwh=float(obs.loc[(year,q),'export_mwh']),rounding_halfwidth_mwh=halfwidth,unscaled_mwh=raw,scaled_mwh=scaled,unscaled_error_pct=100*(raw/observed-1),scaled_error_mwh=scaled-observed,scaled_error_pct=100*(scaled/observed-1),scaled_error_lower_rounding_pct=100*(scaled/(observed+halfwidth)-1),scaled_error_upper_rounding_pct=100*(scaled/(observed-halfwidth)-1),scaled_hours_above_one=int((frame[curve+'|scaled_pu']>1+1e-12).sum()),frozen_2022_scale=float(annual.loc[(year,curve),'frozen_2022_scale'])))
 result=pd.DataFrame(rows);result.to_csv(OUT/'quarterly_comparison.csv',index=False)
 years=[]
 for (year,curve),group in result.groupby(['year','curve']):
  signed=group.scaled_error_mwh.sum();absolute=group.scaled_error_mwh.abs().sum();generation=group.observed_gross_mwh.sum()
  assert abs(group.scaled_mwh.sum()-annual.loc[(year,curve),'scaled_mwh'])<1e-7
  assert abs(generation-annual.loc[(year,curve),'observed_gross_mwh'])<1e-7
  years.append(dict(year=year,curve=curve,quarterly_absolute_error_sum_mwh=absolute,annual_signed_error_mwh=signed,quarterly_absolute_error_over_annual_generation_pct=100*absolute/generation,annual_signed_error_pct=100*signed/generation,cancellation_fraction=1-abs(signed)/absolute if absolute>1e-10 else 0,maximum_absolute_quarter_error_pct=group.scaled_error_pct.abs().max()))
 yr=pd.DataFrame(years);yr.to_csv(OUT/'annual_cancellation.csv',index=False)
 audit=dict(plan_sha256=PLAN_SHA,script_sha256=sha(Path(__file__)),observation_audit_sha256=sha(OUT/'observation_audit.json'),prior_transfer_audit_sha256=sha(BASE/'transfer_audit.json'),quarterly_comparison_sha256=sha(OUT/'quarterly_comparison.csv'),annual_cancellation_sha256=sha(OUT/'annual_cancellation.csv'),conditions=len(rows),refitted_parameters=0,scope='Exploratory aggregate seasonal diagnostic; all shapes retained including physically rejected generic; not hourly or provincial validation; rounding ranges hold scale fixed and are not confidence intervals.')
 (OUT/'comparison_audit.json').write_text(json.dumps(audit,indent=2)+'\n')
 print(result[['year','quarter','curve','observed_gross_mwh','scaled_error_pct']].to_string(index=False))
 print(yr.to_string(index=False))
if __name__=='__main__':main()
