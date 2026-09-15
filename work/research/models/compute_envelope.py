"""Optimistic two-block workload-conserving response envelope.

Measured GPU power/throughput modes, analyst-specified utilization and horizons.
No grid data, arrival traces, market behavior, switching losses or site overhead.
This is a component benchmark, not national research results or a hardware rerun.
"""
from pathlib import Path
import json
import numpy as np
import pandas as pd
from scipy.optimize import linprog

ROOT=Path(__file__).resolve().parents[3]

def baseline_power(q,p,u):
    fit=linprog(p,A_eq=np.array([np.ones(len(q)),q]),b_eq=[1,u],bounds=(0,1),method='highs')
    if not fit.success:raise ValueError(f'Baseline infeasible at throughput {u}: {fit.message}')
    return float(fit.fun),fit.x

def response_envelope(q,p,u,event_h,recovery_h):
    q=np.asarray(q,float);p=np.asarray(p,float);m=len(q)
    assert event_h>0 and recovery_h>=0
    assert len(q)==len(p) and np.all(q>0) and np.all(p>0)
    base,_=baseline_power(q,p,u)
    # x_event and x_recovery are mode time fractions within each block.
    aeq=np.zeros((3,2*m));aeq[0,:m]=1;aeq[1,m:]=1
    aeq[2,:m]=event_h*q;aeq[2,m:]=recovery_h*q
    beq=np.array([1,1,u*(event_h+recovery_h)])
    fit=linprog(np.r_[p,np.zeros(m)],A_eq=aeq,b_eq=beq,bounds=(0,1),method='highs')
    if not fit.success:raise ValueError(fit.message)
    e=fit.x[:m];r=fit.x[m:];qe=float(q@e);qr=float(q@r);pe=float(p@e);pr=float(p@r)
    total_work=event_h*qe+recovery_h*qr
    theoretical_min_q=max(float(q.min()),(u*(event_h+recovery_h)-recovery_h*q.max())/event_h)
    assert abs(total_work-beq[2])<1e-8
    assert qe>=theoretical_min_q-1e-8
    assert np.max(np.abs(aeq@fit.x-beq))<1e-8
    return {'baseline_gpu_power_W':base,'event_gpu_power_W':pe,'recovery_gpu_power_W':pr,
      'event_normalized_throughput':qe,'recovery_normalized_throughput':qr,
      'work_completed_full_speed_hours':total_work,'required_work_full_speed_hours':float(beq[2]),
      'work_conservation_residual':float(total_work-beq[2]),'minimum_event_throughput_analytic':theoretical_min_q,
      'event_power_reduction_pct':100*(1-pe/base),'recovery_power_increase_pct':100*(pr/base-1) if recovery_h>0 else None,
      'event_mode_fractions':e.tolist(),'recovery_mode_fractions':r.tolist()}

def verify_solver():
    # Independent two-mode hand calculation: L=3, R=3, u=.9 => q_event=.8,
    # q_recovery=1; linear p=q -> 11.111...% reduction relative to .9 baseline.
    q=np.array([.5,1]);p=np.array([.5,1]);r=response_envelope(q,p,.9,3,3)
    assert np.isclose(r['event_normalized_throughput'],.8)
    assert np.isclose(r['event_power_reduction_pct'],100/9)
    for u in [.5,.7,.9,1.]:
        r=response_envelope(q,p,u,3,0)
        assert abs(r['event_power_reduction_pct'])<1e-7
    for recovery in [0,1,3,6]:
        r=response_envelope(q,p,1,3,recovery)
        assert abs(r['event_power_reduction_pct'])<1e-7
    vals=[response_envelope(q,p,.9,3,r)['event_power_reduction_pct'] for r in [0,1,3,6]]
    assert np.all(np.diff(vals)>=-1e-8)
    return ['two_mode_analytic_solution','zero_recovery_no_reduction','full_utilization_no_reduction','recovery_monotonicity','work_conservation']

if __name__=='__main__':
    checks=verify_solver()
    data=pd.read_csv(ROOT/'outputs/research/tables/dvfs_measured_and_derived.csv');rows=[];details=[]
    for name,g in data.groupby('Workload',sort=False):
        q=g['normalized throughput'].to_numpy();p=g['total GPU power'].to_numpy()
        for u in [.6,.75,.9,.95,1.]:
            for recovery in [0,1,3,6,12]:
                result=response_envelope(q,p,u,3,recovery)
                keys={'workload':name,'utilization_assumption':u,'event_h':3,'recovery_h_assumption':recovery}
                details.append({**keys,**result})
                rows.append({**keys,**{k:v for k,v in result.items() if not isinstance(v,list)}})
    table=pd.DataFrame(rows)
    for (_,u),g in table.groupby(['workload','utilization_assumption']):
        assert np.all(np.diff(g.sort_values('recovery_h_assumption').event_power_reduction_pct)>=-1e-7)
        assert abs(g[g.recovery_h_assumption==0].event_power_reduction_pct.iloc[0])<1e-7
    assert table.work_conservation_residual.abs().max()<1e-8
    assert table.loc[table.utilization_assumption==1,'event_power_reduction_pct'].abs().max()<1e-7
    out=ROOT/'outputs/research/tables'
    table.to_csv(out/'compute_envelope_benchmark_NOT_grid_results.csv',index=False)
    (out/'compute_envelope_mode_allocations.json').write_text(json.dumps(details,indent=2))
    status={'status':'controlled_component_benchmark','cases':len(rows),'verified_checks':checks,
      'additional_measured_mode_checks':['no_response_without_recovery','no_response_at_full_throughput','recovery_monotonicity','all_200_cases_conserve_work'],
      'max_work_residual':float(table.work_conservation_residual.abs().max()),
      'assumptions':['all_work_available_at_start','single_terminal_deadline','fractional_time_sharing_between_measured_modes','zero_switching_cost','GPU_power_only','no_grid_or_price_model','utilization_and_recovery_are_scenarios_not_observations']}
    (out/'compute_envelope_validation.json').write_text(json.dumps(status,indent=2))
    print(json.dumps(status,indent=2))
    print(table[(table.utilization_assumption==.9)&(table.recovery_h_assumption==3)][['workload','event_power_reduction_pct','recovery_power_increase_pct']].to_string(index=False))
