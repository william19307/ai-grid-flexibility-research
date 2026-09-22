"""Power-boundary/mandatory-load checks plus one certified real-trace integration.

The electrical examples use analytic artificial generators and are not provincial
results. The real schedules are not reoptimized or replaced by fluid task inputs.
"""
from pathlib import Path
import hashlib,json,sys,tempfile,shutil
import numpy as np
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'work/research/models'))
from verified_power_bridge import convert_power,load_verified_case,CELLS
from coupled_grid_compute import Scenario,Generator,solve
from thermal_commitment import ThermalCommitment
OUT=ROOT/'outputs/research/revision/power_bridge';OUT.mkdir(parents=True,exist_ok=True)
checks=[]
# Independent endpoint calculation: fully idle and fully active pools.
bundle=dict(capacity_gpus=np.array([10.,20.,30.]),power_gpu_units={c:np.array([1.,20.,3.]) for c in CELLS},case={'start':'2020-04-06'},proof={})
b=convert_power(bundle,replicas=2,full_active_kw_per_gpu=1,node_idle_ratio=.41)
expected=np.array([10*.41,20,30*.41])*2/1000
for c in CELLS:assert np.allclose(b['power_mw'][c],expected,atol=1e-12)
checks.append('idle_active_endpoints_and_variable_capacity')
# GPU-only identity; constant non-GPU overhead scales the incremental saving.
bundle['power_gpu_units']['C11']=np.array([1.,11.,3.])
b=convert_power(bundle,replicas=1,full_active_kw_per_gpu=1,node_idle_ratio=.1)
assert np.allclose(b['power_mw']['C11'],bundle['power_gpu_units']['C11']/1000)
b2=convert_power(bundle,replicas=3,full_active_kw_per_gpu=2,node_idle_ratio=.41)
assert np.allclose((b2['power_mw']['C00']-b2['power_mw']['C11']),6*(.59/.9)*(b['power_mw']['C00']-b['power_mw']['C11']))
checks+=['GPU_identity','node_boundary_savings_and_replica_scaling']
assert len(b2['times'])==3 and str(b2['times'][0])=='2020-04-06 00:00:00+08:00'
checks.append('explicit_unchanged_trace_clock')
for kw in [dict(replicas=.5),dict(replicas=True),dict(full_active_kw_per_gpu=0),dict(node_idle_ratio=.05),dict(gpu_idle_ratio=.2),dict(time_zone_assumption='UTC')]:
    args=dict(replicas=1,full_active_kw_per_gpu=1,node_idle_ratio=.41);args.update(kw)
    try:convert_power(bundle,**args)
    except ValueError:pass
    else:raise AssertionError(kw)
checks.append('invalid_boundary_and_replication_inputs_rejected')
for invalid in [dict(bundle,capacity_gpus=np.array([10.,float('nan'),30.])),dict(bundle,power_gpu_units={c:np.array([1.,21.,3.]) for c in CELLS})]:
    try:convert_power(invalid,replicas=1,full_active_kw_per_gpu=1,node_idle_ratio=.41)
    except ValueError:pass
    else:raise AssertionError('Invalid capacity/power accepted')
checks.append('invalid_resource_capacity_and_power_bound_rejected')
# A zero base load gives zero non-AI shedding, even if the allowed EENS is large.
s=[Scenario('s',1,{'A':[0.,0.]})]
r=solve(['A'],s,[],external_fixed_load={'s':{'A':[1,1]}},expected_unserved_limit_mwh=100)
assert r['proven_infeasible'];checks.append('external_AI_cannot_be_shed_as_nonAI')
# MW to MWh and shared capacity, independent of fake task reconstruction.
r=solve(['A'],s,[Generator('g','A',0,3,10,4)],dt=.5,external_fixed_load={'s':{'A':[1,2]}})
assert abs(r['total_cost']-(2*10+1.5*4))<1e-8 and r['new_generator_mw']['g']==2
assert r['scenarios']['s']['task_allocations']=={}
checks.append('mandatory_power_capacity_energy_and_no_surrogate_tasks')
for bad in [{'other':{'A':[1,1]}},{'s':{'B':[1,1]}},{'s':{'A':[1]}},{'s':{'A':[1,-1]}},{'s':{'A':[float('nan'),1]}}]:
    try:solve(['A'],s,[],external_fixed_load=bad)
    except ValueError:pass
    else:raise AssertionError(bad)
