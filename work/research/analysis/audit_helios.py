"""Audit SenseTime Helios traces (SC'21) and extract observed queueing delay / duration statistics.

Evidence tier: production job metadata (public, CC-style release; see LICENSE.txt in source dir).
Queueing delay observed in production is used only as a LOWER BOUND on tolerated
delay; it is not a service deadline. No power data exist in this trace.
"""
from pathlib import Path
import json,hashlib,zipfile
import numpy as np,pandas as pd
ROOT=Path(__file__).resolve().parents[3]
SRC=ROOT/'work/research/sources/helios_sensetime';OUT=ROOT/'outputs/research/tables'
audit={'source':'https://github.com/S-Lab-System-Group/HeliosData','paper':'Hu et al., SC 2021, doi:10.1145/3458817.3476223','zip_sha256':hashlib.sha256(open(SRC/'data.zip','rb').read()).hexdigest(),'zip_bytes':(SRC/'data.zip').stat().st_size,'clusters':{}}
frames=[]
for c in ['Venus','Saturn','Earth','Uranus']:
    f=SRC/f'data/{c}/cluster_log.csv';df=pd.read_csv(f)
    for col in ['submit_time','start_time','end_time']:df[col]=pd.to_datetime(df[col])
    df['cluster']=c
    d={'rows':int(len(df)),'file_sha256':hashlib.sha256(open(f,'rb').read()).hexdigest(),'columns':df.columns.tolist(),
       'submit_min':str(df.submit_time.min()),'submit_max':str(df.submit_time.max()),'states':df.state.value_counts().to_dict(),
       'gpu_jobs':int((df.gpu_num>0).sum()),'queue_col_equals_start_minus_submit_max_abs_s':float(((df.start_time-df.submit_time).dt.total_seconds()-df.queue).abs().max()),
       'duration_col_equals_end_minus_start_max_abs_s':float(((df.end_time-df.start_time).dt.total_seconds()-df.duration).abs().max()),
       'null_counts':df.isna().sum().to_dict()}
    audit['clusters'][c]=d;frames.append(df)
df=pd.concat(frames,ignore_index=True)
g=df[(df.gpu_num>0)].copy()
g['gpu_hours']=g.gpu_num*g.duration/3600
g['queue_h']=g.queue/3600;g['dur_h']=g.duration/3600
def q(s):return {f'p{p}':float(np.percentile(s,p)) for p in [10,25,50,75,90,95,99]}
stats={'gpu_jobs_all_states':int(len(g)),'gpu_jobs_completed':int((g.state=='COMPLETED').sum()),
 'queue_hours_all_gpu_jobs':q(g.queue_h),'queue_hours_completed':q(g[g.state=='COMPLETED'].queue_h),
 'duration_hours_completed':q(g[g.state=='COMPLETED'].dur_h),
 'gpu_hours_share_by_state':(g.groupby('state').gpu_hours.sum()/g.gpu_hours.sum()).round(4).to_dict(),
 'gpu_hour_weighted_queue_share_gt_1h':float(g[g.queue_h>1].gpu_hours.sum()/g.gpu_hours.sum()),
 'gpu_hour_weighted_queue_share_gt_6h':float(g[g.queue_h>6].gpu_hours.sum()/g.gpu_hours.sum()),
 'gpu_hour_weighted_queue_share_gt_24h':float(g[g.queue_h>24].gpu_hours.sum()/g.gpu_hours.sum()),
 'gpu_hour_weighted_duration_share_gt_1h':float(g[g.dur_h>1].gpu_hours.sum()/g.gpu_hours.sum()),
 'gpu_hour_weighted_duration_share_gt_24h':float(g[g.dur_h>24].gpu_hours.sum()/g.gpu_hours.sum()),
 'note':'queue = observed scheduling wait in production; a lower bound on delay users tolerated, NOT a deadline'}
# by gpu_num class
cls=pd.cut(g.gpu_num,[0,1,4,8,32,10000],labels=['1','2-4','5-8','9-32','>32'])
by=g.groupby(cls,observed=True).agg(jobs=('job_id','size'),gpu_hours=('gpu_hours','sum'),queue_h_median=('queue_h','median'),queue_h_p90=('queue_h',lambda s:s.quantile(.9)),dur_h_median=('dur_h','median'),dur_h_p90=('dur_h',lambda s:s.quantile(.9)))
by['gpu_hours_share']=by.gpu_hours/by.gpu_hours.sum();by.round(3).to_csv(OUT/'helios_gpu_jobs_by_size_class.csv')
# diurnal & weekly submission profile (GPU-hour weighted and count)
g['hour']=g.submit_time.dt.hour;g['dow']=g.submit_time.dt.dayofweek
prof=g.groupby('hour').agg(jobs=('job_id','size'),gpu_hours=('gpu_hours','sum'));prof['jobs_share']=prof.jobs/prof.jobs.sum();prof['gpu_hours_share']=prof.gpu_hours/prof.gpu_hours.sum()
prof.round(5).to_csv(OUT/'helios_submission_profile_by_hour.csv')
dow=g.groupby('dow').agg(jobs=('job_id','size'),gpu_hours=('gpu_hours','sum'));dow['gpu_hours_share']=dow.gpu_hours/dow.gpu_hours.sum();dow.round(5).to_csv(OUT/'helios_submission_profile_by_weekday.csv')
# hourly running GPU load reconstruction per cluster (GPUs in use at hour boundaries) -> occupancy time series
series=[]
for c,gc in g[g.state.isin(['COMPLETED','FAILED','CANCELLED','TIMEOUT','NODE_FAIL'])].groupby('cluster'):
    t0=gc.start_time.min().floor('h');t1=gc.end_time.max().ceil('h');idx=pd.date_range(t0,t1,freq='h')
    occ=np.zeros(len(idx))
    s=((gc.start_time-t0).dt.total_seconds()//3600).astype(int).values;e=np.ceil((gc.end_time-t0).dt.total_seconds()/3600).astype(int).values;n=gc.gpu_num.values
    delta=np.zeros(len(idx)+1);np.add.at(delta,s,n);np.add.at(delta,np.minimum(e,len(idx)),-n);occ=np.cumsum(delta)[:len(idx)]
    series.append(pd.DataFrame({'time':idx,'cluster':c,'gpus_in_use':occ}))
occ=pd.concat(series);occ.to_csv(OUT/'helios_hourly_gpus_in_use_reconstructed.csv',index=False)
cap={c:pd.read_csv(SRC/f'data/{c}/cluster_gpu_number.csv') for c in ['Venus','Saturn','Earth','Uranus']}
stats['cluster_total_gpus_first_day']={c:int(v['total'].iloc[0]) for c,v in cap.items()}
stats['reconstructed_mean_gpus_in_use']={c:float(v.gpus_in_use.mean()) for c,v in occ.groupby('cluster')}
audit['gpu_job_statistics']=stats
json.dump(audit,open(OUT/'helios_trace_audit.json','w'),indent=1,default=str)
print(json.dumps(stats,indent=1,default=str));print(by.round(3).to_string())
