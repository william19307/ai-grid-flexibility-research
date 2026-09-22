"""Frozen factorial under historical relative tariff shapes, not system costs."""
from pathlib import Path
import sys,json,hashlib,time,itertools,traceback
import numpy as np,pandas as pd
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'work/research/models'));sys.path.insert(0,str(ROOT/'work/research/analysis'))
from gang_policy import coordinate_policy,independent_job_bound,schedule_cost
from policy_attribution import attribution,optimal_share_bracket
from trace_occupancy import integrate_occupancy
from run_regional_smoke_s0_s1_s2 import tariff_shape,OFFICIAL_TOU
OUT=ROOT/'outputs/research/revision/policy';CURVE=ROOT/'outputs/research/tables/dvfs_measured_and_derived.csv'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def freeze():
    path=OUT/'manifest.json'
    if path.exists():raise FileExistsError(path)
    OUT.mkdir(exist_ok=True)
    cases=[dict(cluster=c,start='2020-04-06',workload=w,slack=s,tariff=t) for c,w,s,t in itertools.product(['Earth','Venus','Saturn','Uranus'],['ft_llama_8b_dolly','infer_llama_8b_32g','pt_mpt_13b_lg'],[0,6,24],['Jiangsu','Gansu','Guizhou'])]
    files=[Path(__file__).resolve(),ROOT/'work/research/models/gang_policy.py',ROOT/'work/research/models/policy_attribution.py',ROOT/'work/research/models/trace_occupancy.py',ROOT/'work/research/analysis/run_regional_smoke_s0_s1_s2.py']
    inputs=[CURVE,ROOT/'outputs/research/tables/data_registry.csv']+[ROOT/'work/research/sources/helios_sensetime/data'/c/f for c in ['Earth','Venus','Saturn','Uranus'] for f in ['cluster_log.csv','cluster_gpu_number.csv']]+list((ROOT/'work/research/sources/tariffs').glob('*'))
    spec=dict(written_unix=time.time(),cases=cases,source_sha256={str(p.relative_to(ROOT)):sha(p) for p in files},input_sha256={str(p.relative_to(ROOT)):sha(p) for p in inputs if p.is_file()},
        prices={t:dict(hours=tariff_shape(np.arange(192),'official',t).tolist(),source=OFFICIAL_TOU[t]) for t in ['Jiangsu','Gansu','Guizhou']},
        rules=dict(C00='Observed starts, full speed',C10='Observed starts, variable mode (end time may change)',C01='Flexible starts, full speed',C11='Flexible starts, variable mode'),
        objective='Same integral of normalized GPU incremental power times relative price for all cells; frozen historical TOU shapes, no claim of actual 2020 bills, grid system cost, or present tariff applicability.',
        information='All cells know the same complete retrospective workload, background, capacity and price; future information is not removed and no deployability claim is made.',
        algorithm='C10 and C01 use one fixed observed-start-order coordinate sweep from C00. C11 starts from the lower-bill parent and uses one sweep. Strict improvements only; not global optima. Per-job minima ignoring shared capacity provide lower bounds for each cell.',
        selection='Reuse development April week; three representative existing curves spanning fine-tuning, inference and pretraining chosen after energy-only diagnostics. This is a mechanistic factorial, not an untouched validation sample.',
        clock='Relative tariff clock aligned to trace timestamps by assumption; cluster locations and timestamp time zones do not establish these provinces. Phase sensitivity remains required.',
        background='All noncohort allocations retained for 192h; cohort submitted and completed within168h, positive GPU/time, COMPLETED; idle ratio0.10, occupied background at full reference power.')
    path.write_text(json.dumps(spec,indent=2)+'\n');(OUT/'source_snapshot.json').write_text(json.dumps({str(p.relative_to(ROOT)):p.read_text() for p in files},indent=2)+'\n')
    print('Frozen',len(cases),'factorials')

