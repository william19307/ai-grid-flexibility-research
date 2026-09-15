"""Reanalyse published source tables; no synthetic observations and no GPU experiment."""
from pathlib import Path
import hashlib, json, subprocess
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[3]
SRC=ROOT/'work/research/sources/emerald-ai-demo-may-2025'
CHINA=ROOT/'work/research/sources/PyPSA-China'
OUT=ROOT/'outputs/research'
for d in ['tables','reports','figures']:(OUT/d).mkdir(parents=True,exist_ok=True)
commit=subprocess.check_output(['git','-C',str(SRC),'rev-parse','HEAD'],text=True).strip()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
inventory=[]
for p in sorted((SRC/'data').iterdir()):
    inventory.append({'file':str(p.relative_to(SRC)),'bytes':p.stat().st_size,'sha256':sha(p),'repository_commit':commit})
pd.DataFrame(inventory).to_csv(OUT/'tables/emerald_source_inventory.csv',index=False)

d=pd.read_csv(SRC/'data/dvfs_sweep.csv')
assert len(d)==48 and not d.isna().any().any()
assert not d.duplicated(['Workload','GPU power cap']).any()
assert (d[['throughput','total GPU power','power per GPU']]>0).all().all()
derived=[];selected=[];cv=[]
for name,g in d.groupby('Workload',sort=False):
    g=g.sort_values('GPU power cap').copy();b=g.iloc[-1]
    assert list(g['GPU power cap'])==[100,200,250,300,350,400]
    assert np.allclose(g['normalized throughput'],g.throughput/b.throughput)
    g['measured_power_ratio']=g['total GPU power']/b['total GPU power']
    g['runtime_ratio_equal_work']=1/g['normalized throughput']
    g['gpu_energy_ratio_equal_work']=g['measured_power_ratio']/g['normalized throughput']
    g['inferred_gpu_count']=g['total GPU power']/g['power per GPU']
    derived.append(g)
    # This 0.90 screen is our analysis choice, not an observed SLA.
    s=g[g['normalized throughput']>=.90].sort_values('total GPU power').iloc[0]
    selected.append({'workload':name,'throughput_floor_assumption':.90,'selected_cap_W':int(s['GPU power cap']),
      'measured_throughput_ratio':s['normalized throughput'],'measured_power_reduction_pct':100*(1-s.measured_power_ratio),
      'implied_runtime_increase_pct':100*(s.runtime_ratio_equal_work-1),
      'implied_gpu_energy_change_pct':100*(s.gpu_energy_ratio_equal_work-1)})
    # Leave out interior cap settings only. Endpoints retained; interpolation, no extrapolation.
    for j in range(1,len(g)-1):
        train=g.drop(g.index[j]);test=g.iloc[j]
        pred=np.interp(test['measured_power_ratio'],train.measured_power_ratio,train['normalized throughput'])
        cv.append({'workload':name,'held_out_cap_W':int(test['GPU power cap']),'observed_normalized_throughput':test['normalized throughput'],
          'predicted_normalized_throughput':pred,'absolute_error_percentage_points':100*abs(pred-test['normalized throughput'])})
derived=pd.concat(derived,ignore_index=True);selected=pd.DataFrame(selected);cv=pd.DataFrame(cv)
derived.to_csv(OUT/'tables/dvfs_measured_and_derived.csv',index=False)
selected.to_csv(OUT/'tables/dvfs_90pct_throughput_screen.csv',index=False)
cv.to_csv(OUT/'tables/dvfs_interpolation_holdout.csv',index=False)
cv.groupby('held_out_cap_W')['absolute_error_percentage_points'].agg(['count','mean','max']).to_csv(OUT/'tables/dvfs_interpolation_error_by_cap.csv')

