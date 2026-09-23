"""Admit certified gang schedules as mandatory electrical trajectories.

This is an explicitly assumed power conversion, not a calibration. The entire
192-hour verified trace (including all fixed background and GPU idle) is retained.
Identical independent cluster replicas are synchronous by construction.
"""
from pathlib import Path
import hashlib,json
import numpy as np,pandas as pd
from node_power_mapping import map_gpu_to_node
from reviewed_tariff_version import admit_inputs
CELLS=('C00','C10','C01','C11')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_verified_case(root, name, *, allow_reviewed_tariff_version=False):
    root=Path(root);out=root/'outputs/research/revision/policy';folder=out/'runs'/name
    spec=json.loads((out/'manifest.json').read_text())
    declared={'_'.join(str(c[k]) for k in ['cluster','workload','slack','tariff']) for c in spec['cases']}
    if name not in declared:raise ValueError('Case was not in the frozen manifest')
    audit=json.loads((out/'case_verification'/f'{name}.json').read_text())
    if audit['row']['run']!=name:raise ValueError('Wrong case certificate')
    replacements=admit_inputs(root,spec['input_sha256'],allow_reviewed_tariff_version=allow_reviewed_tariff_version)
    verifier=root/'work/research/analysis/verify_gang_policy_revision.py'
    inputs=[folder/'summary.json']+[folder/f'{cell}.csv.gz' for cell in CELLS]
    key=hashlib.sha256((sha(verifier)+sha(out/'manifest.json')+''.join(sha(p) for p in inputs)).encode()).hexdigest()
    if key!=audit['input_key']:raise ValueError('Certificate does not match current verifier and schedules')
    profile=folder/'verified_hourly_profiles.csv.gz'
    if sha(profile)!=audit['profile_sha256']:raise ValueError('Changed certified power trajectory')
    d=pd.read_csv(profile)
    if not np.array_equal(d.hour,np.arange(192)):raise ValueError('Incomplete or reordered hourly horizon')
    power=d[list(CELLS)].to_numpy(float)
    if not np.isfinite(power).all() or (power<0).any():raise ValueError('Invalid certified powers')
    case=audit['row'];start=pd.Timestamp(case['start'])
    source=root/'work/research/sources/helios_sensetime/data'/case['cluster']/'cluster_gpu_number.csv'
    cap=pd.read_csv(source,parse_dates=['date']).set_index('date')['total']
    capacity=cap.reindex(start+pd.to_timedelta(np.arange(192)//24,unit='D')).to_numpy(float)
    if not np.isfinite(capacity).all() or (capacity<=0).any():raise ValueError('Missing or nonpositive hourly capacity')
    if (power>capacity[:,None]+1e-7).any():raise ValueError('Power exceeds full-speed homogeneous capacity')
    proof=dict(manifest_sha256=sha(out/'manifest.json'),case_certificate_sha256=sha(out/'case_verification'/f'{name}.json'),
               profile_sha256=sha(profile),verifier_sha256=sha(verifier),upstream_inputs_verified=len(spec['input_sha256']))
    if replacements:proof['reviewed_source_versions']=replacements
    return dict(case=case,capacity_gpus=capacity,power_gpu_units={c:d[c].to_numpy(float) for c in CELLS},proof=proof)


def convert_power(bundle, *, replicas, full_active_kw_per_gpu, node_idle_ratio,
                  gpu_idle_ratio=.1, time_zone_assumption='Asia/Shanghai'):
    if isinstance(replicas,bool) or not isinstance(replicas,(int,np.integer)) or replicas<1:
        raise ValueError('Replicas must be a positive integer')
    if not np.isfinite(full_active_kw_per_gpu) or full_active_kw_per_gpu<=0:
        raise ValueError('Explicit positive full active power assumption required')
    if gpu_idle_ratio!=.1:raise ValueError('Certified GPU trajectory uses idle ratio 0.1')
    if time_zone_assumption!='Asia/Shanghai':raise ValueError('Only explicit unchanged trace-clock alignment is implemented')
    _,mapping=map_gpu_to_node([gpu_idle_ratio,1.],node_idle_ratio,gpu_idle_ratio,0.)
    capacity=np.asarray(bundle['capacity_gpus'],float);a=mapping['gpu_share_of_full_node_power']
    if capacity.ndim!=1 or not len(capacity) or not np.isfinite(capacity).all() or (capacity<=0).any():raise ValueError('Invalid resource capacity')
    scale=replicas*full_active_kw_per_gpu/1000
    traces={}
    for cell in CELLS:
        gpu=np.asarray(bundle['power_gpu_units'][cell],float)
        if gpu.shape!=capacity.shape or not np.isfinite(gpu).all() or np.any(gpu<gpu_idle_ratio*capacity-1e-7) or np.any(gpu>capacity+1e-7):
            raise ValueError('Invalid GPU trace or missing idle/background power')
        traces[cell]=scale*(node_idle_ratio*capacity+a*(gpu-gpu_idle_ratio*capacity))
    start=pd.Timestamp(bundle['case']['start']).tz_localize(time_zone_assumption)
    return dict(power_mw=traces,full_active_capacity_mw=scale*capacity,
                times=pd.date_range(start,periods=len(capacity),freq='h'),proof=bundle['proof'],
                assumptions=dict(replicas=int(replicas),full_active_kw_per_gpu=full_active_kw_per_gpu,
                    node_idle_ratio=node_idle_ratio,gpu_idle_ratio=gpu_idle_ratio,non_gpu_active_overhead=0.,
                    time_zone_assumption=time_zone_assumption,mapping=mapping,
                    evidence='Assumed homogeneous power boundary and synchronous replicas; not measured facility load',
                    service_scope='Original verified gangs per independent replica; same jobs, background and 192-hour tail',
                    geography='Province pairing is a scenario, not the observed cluster location'))