checks.append('missing_misaligned_nonfinite_external_input_rejected')
# Use an already independently certified case, preserving all 192 hours.
case='Earth_ft_llama_8b_dolly_6_Jiangsu'
real=load_verified_case(ROOT,case)
# Mutations are confined to copied fixture files; raw datasets are read-only symlinks.
with tempfile.TemporaryDirectory(prefix='power_bridge_proof_') as td:
    fixture=Path(td);(fixture/'work').symlink_to(ROOT/'work',target_is_directory=True)
    po=fixture/'outputs/research/revision/policy';po.mkdir(parents=True)
    (fixture/'outputs/research/tables').symlink_to(ROOT/'outputs/research/tables',target_is_directory=True)
    original=ROOT/'outputs/research/revision/policy'
    shutil.copy2(original/'manifest.json',po/'manifest.json')
    (po/'case_verification').mkdir();shutil.copy2(original/'case_verification'/f'{case}.json',po/'case_verification'/f'{case}.json')
    shutil.copytree(original/'runs'/case,po/'runs'/case)
    load_verified_case(fixture,case)
    for file,expected_message in [('verified_hourly_profiles.csv.gz','Changed certified power trajectory'),('C11.csv.gz','Certificate does not match')]:
        target=po/'runs'/case/file;before=target.read_bytes();target.write_bytes(before+b'corruption')
        try:load_verified_case(fixture,case)
        except ValueError as ex:assert expected_message in str(ex),ex
        else:raise AssertionError('Accepted modified schedule or profile')
        finally:target.write_bytes(before)
        checks.append('reject_modified_'+file)
b=convert_power(real,replicas=1,full_active_kw_per_gpu=.5,node_idle_ratio=.41)
assert len(b['times'])==192 and str(b['times'][-1])=='2020-04-13 23:00:00+08:00'
results={};maximum_balance=0
for cell in CELLS:
    power=b['power_mw'][cell]
    gen=Generator('analytic_thermal','A',float(np.max(power)*1.01),0,0,5,min_output_fraction=0)
    control=ThermalCommitment('analytic_thermal',startup_cost=10)
    r=solve(['A'],[Scenario('trace',1,{'A':np.zeros(192)})],[gen],commitments=[control],
            external_fixed_load={'trace':{'A':power}})
    assert r['feasible'],r
    expected=10+5*float(power.sum());assert abs(r['total_cost']-expected)<1e-6
    rr=r['scenarios']['trace'];err=float(np.max(abs(np.array(rr['generation']['analytic_thermal'])-power)))
    maximum_balance=max(maximum_balance,err);assert err<1e-8
    assert sum(rr['unit_commitment']['analytic_thermal']['startup'])==1
    assert rr['task_allocations']=={} and rr['external_fixed_load_mw']['A']==power.tolist()
    results[cell]=r
checks.append('four_certified_real_trajectories_joint_MILP_analytic_cost')
files=[Path(__file__),ROOT/'work/research/models/verified_power_bridge.py',ROOT/'work/research/models/node_power_mapping.py',ROOT/'work/research/models/coupled_grid_compute.py',ROOT/'work/research/models/thermal_commitment.py']
report=dict(checks=checks,number_of_checks=len(checks),certified_case=case,upstream_proof=real['proof'],
    assumptions=b['assumptions'],maximum_independent_power_balance_error_mw=maximum_balance,
    evidence='Bridge and analytic integration validation, not measured facility power or provincial grid benefits',
    source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files})
(OUT/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
(OUT/'analytic_real_trace_results.json').write_text(json.dumps(results,indent=2)+'\n')
(OUT/'source_snapshot.json').write_text(json.dumps({str(p.relative_to(ROOT)):p.read_text() for p in files},indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in ['checks','source_sha256','assumptions','upstream_proof']},indent=2))