def run():
    spec=json.loads((OUT/'manifest.json').read_text())
    for p,h in {**spec['source_sha256'],**spec['input_sha256']}.items():assert sha(ROOT/p)==h,p
    target=OUT/'runs';target.mkdir(exist_ok=False);curves=pd.read_csv(CURVE);cache=None;rows=[]
    for case in spec['cases']:
        name='_'.join(str(case[k]) for k in ['cluster','workload','slack','tariff']);folder=target/name;folder.mkdir();started=time.time()
        try:
            c=case['cluster'];src=ROOT/'work/research/sources/helios_sensetime/data'/c
            if cache!=c:
                d=pd.read_csv(src/'cluster_log.csv',parse_dates=['submit_time','start_time','end_time']);d=d[d.gpu_num>0];cap=pd.read_csv(src/'cluster_gpu_number.csv',parse_dates=['date']).set_index('date')['total'];cache=c
            t0=pd.Timestamp(case['start']);t1=t0+pd.Timedelta(days=7);end=t0+pd.Timedelta(hours=192)
            co=d[(d.state=='COMPLETED')&(d.submit_time>=t0)&(d.end_time<=t1)&(d.duration>0)];active=d[(d.start_time<end)&(d.end_time>t0)]
            sec=lambda s:(s-t0).dt.total_seconds().to_numpy()
            release=sec(co.submit_time)/3600;deadline=(sec(co.end_time)+case['slack']*3600)/3600;gpu=co.gpu_num.to_numpy();work=gpu*co.duration.to_numpy()/3600
            edge_sec=np.unique(np.r_[np.arange(193)*3600,sec(co.submit_time),sec(co.end_time)+case['slack']*3600,np.clip(sec(active.start_time),0,192*3600),np.clip(sec(active.end_time),0,192*3600)])
            edges=edge_sec/3600;baseline=integrate_occupancy(sec(active.start_time),sec(active.end_time),active.gpu_num.to_numpy(),edge_sec)
            capacities=cap.reindex(t0+pd.to_timedelta(np.floor(edge_sec[:-1]/86400).astype(int),unit='D')).to_numpy(float)
            if not np.isfinite(capacities).all():raise ValueError('Missing capacity')
            free=capacities-baseline['mean_resources'];cv=curves[curves.Workload==case['workload']].sort_values('GPU power cap');q=cv['normalized throughput'].to_numpy();p=cv['measured_power_ratio'].to_numpy()-.1
            pe=np.arange(193.);prices=np.asarray(spec['prices'][case['tariff']]['hours']);full=int(np.flatnonzero(q==1.)[0]);original_start=sec(co.start_time)/3600
            plan=np.c_[original_start,sec(co.end_time)/3600,np.full(len(co),full)]
            states={'C00':dict(plan=plan,edges=edges,free_capacity=free,incremental_bill=schedule_cost(plan,gpu,p,pe,prices))};lower={'C00':states['C00']['incremental_bill']}
            for cell,am,at in [('C10',True,False),('C01',False,True),('C11',True,True)]:
                seed='C00' if cell!='C11' else min(['C10','C01'],key=lambda k:states[k]['incremental_bill'])
                initial=states[seed]
                states[cell]=coordinate_policy(release,deadline,work,gpu,original_start,initial['plan'],initial['edges'],initial['free_capacity'],q,p,pe,prices,am,at)
                states[cell]['seed']=seed
                lower[cell]=float(independent_job_bound(release,deadline,work,gpu,original_start,q,p,pe,prices,am,at).sum())
            upper={k:states[k]['incremental_bill'] for k in states};estimate=attribution(upper);bracket=optimal_share_bracket(lower,upper)
            for cell,state in states.items():
                pl=state['plan'];pd.DataFrame(dict(source_row=co.index,start_s=np.round(pl[:,0]*3600,8),end_s=np.round(pl[:,1]*3600,8),mode=pl[:,2].astype(int),gpus=gpu)).to_csv(folder/f'{cell}.csv.gz',index=False,compression={'method':'gzip','mtime':0})
            row=dict(run=name,**case,status='constructed_pending_independent_verification',jobs=len(co),runtime_s=time.time()-started,**estimate,optimal_mode_share_lower_pct=bracket['lower_pct'],optimal_mode_share_upper_pct=bracket['upper_pct'])
            details=dict(**row,upper_incremental_bill=upper,lower_incremental_bill=lower,global_optimum_mode_share_bracket=bracket,seed_C11=states['C11']['seed'])
            (folder/'summary.json').write_text(json.dumps(details,indent=2)+'\n')
        except Exception as e:
            row=dict(run=name,**case,status='error',error_type=type(e).__name__,error=str(e),runtime_s=time.time()-started)
            (folder/'error.txt').write_text(traceback.format_exc());(folder/'summary.json').write_text(json.dumps(row,indent=2)+'\n')
        rows.append(row);pd.DataFrame(rows).to_csv(OUT/'outcomes.csv',index=False)
        print(json.dumps({k:row[k] for k in ['run','status','runtime_s']}),flush=True)
    (OUT/'complete.json').write_text(json.dumps(dict(cases=len(rows),errors=sum(r['status']=='error' for r in rows),all_planned_arms_attempted=len(rows)==len(spec['cases'])),indent=2)+'\n')

if __name__=='__main__':
    if len(sys.argv)!=2 or sys.argv[1] not in ['freeze','run']:raise SystemExit('Use freeze or run')
    freeze() if sys.argv[1]=='freeze' else run()