# Compare versions rather than silently choosing a correction.
csv_power=pd.read_csv(SRC/'data/SRP_total_power.csv')
xls_power=pd.read_excel(SRC/'data/Fig2_data.xlsx',sheet_name='SRP_granular',header=1).iloc[:,:2].dropna()
csv_power['timestamp']=pd.to_datetime(csv_power.timestamp);xls_power['timestamp']=pd.to_datetime(xls_power.timestamp)
offset=(csv_power.timestamp-xls_power.timestamp).dt.total_seconds()/3600
assert len(csv_power)==len(xls_power)==400
assert np.array_equal(csv_power.total.to_numpy(),xls_power.total.astype(float).to_numpy())
xls_perf=pd.read_excel(SRC/'data/Fig2_data.xlsx',sheet_name='Performance Data',header=1)
csv_perf=pd.read_csv(SRC/'data/SRP_exp_performance.csv')
jobs=xls_perf.iloc[:6].copy()
weighted=float(np.dot(jobs.Performance,jobs['Weight based on bucket']))
assert np.isclose(jobs['Weight based on bucket'].sum(),1)
assert np.allclose(jobs.Performance,csv_perf.iloc[:6].Performance)
weighted_xls=float(xls_perf.iloc[6].Performance);weighted_csv=float(csv_perf.iloc[6].Performance)
assert np.isclose(weighted,weighted_xls)
jobs.to_csv(OUT/'tables/srp_published_job_performance.csv',index=False)
issues=[
 {'id':'A01','severity':'material_alignment','finding':'All 400 power values identical, but CSV timestamps are exactly 24 h later than XLSX.','handling':'Retain originals; prohibit date-aligned grid counterfactuals until resolved.','offset_hours':sorted(offset.unique().tolist())},
 {'id':'A02','severity':'aggregate_conflict','finding':'Six job performance values match; published weighted aggregates disagree.','handling':'Use XLSX only for explicitly documented weight-based recomputation; do not call weights GPU or compute shares.','csv_weighted_performance':weighted_csv,'xlsx_weighted_performance':weighted_xls,'recomputed_from_xlsx_weights':weighted},
 {'id':'A03','severity':'dependence','finding':'Three inference configurations have identical normalized throughput at all six caps.','handling':'Treat rows as configurations; do not claim eight independent sampled models.'},
 {'id':'A04','severity':'external_validity','finding':'No repeated-run uncertainty, workload-arrival timestamps, or job completion telemetry in the eight enumerated source tables.','handling':'Do not infer statistical confidence, recovery feasibility, workload completion or China-wide availability from this dataset.'}
]
pd.DataFrame(issues).to_json(OUT/'tables/source_conflicts.json',orient='records',force_ascii=False,indent=2)

# Audit the input library without representing it as current measured grid data.
china_load_path=CHINA/'resources/data/load/Hourly_demand_of_31_province_China_modified_V2.1.csv'
load=pd.read_csv(china_load_path);numeric=load.iloc[:,1:]
assert len(load)==8760 and numeric.shape[1]==31
gridstats=pd.DataFrame({'province_code':numeric.columns,'annual_sum_MWh_if_hourly_mean_MW':numeric.sum().values,
 'minimum_input_MW':numeric.min().values,'maximum_input_MW':numeric.max().values,'mean_input_MW':numeric.mean().values,
 'missing_count':numeric.isna().sum().values})
gridstats['load_factor']=gridstats.mean_input_MW/gridstats.maximum_input_MW
gridstats.to_csv(OUT/'tables/china_load_input_audit.csv',index=False)
china_commit=subprocess.check_output(['git','-C',str(CHINA),'rev-parse','HEAD'],text=True).strip()

# Publication-style source-data analysis figure.
C=['#306D99','#66A1BC','#C47C3C','#E5AF70','#9A693A','#247F70','#62A89A','#778491']
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9,'axes.spines.top':False,'axes.spines.right':False,'axes.linewidth':.7,'svg.fonttype':'none','pdf.fonttype':42,'axes.labelcolor':'#283741','text.color':'#283741'})
fig,axs=plt.subplots(2,2,figsize=(12,9.1));fig.subplots_adjust(left=.09,right=.96,bottom=.12,top=.80,wspace=.38,hspace=.85)
fig.text(.06,.948,'EMPIRICAL SOURCE REANALYSIS 01',fontsize=9,color='#247F70',weight='bold')
fig.text(.06,.90,'Measured GPU power–performance trade-offs',fontsize=21,weight='bold')
fig.text(.06,.855,'Published experiment data; independent calculations. No new hardware experiment or China-wide inference.',fontsize=10,color='#65737C')
names={'ft_llama_8b_dolly':'FT Llama 8B / Dolly','ft_llama_8b_p3':'FT Llama 8B / P3','infer_llama_8b_48g':'Inference / 48 GPUs','infer_llama_8b_32g':'Inference / 32 GPUs','infer_llama_8b':'Inference / base','pt_mpt_13b_lg':'PT MPT 13B / large','pt_mpt_13b_sm':'PT MPT 13B / small','pt_mpt_7b_fast':'PT MPT 7B / fast'}
for ax,l,t in zip(axs.flat,'abcd',['Measured response curves','Power reduction with throughput ≥90%','Equal-work GPU energy implication','Interior-point interpolation check']):
 ax.set_title(t,loc='left',fontsize=10.5,weight='bold',pad=12);ax.text(-.14,1.05,l,transform=ax.transAxes,fontsize=15,weight='bold');ax.tick_params(labelsize=8)
