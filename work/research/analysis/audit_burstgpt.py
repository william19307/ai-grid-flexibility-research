"""Audit release v2.0 part 1. Token counts are not hardware work units."""
from pathlib import Path
import json,hashlib
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[3]
SRC=ROOT/'work/research/sources/BurstGPT';OUT=ROOT/'outputs/research/tables'
p=SRC/'BurstGPT_1.csv';meta=json.loads((SRC/'download_verified.json').read_text())
assert hashlib.sha256(p.read_bytes()).hexdigest()==meta['sha256']
d=pd.read_csv(p)
assert list(d.columns)==['Timestamp','Model','Request tokens','Response tokens','Total tokens','Log Type']
assert not d.isna().any().any()
assert (d[['Timestamp','Request tokens','Response tokens','Total tokens']]>=0).all().all()
token_errors=int((d['Request tokens']+d['Response tokens']!=d['Total tokens']).sum())
assert token_errors==0
d['hour_index']=(d.Timestamp//3600).astype(int)
d['zero_output']=(d['Response tokens']==0).astype(int)
hour_max=int(d.hour_index.max())
groups=[]
for (model,kind),g in d.groupby(['Model','Log Type']):
    h=g.groupby('hour_index').agg(recorded_requests=('Timestamp','size'),
       input_tokens=('Request tokens','sum'),output_tokens=('Response tokens','sum'),
       zero_output_requests=('zero_output','sum')).reindex(range(hour_max+1),fill_value=0).reset_index()
    h['Model']=model;h['Log Type']=kind;h['is_last_partial_hour']=h.hour_index==hour_max
    groups.append(h)
hourly=pd.concat(groups,ignore_index=True)
hourly.to_csv(OUT/'burstgpt_v2_part1_hourly_recorded_requests.csv',index=False)
modelstats=[]
for model,g in d.groupby('Model'):
    hh=g.groupby('hour_index').size().reindex(range(hour_max),fill_value=0)
    modelstats.append({'model':model,'records':len(g),'zero_output_records':int(g.zero_output.sum()),
          'median_input_tokens':float(g['Request tokens'].median()),
          'median_output_tokens_all_records':float(g['Response tokens'].median()),
          'mean_recorded_requests_per_full_hour':float(hh.mean()),
          'max_recorded_requests_per_full_hour':int(hh.max()),
          'recorded_hourly_peak_to_mean':float(hh.max()/hh.mean()),
          'p95_recorded_requests_per_full_hour':float(hh.quantile(.95)),
          'zero_record_hours':int((hh==0).sum())})
pd.DataFrame(modelstats).to_csv(OUT/'burstgpt_v2_part1_model_summary.csv',index=False)
summary={'status':'real_request_trace_audited_NOT_gpu_power_or_deadline_data',
    'release':'v2.0','part':'1','rows':len(d),'columns':list(d.columns[:6]),
    'timestamp_min_seconds':int(d.Timestamp.min()),'timestamp_max_seconds':int(d.Timestamp.max()),
    'timestamps_monotonic':bool(d.Timestamp.is_monotonic_increasing),
    'full_hour_bins_used_for_rate_summary':hour_max,'last_partial_hour_excluded_from_rate_summary':True,
    'full_row_repetitions_retained':int(d.iloc[:,:6].duplicated().sum()),
    'reason_repetitions_retained':'coarse timestamps and no request ID; matching metadata can be separate requests',
    'zero_output_records_retained':int(d.zero_output.sum()),
    'zero_output_interpretation':'source release labels zero-response-token records failures; not dropped from arrival counts',
    'token_sum_errors':token_errors,'missing_elapsed_time':True,'missing_session_id':True,
    'documentation_version_caveat':'current README announces added columns; pinned release asset has only six columns',
    'unknowns':['calendar_start_date','absolute_timezone_identity','collection_completeness',
                'allowed_service_deadlines','hardware_allocation','per_request_GPU_energy','prefill_decode_work_conversion'],
    'not_allowed':['treat ChatGPT and GPT-4 tokens as same compute work',
                   'treat observed duration as permissible deferral deadline',
                   'interpret hourly arrival counts as Chinese AI power'],
    'download':meta}
(OUT/'burstgpt_v2_part1_audit.json').write_text(json.dumps(summary,indent=2))
registry=OUT/'data_registry.csv';tab=pd.read_csv(registry)
tab=tab[tab.id!='D07']
tab=pd.concat([tab,pd.DataFrame([dict(id='D07',dataset='BurstGPT release v2.0 part 1',
    url='https://github.com/HPMLL/BurstGPT/releases/tag/v2.0',evidence_type='production_request_metadata',
    coverage=f'{len(d)} request records; relative timestamps; two model labels',licence='CC-BY-4.0',
    status='download_digest_verified_schema_and_hourly_audit_complete',
    limits='no deadlines, elapsed time, request IDs or power; retain repeated metadata and zero-output records',
    version=meta['sha256'])])],ignore_index=True)
tab.to_csv(registry,index=False)
print(json.dumps(summary,indent=2))
