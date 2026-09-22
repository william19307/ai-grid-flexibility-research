"""Retain strict infeasibility, analytic interval witnesses and boundary effects."""
from pathlib import Path
from dataclasses import asdict,replace
import sys,json,csv,hashlib,time
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'work/research/models'));sys.path.insert(0,str(ROOT/'work/research/analysis'))
from strict_workload import sample_fixed_windows,demand_bound,edf_replay
from sequential_tasks import schedule
from run_regional_2030_s0_s3 import helios_queue_jobs,WEEK_STARTS

OUT=ROOT/'outputs/research/revision/service'


def main():
    if (OUT/'cases').exists():raise FileExistsError('Existing service cases retained')
    (OUT/'cases').mkdir(parents=True,exist_ok=True)
    sources=['work/research/models/strict_workload.py','work/research/models/sequential_tasks.py',
             'work/research/analysis/audit_strict_service_revision.py','work/research/analysis/run_regional_2030_s0_s3.py']
    input_path='work/research/prepared/helios_completed_gpu_jobs_sample.csv.gz'
    sha=lambda p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
    (OUT/'run_manifest.json').write_text(json.dumps(dict(started_unix=time.time(),source_sha256={p:sha(p) for p in sources},
        input_sha256={input_path:sha(input_path)},parameters=dict(utilizations=[.3,.5,.7,.9],slack_base_h=[6.,24.],slack_multiplier=1.,seeds=WEEK_STARTS)),indent=2)+'\n')
    (OUT/'implementation_snapshot.json').write_text(json.dumps({p:(ROOT/p).read_text() for p in sources},indent=2)+'\n')
    rows=[];thresholds=[];max_work_error=0.
    for season,start in WEEK_STARTS.items():
        for slack in [6.,24.]:
            for boundary in ['historical_clip','full_tail']:
                # One ex ante job shape; utilization scales work once, never deadlines.
                unit_jobs,horizon,meta=sample_fixed_windows(168,1.,start%24,1.,slack,start,boundary)
                bound=demand_bound(unit_jobs);max_u=bound['maximum_work_scale']
                below=[replace(j,work=j.work*max_u*(1-1e-6)) for j in unit_jobs]
                above=[replace(j,work=j.work*max_u*(1+1e-6)) for j in unit_jobs]
                assert schedule(below,[1.],[1.],horizon,0.)['feasible']
                assert edf_replay(below,horizon)['feasible']
                assert not schedule(above,[1.],[1.],horizon,0.)['feasible']
                assert not edf_replay(above,horizon)['feasible']
                thresholds.append(dict(season=season,slack_base_h=slack,boundary=boundary,maximum_feasible_arrival_utilization=max_u,
                                       service_horizon=horizon,threshold_lp_and_edf_agree=True))
                for u in [.3,.5,.7,.9]:
                    jobs=[replace(j,work=j.work*u) for j in unit_jobs]
                    name=f'{season}_u{u:g}_slack{slack:g}_{boundary}'
                    constraint=demand_bound(jobs);edf=edf_replay(jobs,horizon)
                    lp=schedule(jobs,[1.],[1.],horizon,0.)
                    assert lp['feasible']==edf['feasible']==constraint['feasible'],name
                    error=abs(sum(j.work for j in jobs)-u*168);max_work_error=max(max_work_error,error)
                    assert error<1e-10
                    legacy,guard=helios_queue_jobs(168,u,start%24,1.,slack,start)
                    legacy_work=sum(j.work for j in legacy)
                    result=dict(name=name,parameters=dict(season=season,start=start,u=u,slack=slack,boundary=boundary),
                                source_meta=meta,jobs=[asdict(j) for j in jobs],demand_bound=constraint,edf=edf,
                                lp=dict(feasible=lp['feasible'],message=lp.get('message')),
                                legacy_guard=guard,legacy_guard_actual_work=legacy_work)
                    (OUT/'cases'/f'{name}.json').write_text(json.dumps(result,indent=2)+'\n')
                    rows.append(dict(case=name,season=season,utilization=u,slack_base_h=slack,boundary=boundary,
                                     service_horizon=horizon,strict_feasible=lp['feasible'],maximum_feasible_arrival_utilization=max_u,
                                     fixed_work=u*168,critical_density=constraint['maximum_density'],
                                     critical_start=constraint['critical_interval']['start'],critical_end=constraint['critical_interval']['end'],
                                     edf_unfinished_work=edf['unfinished_work'],edf_missed_batches=len(edf['missed_jobs']),
                                     historical_guard_extended=guard['extended'],historical_guard_final_work=legacy_work,
                                     boundary_raw_gpu_hour_clipping_share=meta['raw_gpu_hour_clipping_share']))
                    print(name,lp['feasible'],round(max_u,6),flush=True)
    for filename,records in [('strict_service_results.csv',rows),('feasibility_thresholds.csv',thresholds)]:
        with (OUT/filename).open('w') as f:
            writer=csv.DictWriter(f,fieldnames=list(records[0]),lineterminator='\n');writer.writeheader();writer.writerows(records)
    report=dict(cases=len(rows),feasible=sum(r['strict_feasible'] for r in rows),infeasible=sum(not r['strict_feasible'] for r in rows),
                independent_interval_lp_edf_agreement=True,threshold_cross_checks=len(thresholds),maximum_fixed_work_error=max_work_error,
                invalid_success_claims='No infeasible case is silently repaired or excluded from the result table.',
                limitations=['Deadlines remain assumptions; no empirical SLA.',
                             'Full-tail finite cohort has no arrivals after 168h; not an equilibrium load estimate.',
                             'Historical clipping retained only as a paired diagnostic.',
                             'Per-job GPU parallelism, gang scheduling, checkpoint costs and mixed workload types remain unresolved.'])
    (OUT/'verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))


if __name__=='__main__':main()
