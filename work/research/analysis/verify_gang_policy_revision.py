"""Raw-event schedule audit, independent hourly bills and cost-bracket vertices."""
from pathlib import Path
import json,hashlib,itertools,time
import numpy as np,pandas as pd
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'outputs/research/revision/policy'

def integral(t,prices):
    t=np.asarray(t);i=np.minimum(np.floor(t).astype(int),len(prices)-1);cum=np.r_[0,np.cumsum(prices)]
    return cum[i]+(t-i)*prices[i]

def bound_direct(release,deadline,work,gpu,start,q,p,prices,am,at):
    best=np.full(len(work),np.inf)
    for m in (range(len(q)) if am else np.flatnonzero(q==1.)):
        duration=work/gpu/q[m]
        # Evaluate all price breakpoints and shifted breakpoints for all jobs.
        # Each vector is one candidate family, independently clipped/filtered.
        candidates=[release,deadline-duration] if at else [start]
        if at:
            candidates += [np.full(len(work),float(h)) for h in range(193)]
            candidates += [h-duration for h in range(193)]
        for s in candidates:
            ok=(s>=release-1e-11)&(s+duration<=deadline+1e-11)&(s>=0)&(s+duration<=192+1e-11)
            if not ok.any():continue
            value=gpu[ok]*p[m]*(integral(s[ok]+duration[ok],prices)-integral(s[ok],prices))
            best[ok]=np.minimum(best[ok],value)
    assert np.isfinite(best).all()
    return float(best.sum())

def share_vertices(lower,upper):
    c0=upper['C00'];lo=np.array([lower[k] for k in ['C10','C01','C11']]);hi=np.array([upper[k] for k in ['C10','C01','C11']])
    # Each vertex intersects three cost-box/nesting boundary planes.
    A=np.r_[np.eye(3),-np.eye(3),[[1,0,0],[0,1,0],[-1,0,1],[0,-1,1]]];b=np.r_[hi,-lo,c0,c0,0,0]
    ratios=[]
    scale=max(1.,c0)
    for ids in itertools.combinations(range(len(b)),3):
        a=A[list(ids)]
        if abs(np.linalg.det(a))<1e-10:continue
        x=np.linalg.solve(a,b[list(ids)])
        if np.max(A@x-b)>1e-8*scale:continue
        total=c0-x[2]
        if total>1e-8:ratios.append(100*.5*(c0-x[0]+x[1]-x[2])/total)
    return min(ratios),max(ratios)

