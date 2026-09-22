"""Rebuild true ordered GPU occupancy, preserving boundaries and job states.

No inferred power, no sampled arrivals, no invented deadlines or utilization.
Reported capacity is tested against concurrent allocations, not assumed valid.
"""
from pathlib import Path
import sys,json,hashlib
import numpy as np,pandas as pd
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'work/research/models'))
from trace_occupancy import integrate_occupancy
SRC=ROOT/'work/research/sources/helios_sensetime/data'
OUT=ROOT/'outputs/research/revision/service/chronological'


def main():
    if (OUT/'audit.json').exists():raise FileExistsError('Existing chronological audit retained')
    OUT.mkdir(parents=True,exist_ok=True);audit={};tables=[]
    for cluster in ['Venus','Saturn','Earth','Uranus']:
        path=SRC/cluster/'cluster_log.csv';capacity_path=SRC/cluster/'cluster_gpu_number.csv'
        raw=pd.read_csv(path);capacity=pd.read_csv(capacity_path,parse_dates=['date']).set_index('date')
        assert capacity.index.is_unique and not capacity.total.isna().any() and (capacity.total>=0).all()
        for column in ['submit_time','start_time','end_time']:raw[column]=pd.to_datetime(raw[column])
        valid=(raw.gpu_num>0)&raw[['start_time','end_time','gpu_num']].notna().all(axis=1)&(raw.end_time>=raw.start_time)
        jobs=raw[valid].copy()
        t0=capacity.index.min();t1=capacity.index.max()+pd.Timedelta(days=1)
        calendar=pd.date_range(t0,t1,freq='h');edges=(calendar-t0).total_seconds().to_numpy()
        starts=(jobs.start_time-t0).dt.total_seconds().to_numpy();ends=(jobs.end_time-t0).dt.total_seconds().to_numpy()
        all_result=integrate_occupancy(starts,ends,jobs.gpu_num.to_numpy(),edges)
        completed=(jobs.state=='COMPLETED').to_numpy()
        done_result=integrate_occupancy(starts[completed],ends[completed],jobs.gpu_num.to_numpy()[completed],edges)
        caps=capacity.total.reindex(calendar[:-1].floor('D')).to_numpy(float)
        frame=pd.DataFrame(dict(time=calendar[:-1],cluster=cluster,reported_gpus=caps,
                                all_mean_gpus=all_result['mean_resources'],all_peak_gpus=all_result['peak_resources'],
                                completed_mean_gpus=done_result['mean_resources'],completed_peak_gpus=done_result['peak_resources']))
        known=np.isfinite(caps)
        week=frame.set_index('time').resample('W-MON',closed='left',label='left').agg(
            hours=('all_mean_gpus','size'),capacity_known_hours=('reported_gpus','count'),
            reported_gpu_hours=('reported_gpus','sum'),all_gpu_hours=('all_mean_gpus','sum'),
            completed_gpu_hours=('completed_mean_gpus','sum'),max_concurrent_gpus=('all_peak_gpus','max'))
        week['full_week']=week.hours==168
        week['capacity_coverage_complete']=week.capacity_known_hours==week.hours
        week['allocation_utilization']=week.all_gpu_hours/week.reported_gpu_hours
        week['completed_allocation_utilization']=week.completed_gpu_hours/week.reported_gpu_hours
        week.to_csv(OUT/f'{cluster}_weekly_summary.csv')
        active=(starts<edges[-1])&(ends>0)
        by_state={}
        for state in sorted(jobs.state.unique()):
            mask=(jobs.state==state).to_numpy()
            value=integrate_occupancy(starts[mask],ends[mask],jobs.gpu_num.to_numpy()[mask],edges)
            by_state[state]=value['total_resource_seconds']/3600
        assert np.isclose(sum(by_state.values()),all_result['total_resource_seconds']/3600)
        audit[cluster]=dict(source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),capacity_sha256=hashlib.sha256(capacity_path.read_bytes()).hexdigest(),
            source_rows=len(raw),positive_gpu_rows=int((raw.gpu_num>0).sum()),valid_gpu_intervals=len(jobs),
            invalid_positive_gpu_rows=int(((raw.gpu_num>0)&~valid).sum()),duplicate_job_id_rows=int(raw.job_id.duplicated().sum()),
            clock_note='Source timestamps used as supplied; timezone not inferred.',
            capacity_start=str(t0),capacity_end_exclusive=str(t1),hours=len(frame),capacity_missing_hours=int((~known).sum()),
            gpu_hours_by_state=by_state,total_gpu_hours=all_result['total_resource_seconds']/3600,
            completed_gpu_hours=done_result['total_resource_seconds']/3600,
            carry_in_jobs=all_result['carry_in_intervals'],carry_out_jobs=all_result['carry_out_intervals'],
            jobs_outside_capacity_calendar=int((~active).sum()),
            hours_all_peak_exceeds_reported_capacity=int(np.sum((all_result['peak_resources']>caps+1e-7)&known)),
            hours_all_mean_exceeds_reported_capacity=int(np.sum((all_result['mean_resources']>caps+1e-7)&known)),
            hours_completed_peak_exceeds_reported_capacity=int(np.sum((done_result['peak_resources']>caps+1e-7)&known)),
            maximum_all_peak_minus_capacity=float(np.nanmax(all_result['peak_resources']-caps)),
            max_conservation_error_gpu_seconds=max(all_result['conservation_error'],done_result['conservation_error']),
            queue_column_max_error_s=float(np.max(np.abs((jobs.start_time-jobs.submit_time).dt.total_seconds()-jobs.queue))),
            duration_column_max_error_s=float(np.max(np.abs((jobs.end_time-jobs.start_time).dt.total_seconds()-jobs.duration))))
        tables.append(frame);print(cluster,json.dumps(audit[cluster]),flush=True)
    pd.concat(tables,ignore_index=True).to_csv(OUT/'hourly_allocations.csv.gz',index=False,compression={'method':'gzip','mtime':0})
    report=dict(clusters=audit,method='Exact piecewise-constant allocation integral; no start/end rounding; all terminal states included.',
                limitations=['Allocated GPU time is not electrical power or useful completed work.',
                             'Observed queue time is not a measured deadline or contractual tolerance.',
                             'Failed/cancelled allocations cannot be counted as successful service.',
                             'Daily resource allocation and job allocation may refer to different capacity concepts; exceedances require reconciliation.',
                             'Six-month trace does not establish annual workload or future growth.'])
    (OUT/'audit.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':main()
