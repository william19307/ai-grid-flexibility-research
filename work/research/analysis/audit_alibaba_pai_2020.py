"""Audit Alibaba PAI GPU trace (NSDI'22 'MLaaS in the Wild') and extract observed wait/duration/utilisation.

Evidence tier: production job/task/instance metadata and per-instance average sensors.
job.start_time = submission; earliest task.start_time = launch -> wait = scheduling latency (README).
Timestamps are desensitised but preserve time-of-day and weekday (README). No power data.
"""
from pathlib import Path
import json,hashlib
import numpy as np,pandas as pd
ROOT=Path(__file__).resolve().parents[3]
SRC=ROOT/'work/research/sources/alibaba_pai_gpu_2020';OUT=ROOT/'outputs/research/tables'
def sha(f):
    h=hashlib.sha256()
    with open(f,'rb') as fh:
        for b in iter(lambda:fh.read(1<<24),b''):h.update(b)
    return h.hexdigest()
audit={'source':'https://github.com/alibaba/clusterdata/tree/master/cluster-trace-gpu-v2020','paper':'Weng et al., NSDI 2022','license':'CC-BY-4.0 per repository LICENSE','files':{}}
for t in ['pai_job_table','pai_task_table','pai_group_tag_table','pai_machine_spec','pai_instance_table','pai_sensor_table']:
    audit['files'][t]={'tar_sha256':sha(SRC/f'{t}.tar.gz'),'tar_bytes':(SRC/f'{t}.tar.gz').stat().st_size,'csv_bytes':(SRC/f'{t}.csv').stat().st_size,'header':open(SRC/f'{t}.header').read().strip()}
hdr=lambda t:open(SRC/f'{t}.header').read().strip().split(',')
job=pd.read_csv(SRC/'pai_job_table.csv',names=hdr('pai_job_table'));task=pd.read_csv(SRC/'pai_task_table.csv',names=hdr('pai_task_table'))
tag=pd.read_csv(SRC/'pai_group_tag_table.csv',names=hdr('pai_group_tag_table'))
audit['job_rows']=int(len(job));audit['task_rows']=int(len(task));audit['job_status']=job.status.value_counts().to_dict()
audit['job_name_unique']=bool(job.job_name.is_unique);audit['inst_id_unique']=bool(job.inst_id.is_unique)
gt=task[task.plan_gpu.fillna(0)>0]
audit['tasks_with_gpu']=int(len(gt));audit['gpu_type_counts']=gt.gpu_type.value_counts().to_dict()
# wait: earliest task launch minus job submission, per job (Terminated jobs and GPU tasks only)
first=gt.groupby('job_name').agg(task_start=('start_time','min'),task_end=('end_time','max'),plan_gpu_sum=('plan_gpu',lambda s:(s*gt.loc[s.index,'inst_num'].fillna(1)).sum()/100),ntask=('task_name','size'))
j=job.merge(first,left_on='job_name',right_index=True,how='inner')
j=j[j.status=='Terminated'].dropna(subset=['start_time','end_time','task_start'])
j['wait_h']=(j.task_start-j.start_time)/3600;j['run_h']=(j.task_end-j.task_start)/3600;j['dur_h']=(j.end_time-j.start_time)/3600
j=j[(j.wait_h>=0)&(j.run_h>=0)]
j['gpu_hours']=j.plan_gpu_sum*j.run_h
def q(s):return {f'p{p}':float(np.percentile(s,p)) for p in [10,25,50,75,90,95,99]}
stats={'terminated_gpu_jobs':int(len(j)),'negative_or_missing_dropped':int(audit['job_rows']-len(j)),
 'wait_hours':q(j.wait_h),'run_hours':q(j.run_h),'requested_gpus':q(j.plan_gpu_sum),
 'gpu_hour_weighted_wait_share_gt_1h':float(j[j.wait_h>1].gpu_hours.sum()/j.gpu_hours.sum()),
 'gpu_hour_weighted_wait_share_gt_6h':float(j[j.wait_h>6].gpu_hours.sum()/j.gpu_hours.sum()),
 'gpu_hour_weighted_wait_share_gt_24h':float(j[j.wait_h>24].gpu_hours.sum()/j.gpu_hours.sum()),
 'gpu_hour_weighted_run_share_gt_1h':float(j[j.run_h>1].gpu_hours.sum()/j.gpu_hours.sum()),
 'gpu_hour_weighted_run_share_gt_24h':float(j[j.run_h>24].gpu_hours.sum()/j.gpu_hours.sum()),
 'note':'wait = scheduling latency observed in production (README); lower bound on tolerated delay, not a deadline. plan_gpu is requested, not used.'}
# workload tags (~9% instances)
jt=j.merge(tag[['inst_id','workload']],on='inst_id',how='left')
wl=jt.groupby(jt.workload.fillna('untagged')).agg(jobs=('job_name','size'),gpu_hours=('gpu_hours','sum'),wait_h_median=('wait_h','median'),run_h_median=('run_h','median'),run_h_p90=('run_h',lambda s:s.quantile(.9)))
wl['gpu_hours_share']=wl.gpu_hours/wl.gpu_hours.sum();wl.sort_values('gpu_hours',ascending=False).round(3).to_csv(OUT/'alibaba_pai_2020_by_workload_tag.csv')
# time-of-day / weekday submission profile (README: time-of-day and weekday preserved under UTC+8)
ts=pd.to_datetime(j.start_time,unit='s',utc=True).dt.tz_convert('Asia/Shanghai')
j['hour']=ts.dt.hour;j['dow']=ts.dt.dayofweek
prof=j.groupby('hour').agg(jobs=('job_name','size'),gpu_hours=('gpu_hours','sum'));prof['jobs_share']=prof.jobs/prof.jobs.sum();prof['gpu_hours_share']=prof.gpu_hours/prof.gpu_hours.sum();prof.round(5).to_csv(OUT/'alibaba_pai_2020_submission_profile_by_hour.csv')
# sensor: per-instance average GPU utilisation of requested share
sen=pd.read_csv(SRC/'pai_sensor_table.csv',names=hdr('pai_sensor_table'),usecols=['job_name','worker_name','gpu_wrk_util'])
sen=sen.dropna(subset=['gpu_wrk_util']);audit['sensor_rows_with_gpu_util']=int(len(sen))
stats['instance_avg_gpu_util_percent_of_one_gpu']=q(sen.gpu_wrk_util)
stats['instance_share_gpu_util_below_10pct']=float((sen.gpu_wrk_util<10).mean())
audit['statistics']=stats
json.dump(audit,open(OUT/'alibaba_pai_2020_trace_audit.json','w'),indent=1,default=str)
j[['job_name','wait_h','run_h','dur_h','plan_gpu_sum','gpu_hours','hour','dow']].to_csv(ROOT/'work/research/prepared/alibaba_pai_2020_terminated_gpu_jobs_wait_run.csv.gz',index=False,compression='gzip')
print(json.dumps(stats,indent=1));print(wl.sort_values('gpu_hours',ascending=False).head(12).round(3).to_string())