def main():
    spec=json.loads((OUT/'manifest.json').read_text());snap=json.loads((OUT/'source_snapshot.json').read_text())
    for path,h in spec['input_sha256'].items():assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==h
    for path,h in spec['source_sha256'].items():assert hashlib.sha256(snap[path].encode()).hexdigest()==h
    (OUT/'verification_source_snapshot.json').write_text(json.dumps(dict(written_unix=time.time(),scope='Verifier archived before verification, after experimental construction began',source=Path(__file__).read_text()),indent=2)+'\n')
    cv=pd.read_csv(ROOT/'outputs/research/tables/dvfs_measured_and_derived.csv');cache=None;rows=[];cellrows=[];failures=[];max_work=max_window=max_peak=0.
    for case in spec['cases']:
        name='_'.join(str(case[k]) for k in ['cluster','workload','slack','tariff']);folder=OUT/'runs'/name
        sm=json.loads((folder/'summary.json').read_text())
        if sm['status']=='error':failures.append(sm);continue
        cluster=case['cluster'];src=ROOT/'work/research/sources/helios_sensetime/data'/cluster
        if cache!=cluster:
            raw=pd.read_csv(src/'cluster_log.csv',parse_dates=['submit_time','start_time','end_time']);raw=raw[raw.gpu_num>0]
            cap=pd.read_csv(src/'cluster_gpu_number.csv',parse_dates=['date']).set_index('date')['total'];cache=cluster
        t0=pd.Timestamp(case['start']);t1=t0+pd.Timedelta(days=7);end=t0+pd.Timedelta(hours=192)
        co=raw[(raw.state=='COMPLETED')&(raw.submit_time>=t0)&(raw.end_time<=t1)&(raw.duration>0)]
        sec=lambda s:(s-t0).dt.total_seconds().to_numpy()
        release=sec(co.submit_time);deadline=sec(co.end_time)+case['slack']*3600;gpu=co.gpu_num.to_numpy();work=gpu*co.duration.to_numpy()/3600;orig=sec(co.start_time)
        bg=raw[~raw.index.isin(co.index)];bg=bg[(bg.start_time<end)&(bg.end_time>t0)];ba=np.maximum(0,sec(bg.start_time));bb=np.minimum(192*3600,sec(bg.end_time));bgpu=bg.gpu_num.to_numpy()
        curve=cv[cv.Workload==case['workload']].sort_values('GPU power cap');q=curve['normalized throughput'].to_numpy();p=curve['measured_power_ratio'].to_numpy()-.1
        prices=np.array(spec['prices'][case['tariff']]['hours']);hour_capacity=cap.reindex(t0+pd.to_timedelta(np.arange(192)//24,unit='D')).to_numpy(float)
        bg_hour=np.array([np.maximum(0,np.minimum(bb,(h+1)*3600)-np.maximum(ba,h*3600))@bgpu/3600 for h in range(192)])
        fixed=.1*hour_capacity+.9*bg_hour;upper={};lower={};profiles={}
        for cell,am,at in [('C00',False,False),('C10',True,False),('C01',False,True),('C11',True,True)]:
            plan=pd.read_csv(folder/f'{cell}.csv.gz',float_precision='round_trip');assert plan.source_row.is_unique and plan.source_row.tolist()==co.index.tolist()
            a=plan.start_s.to_numpy();b=plan.end_s.to_numpy();m=plan['mode'].to_numpy(int)
            assert np.array_equal(plan['mode'].to_numpy(),m) and np.all((m>=0)&(m<len(q))) and np.array_equal(plan.gpus.to_numpy(),gpu)
            assert np.all(b>a)
            err=float(np.max(abs((b-a)/3600*gpu*q[m]-work)));window=max(0.,float(np.max(release-a)),float(np.max(b-deadline)))
            max_work=max(max_work,err);max_window=max(max_window,window);assert err<1e-7 and window<1e-7
            if not at:assert np.max(abs(a-orig))<1e-7
            if not am:assert np.all(q[m]==1.)
            ev,ix=np.unique(np.r_[ba,bb,a,b,np.arange(193)*3600],return_inverse=True)
            usage=np.cumsum(np.bincount(ix,weights=np.r_[bgpu,-bgpu,gpu,-gpu,np.zeros(193)]))[:-1]
            limits=cap.reindex(t0+pd.to_timedelta(np.floor(ev[:-1]/86400).astype(int),unit='D')).to_numpy(float)
            assert np.isfinite(limits).all() and usage.min()>=0
            excess=max(0.,float(np.max(usage-limits)));max_peak=max(max_peak,excess);assert excess==0.
            cohort_hour=np.array([np.maximum(0,np.minimum(b,(h+1)*3600)-np.maximum(a,h*3600))@(gpu*p[m])/3600 for h in range(192)])
            profiles[cell]=fixed+cohort_hour;upper[cell]=float(cohort_hour@prices)
            lower[cell]=upper[cell] if cell=='C00' else bound_direct(release/3600,deadline/3600,work,gpu,orig/3600,q,p,prices,am,at)
            assert np.isclose(upper[cell],sm['upper_incremental_bill'][cell],atol=1e-6,rtol=1e-10)
            assert np.isclose(lower[cell],sm['lower_incremental_bill'][cell],atol=1e-6,rtol=1e-10)
            assert lower[cell]<=upper[cell]+1e-6
            cellrows.append(dict(run=name,**case,cell=cell,incremental_bill=upper[cell],lower_incremental_bill=lower[cell],all_gpu_bill=float(profiles[cell]@prices),all_gpu_energy=float(profiles[cell].sum()),peak_normalized_gpu_power=float(profiles[cell].max()),max_work_error_gpu_h=err,max_window_violation_s=window,capacity_excess_gpus=excess))
        assert upper['C11']<=min(upper['C10'],upper['C01'])+1e-6 and max(upper['C10'],upper['C01'])<=upper['C00']+1e-6
        total=upper['C00']-upper['C11'];mode=.5*(upper['C00']-upper['C10']+upper['C01']-upper['C11']);timing=total-mode
        for key,val in [('total_saving',total),('mode_shapley',mode),('start_shapley',timing)]:assert np.isclose(val,sm[key],atol=1e-6)
        share=100*mode/total if total>1e-9 else None
        if total>1e-8:
            lo,hi=share_vertices(lower,upper);br=sm['global_optimum_mode_share_bracket'];assert np.isclose(lo,br['lower_pct'],atol=1e-5) and np.isclose(hi,br['upper_pct'],atol=1e-5)
        else:lo=hi=None
        if case['slack']==0:
            assert np.isclose(upper['C10'],upper['C00'],atol=1e-6) and np.isclose(lower['C10'],upper['C00'],atol=1e-6)
            assert share is None or share<=50+1e-6
            assert hi is None or hi<=50+1e-5
        pd.DataFrame(dict(hour=np.arange(192),relative_price=prices,**profiles)).to_csv(folder/'verified_hourly_profiles.csv.gz',index=False,compression={'method':'gzip','mtime':0})
        rows.append(dict(run=name,**case,jobs=len(co),constructed_total_bill_saving_pct=100*total/float(profiles['C00']@prices),constructed_all_gpu_energy_saving_pct=100*(profiles['C00'].sum()-profiles['C11'].sum())/profiles['C00'].sum(),mode_share_pct=share,optimal_mode_share_lower_pct=lo,optimal_mode_share_upper_pct=hi,interaction=upper['C10']+upper['C01']-upper['C00']-upper['C11'],mode_first=upper['C00']-upper['C10']))
        print(name,flush=True)
    pd.DataFrame(rows).to_csv(OUT/'certified_factorials.csv',index=False);pd.DataFrame(cellrows).to_csv(OUT/'certified_cells.csv',index=False)
    (OUT/'failed_cases.json').write_text(json.dumps(failures,indent=2)+'\n')
    assert len(rows)+len(failures)==len(spec['cases'])
    report=dict(verified_factorials=len(rows),verified_schedules=len(cellrows),failed_factorials=len(failures),all_declared_cases_accounted_for=True,max_work_error_gpu_h=max_work,max_service_window_violation_s=max_window,max_aggregate_gpu_excess=max_peak,
        all_four_policies_same_cohort_and_background=True,independent_hourly_power_and_price_integration=True,independent_per_job_bound_and_fractional_share_vertex_check=True,zero_allowance_fixed_start_no_slowdown_verified=True,
        scope='Retrospective, aggregate fixed-size gangs; normalized conditional GPU bill and policy-specific attribution, not actual node power, system cost, global schedule optimality or online operation.')
    (OUT/'independent_verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))

if __name__=='__main__':main()
