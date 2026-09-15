"""Audit Microsoft Philly trace (ATC'19): job log with scheduling attempts and per-minute GPU utilisation.

Evidence tier: production job metadata (2017) and machine-level utilisation telemetry. No power.
Queueing wait = first attempt start minus submission (lower bound on tolerated delay, not a deadline).
"""
from pathlib import Path
import json,hashlib
import numpy as np,pandas as pd
ROOT=Path(__file__).resolve().parents[3]
SRC=ROOT/'work/research/sources/philly_msr';OUT=ROOT/'outputs/research/tables'
def sha(f):
    h=hashlib.sha256()
    with open(f,'rb') as fh:
        for b in iter(lambda:fh.read(1<<24),b''):h.update(b)
    return h.hexdigest()
audit={'source':'https://github.com/msr-fiddle/philly-traces','paper':'Jeon et al., USENIX ATC 2019','license':'CC-BY-4.0 (repository LICENSE)','tar_sha256':sha(SRC/'trace-data.tar.gz'),'tar_bytes':(SRC/'trace-data.tar.gz').stat().st_size,'files':{f.name:f.stat().st_size for f in (SRC/'trace-data').iterdir()}}
log=json.load(open(SRC/'trace-data/cluster_job_log'))
rows=[]
for j in log:
    att=j.get('attempts',[])
    ok=lambda v:v not in (None,'None','');st=pd.to_datetime(j.get('submitted_time')) if ok(j.get('submitted_time')) else pd.NaT;first=pd.to_datetime(att[0]['start_time']) if att and ok(att[0].get('start_time')) else pd.NaT
    last_end=max([pd.to_datetime(a['end_time']) for a in att if ok(a.get('end_time'))],default=pd.NaT)
    ng=max([sum(len(d['gpus']) for d in a['detail']) for a in att],default=0)
    rows.append(dict(jobid=j['jobid'],status=j['status'],vc=j['vc'],submitted=st,first_start=first,last_end=last_end,attempts=len(att),gpus=ng))
df=pd.DataFrame(rows);audit['jobs']=int(len(df));audit['status']=df.status.value_counts().to_dict();audit['jobid_unique']=bool(df.jobid.is_unique)
df['wait_h']=(df.first_start-df.submitted).dt.total_seconds()/3600;df['run_h']=(df.last_end-df.first_start).dt.total_seconds()/3600
g=df[(df.gpus>0)&df.wait_h.notna()&df.run_h.notna()&(df.wait_h>=0)&(df.run_h>=0)].copy();g['gpu_hours']=g.gpus*g.run_h
def q(s):return {f'p{p}':float(np.percentile(s,p)) for p in [10,25,50,75,90,95,99]}
stats={'gpu_jobs_with_times':int(len(g)),'wait_hours':q(g.wait_h),'wait_hours_pass_only':q(g[g.status=='Pass'].wait_h),'run_hours_pass_only':q(g[g.status=='Pass'].run_h),'gpus':q(g.gpus),
 'gpu_hour_weighted_wait_share_gt_1h':float(g[g.wait_h>1].gpu_hours.sum()/g.gpu_hours.sum()),'gpu_hour_weighted_wait_share_gt_6h':float(g[g.wait_h>6].gpu_hours.sum()/g.gpu_hours.sum()),'gpu_hour_weighted_wait_share_gt_24h':float(g[g.wait_h>24].gpu_hours.sum()/g.gpu_hours.sum()),
 'gpu_hour_weighted_run_share_gt_24h':float(g[g.run_h>24].gpu_hours.sum()/g.gpu_hours.sum()),'gpu_hours_share_by_status':(g.groupby('status').gpu_hours.sum()/g.gpu_hours.sum()).round(4).to_dict(),
 'jobs_with_multiple_attempts_share':float((g.attempts>1).mean()),'note':'wait = first attempt start - submission (README); lower bound on tolerated delay, not a deadline'}
# per-minute GPU utilisation: aggregate cluster-wide mean of per-GPU utilisation by time
# Stream the 3 GB utilisation file with awk: variable field counts (2-8 GPUs per machine, trailing comma,
# 19-field rows at the DST fall-back hour are two concatenated samples; only the first 8 values are used).
import subprocess
awk=r"""BEGIN{FS=","} NR>1{h=substr($1,1,13); n=(NF>10?10:NF); for(i=3;i<=n;i++){if($i!=""){v=$i+0; s[h]+=v; c[h]++; if(v<10)b++; t++; k=int(v); if(k>100)k=100; if(k<0)k=0; hist[k]++}}} END{for(h in s)print "H",h,s[h],c[h]; for(k=0;k<=100;k++)print "B",k,hist[k]+0; print "T",t,b}"""
out=subprocess.run(['awk',awk,str(SRC/'trace-data/cluster_gpu_util')],capture_output=True,text=True,check=True).stdout
hours={};hist=np.zeros(101);ntot=nbelow=0
for line in out.splitlines():
    f=line.split()
    if f[0]=='H':hours[f[1]+' '+f[2]]=(float(f[3]),int(f[4]))
    elif f[0]=='B':hist[int(f[1])]=float(f[2])
    elif f[0]=='T':ntot=int(f[1]);nbelow=int(f[2])
h=pd.Series({pd.to_datetime(k):v[0]/v[1] for k,v in hours.items() if v[1]}).sort_index()
cdf=np.cumsum(hist)/hist.sum()
stats['machine_gpu_util_percent']={f'p{p}':int(np.searchsorted(cdf,p/100)) for p in [10,25,50,75,90,95,99]}
stats['cluster_hourly_mean_util_percent']=q(h.dropna())
stats['share_of_gpu_minutes_below_10pct_util']=nbelow/ntot;stats['gpu_minute_samples']=ntot
h.rename('mean_gpu_util_percent').to_csv(OUT/'philly_cluster_hourly_mean_gpu_util.csv')
g[['jobid','status','wait_h','run_h','gpus','gpu_hours','attempts']].to_csv(OUT/'philly_gpu_jobs_wait_run.csv.gz',index=False,compression='gzip')
audit['statistics']=stats;json.dump(audit,open(OUT/'philly_trace_audit.json','w'),indent=1,default=str)
print(json.dumps(stats,indent=1,default=str))
