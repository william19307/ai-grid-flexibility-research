"""Synthetic fixtures test information leakage; none are market observations."""
from pathlib import Path
from datetime import datetime,timedelta
import sys,json,copy,hashlib
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'work/research/models'))
from forecast_vintages import select_curve,digest
OUT=ROOT/'outputs/research/revision/market_information';OUT.mkdir(parents=True,exist_ok=True)
checks=[]
request=dict(decision_at='2026-09-20T12:00:00+08:00',delivery_start='2026-09-21T00:00:00+08:00',periods=96,interval_minutes=15,series_id='SYNTHETIC_ONLY|load',unit='MW')
start=datetime.fromisoformat(request['delivery_start'])
base=dict(snapshot_id='initial',series_id=request['series_id'],kind='forecast',unit='MW',interval_minutes=15,
    available_at='2026-09-20T08:00:00+08:00',interval_starts=[(start+timedelta(minutes=15*i)).isoformat() for i in range(96)],values=list(range(96)),source_sha256='a'*64)
def admitted(r,**overrides):
    return dict(snapshot_sha256=digest(r),source_sha256=r['source_sha256'],availability_evidence_sha256='b'*64,verified_available_at=r['available_at'],evidence_kind='archived_version_record',**overrides)
def run(records,admissions=None,**changes):
    return select_curve(records,{r['snapshot_id']:admitted(r) for r in records} if admissions is None else admissions,**dict(request,**changes))
new=copy.deepcopy(base);new.update(snapshot_id='revision',available_at='2026-09-20T10:00:00+08:00',values=[v+3 for v in base['values']])
late=copy.deepcopy(new);late.update(snapshot_id='late_revision',available_at='2026-09-20T12:00:01+08:00',values=[v+999 for v in base['values']])
records=[base,new,late];before=digest(records)
r=run(records);assert r['selected']['snapshot_id']=='revision' and digest(records)==before
checks.append('whole_latest_eligible_version_without_future_revision_or_mutation')
exact=copy.deepcopy(new);exact.update(snapshot_id='exact',available_at=request['decision_at'])
assert run([base,exact])['selected']['snapshot_id']=='exact';checks.append('cutoff_equality_explicitly_allowed')
assert run([late])['status']=='unavailable';checks.append('all_late_returns_unavailable')
assert run([base],{})['status']=='unavailable';checks.append('no_approved_source_returns_unavailable')
policy=admitted(base);policy['evidence_kind']='rule_deadline'
assert run([base],{'initial':policy})['status']=='unavailable';checks.append('publication_rule_is_not_release_evidence')
tampered=copy.deepcopy(base);tampered['values'][0]=99
assert run([tampered],{'initial':admitted(base)})['status']=='unavailable';checks.append('post_admission_value_change_rejected')
partial=copy.deepcopy(new);partial['interval_starts']=partial['interval_starts'][:-1];partial['values']=partial['values'][:-1]
assert run([base,partial])['selected']['snapshot_id']=='initial';checks.append('partial_revision_not_spliced_into_older_complete_curve')
for label,field,value in [('units','unit','kW'),('actuals','kind','actual'),('end_stamps','interval_starts',[(start+timedelta(minutes=15*(i+1))).isoformat() for i in range(96)]),('naive_time','available_at','2026-09-20T08:00:00')]:
    bad=copy.deepcopy(base);bad[field]=value
    assert run([bad])['status']=='unavailable';checks.append('reject_'+label)
utc=copy.deepcopy(base);utc['available_at']='2026-09-20T00:00:00Z'
assert run([utc])['status']=='selected';checks.append('utc_and_local_offset_comparison')
duplicate=copy.deepcopy(base);duplicate['snapshot_id']='concurrent';duplicate['values'][0]=100
assert run([base,duplicate])['status']=='ambiguous_latest_release';checks.append('same_release_time_ambiguity_retained')
approval=admitted(base);approval['availability_evidence_sha256']=''
assert run([base],{'initial':approval})['status']=='unavailable';checks.append('missing_version_evidence_rejected')
approval=admitted(base);approval['verified_available_at']='2026-09-20T09:00:00+08:00'
assert run([base],{'initial':approval})['status']=='unavailable';checks.append('source_review_timestamp_binding')
try:run([base,base])
except ValueError:checks.append('duplicate_snapshot_ids_rejected')
else:raise AssertionError('Duplicate id accepted')
try:run([base],decision_at='2026-09-22T12:00:00+08:00')
except ValueError:checks.append('retrospective_decision_after_delivery_rejected')
else:raise AssertionError('Late decision accepted')
files=[Path(__file__),ROOT/'work/research/models/forecast_vintages.py']
report=dict(status='PASS_SYNTHETIC_VERSION_LOGIC_ONLY',number_of_checks=len(checks),checks=checks,
    empirical_forecast_snapshots_admitted=0,
    source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files},
    scope='Synthetic fixtures; does not verify actual publication timestamps, source authenticity, extraction correctness or forecast skill')
(OUT/'vintage_logic_validation.json').write_text(json.dumps(report,indent=2)+'\n')
(OUT/'synthetic_vintage_selection.json').write_text(json.dumps({'fixture_label':'SYNTHETIC_ONLY_NOT_MARKET_DATA','result':r},indent=2)+'\n')
print(json.dumps(report,indent=2))