for (name,g),col in zip(derived.groupby('Workload',sort=False),C):
 axs[0,0].plot(g.measured_power_ratio*100,g['normalized throughput']*100,'o-',lw=1,ms=3,color=col,label=names[name])
axs[0,0].axhline(90,ls=':',color='#7D878E',lw=.8);axs[0,0].set(xlabel='Measured GPU power (% of 400 W-cap baseline)',ylabel='Throughput (% of baseline)',xlim=(15,103),ylim=(0,105))
axs[0,0].legend(fontsize=6.9,ncol=2,frameon=False,loc='upper left',bbox_to_anchor=(-.025,-.25),columnspacing=.7)
order=selected.sort_values('measured_power_reduction_pct'); y=np.arange(len(order))
axs[0,1].barh(y,order.measured_power_reduction_pct,color='#306D99',height=.63)
axs[0,1].set(yticks=y,yticklabels=[names[w] for w in order.workload],xlabel='Measured GPU power reduction (%)',xlim=(0,36))
for i,v in enumerate(order.measured_power_reduction_pct):axs[0,1].text(v+.5,i,f'{v:.1f}',va='center',fontsize=8)
for (name,g),col in zip(derived.groupby('Workload',sort=False),C):
 axs[1,0].plot((g.runtime_ratio_equal_work-1)*100,(g.gpu_energy_ratio_equal_work-1)*100,'o-',lw=1,ms=3,color=col)
axs[1,0].axhline(0,ls=':',color='#7D878E',lw=.8);axs[1,0].set(xlabel='Implied runtime increase for equal work (%)',ylabel='Implied GPU energy change (%)',xlim=(0,40),ylim=(-30,25))
axs[1,0].text(.02,.95,'Zoom: ≤40% runtime increase\nAssumes sustained measured throughput',transform=axs[1,0].transAxes,fontsize=8,va='top',color='#65737C')
axs[1,1].scatter(cv.observed_normalized_throughput*100,cv.predicted_normalized_throughput*100,s=24,color='#247F70',alpha=.75)
axs[1,1].plot([40,101],[40,101],ls=':',color='#7D878E',lw=.8);axs[1,1].set(xlabel='Held-out measured throughput (%)',ylabel='Interpolated throughput (%)',xlim=(40,101),ylim=(40,101))
axs[1,1].text(.035,.95,f'32 interior points\nMAE = {cv.absolute_error_percentage_points.mean():.2f} percentage points\nWithin-workload interpolation only',transform=axs[1,1].transAxes,fontsize=8,va='top')
fig.text(.06,.053,'Source: Colangelo et al., Nature Energy; ai-emerald/emerald-ai-demo-may-2025, dvfs_sweep.csv.',fontsize=8,color='#65737C')
fig.text(.06,.031,'90% is an analyst-selected throughput screen, not a verified SLA. Eight configurations are not eight independent model samples.',fontsize=8,color='#65737C')
for ext in ['png','svg','pdf']:fig.savefig(OUT/f'figures/empirical_dvfs_reanalysis.{ext}',dpi=190)
plt.close(fig)

summary={'status':'source_reanalysis_not_new_experiment','source_commit':commit,'rows':len(d),'configurations':int(d.Workload.nunique()),
 'interpolation_holdout_points':len(cv),'interpolation_MAE_pp':float(cv.absolute_error_percentage_points.mean()),'interpolation_max_error_pp':float(cv.absolute_error_percentage_points.max()),
 'power_reduction_at_90pct_screen_min_pct':float(selected.measured_power_reduction_pct.min()),'power_reduction_at_90pct_screen_max_pct':float(selected.measured_power_reduction_pct.max()),
 'source_conflicts':issues[:2],'china_load_rows':len(load),'china_load_columns':numeric.shape[1],
 'china_load_input_annual_total_TWh':float(numeric.sum().sum()/1e6),'china_load_commit':china_commit,'china_load_sha256':sha(china_load_path)}
(OUT/'tables/reanalysis_summary.json').write_text(json.dumps(summary,indent=2))
print(json.dumps(summary,indent=2))
