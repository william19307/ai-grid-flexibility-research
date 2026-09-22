"""Descriptive conditional ranges; paired scenarios are not statistical replicates."""
from pathlib import Path
import json,hashlib
import numpy as np,pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'outputs/research/revision/multiperiod'
src=OUT/'certified_results.csv';d=pd.read_csv(src);spec=json.loads((OUT/'manifest.json').read_text());audit=json.loads((OUT/'independent_verification.json').read_text())
assert audit['all_declared_cases_present']
# Neither curves nor slack arms contribute new workload observations.
keys=['cluster','start'];coverage=d.groupby(keys).agg(jobs=('jobs','first'),gpu_h=('fixed_work_gpu_h','first'),coverage=('cohort_share_of_week_gpu_h','first'))
for col in ['jobs','fixed_work_gpu_h','week_allocation_gpu_h','cohort_share_of_week_gpu_h']:
    assert d.groupby(keys)[col].nunique().max()==1
coverage.reset_index().to_csv(OUT/'cohort_coverage.csv',index=False)
summary=d.groupby(['workload','slack']).agg(cases=('run','count'),min_pct=('all_gpu_energy_saving_pct','min'),median_pct=('all_gpu_energy_saving_pct','median'),max_pct=('all_gpu_energy_saving_pct','max')).reset_index()
summary.to_csv(OUT/'conditional_ranges.csv',index=False)
paired=d.pivot(index=['cluster','start','workload'],columns='slack',values='all_gpu_energy_saving_pct')
violations=[]
for a,b in [(0,6),(6,24)]:
    for idx,row in paired.iterrows():
        if row[b]<row[a]-1e-8:violations.append(dict(cluster=idx[0],start=idx[1],workload=idx[2],from_slack=a,to_slack=b,change_percentage_points=float(row[b]-row[a])))
curves=pd.read_csv(ROOT/'outputs/research/tables/dvfs_measured_and_derived.csv');groups={}
for name,cv in curves.groupby('Workload',sort=False):
    v=cv.sort_values('GPU power cap')[['normalized throughput','measured_power_ratio']].to_numpy()
    key=tuple(np.round(v,12).ravel());groups.setdefault(key,[]).append(name)
d['cohort_bound_gap_pp']=d.upper_bound_on_cohort_saving_pct-d.cohort_incremental_gpu_energy_saving_pct
report=dict(planned_arms=len(spec['cases']),verified_arms=len(d),failed_arms=audit['failed_cases'],distinct_cluster_weeks=len(coverage),distinct_job_executions=int(coverage.jobs.sum()),
    coverage_min_pct=float(coverage.coverage.min()*100),coverage_max_pct=float(coverage.coverage.max()*100),
    normalized_curve_equivalence_groups=list(groups.values()),curve_equivalence_tolerance_decimal_places=12,
    by_slack={str(s):dict(min_pct=float(g.all_gpu_energy_saving_pct.min()),max_pct=float(g.all_gpu_energy_saving_pct.max())) for s,g in d.groupby('slack')},
    nonmonotone_greedy_pairs=violations,maximum_cohort_bound_gap_pp=float(d.cohort_bound_gap_pp.max()),
    inference='Descriptive conditional range over fixed scenarios, not confidence interval, independent experiments, actual heterogeneous workload mix, or annual generalization.')
(OUT/'analysis.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
plt.rcParams.update({'font.size':9,'axes.spines.top':False,'axes.spines.right':False,'pdf.fonttype':42,'svg.fonttype':'none'})
order=curves.Workload.unique().tolist();labels=['Fine-tune / Dolly','Fine-tune / P3','Inference / 48 GPUs','Inference / 32 GPUs','Inference / reference','Pretrain / MPT 13B large','Pretrain / MPT 13B small','Pretrain / MPT 7B fast']
cols=[(c,t) for c in ['Earth','Venus','Saturn','Uranus'] for t in ['2020-05-04','2020-07-06','2020-09-07']]
fig,axs=plt.subplots(3,1,figsize=(14,11));fig.subplots_adjust(left=.20,right=.88,bottom=.16,top=.87,hspace=.50)
maximum=float(d.all_gpu_energy_saving_pct.max())
for ax,s,panel in zip(axs,[0,6,24],'abc'):
    data=d[d.slack==s].pivot(index='workload',columns=['cluster','start'],values='all_gpu_energy_saving_pct').reindex(index=order,columns=cols).to_numpy()
    im=ax.imshow(data,vmin=0,vmax=maximum,cmap='YlGnBu',aspect='auto');ax.set_yticks(range(8),labels)
    ax.set_xticks(range(12),[f'{c}\n{t[5:7]}' for c,t in cols]);ax.set_title(f'{panel}   Extra completion allowance: {s} h',loc='left',fontweight='bold',pad=10)
    for i in range(8):
        for j in range(12):
            v=data[i,j]
            ax.text(j,i,'failed' if np.isnan(v) else f'{v:.1f}',ha='center',va='center',fontsize=8,color='white' if v>maximum*.58 else '#172b3a')
    for x in [2.5,5.5,8.5]:ax.axvline(x,color='white',lw=2)
cax=fig.add_axes([.91,.33,.015,.40]);fig.colorbar(im,cax=cax,label='All-GPU normalized energy saving (%)')
fig.suptitle('Temporal validation reveals workload-dependent energy opportunity',x=.04,y=.97,ha='left',fontsize=16,fontweight='bold')
fig.text(.04,.923,'Three calendar-selected weeks | 4 clusters × 8 curve conditions × 3 allowances | fixed-size non-preemptive gangs',fontsize=10)
fig.text(.04,.100,'Each cell retains all background allocations and GPU idle. Homogeneous curve transfer and idle ratio 0.10 are assumptions.',fontsize=9)
fig.text(.04,.073,'May / July / September 2020 (month labels). Inference 48/32 curves coincide; conditions are correlated, not independent replicates.',fontsize=9)
fig.text(.04,.046,'Retrospective completion benchmarks with future allocations known. No actual SLA, useful-work calibration, node energy or grid benefit measured.',fontsize=9)
folder=OUT/'figures';folder.mkdir(exist_ok=True)
for ext in ['png','pdf','svg']:fig.savefig(folder/f'temporal_curve_validation.{ext}',dpi=170)
svg=folder/'temporal_curve_validation.svg';svg.write_text('\n'.join(l.rstrip() for l in svg.read_text().splitlines())+'\n')
(folder/'provenance.json').write_text(json.dumps(dict(source=str(src.relative_to(ROOT)),sha256=hashlib.sha256(src.read_bytes()).hexdigest(),cells=len(d),quantity='all_gpu_energy_saving_pct',scope=report['inference']),indent=2)+'\n')
