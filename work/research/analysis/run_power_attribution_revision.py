"""Factorial scheduling diagnostic with explicit dependency substitution.

Four cells: full-speed EDF C00; energy-oriented non-idling EDF C10;
grid-coordinated full-speed C01; grid-coordinated variable modes C11.
Slower processing changes execution times, so C10 is not labelled no shifting.
Each run uses a fresh process; source modules and frozen tables are unchanged.
"""
from pathlib import Path
import sys,json,argparse,hashlib,time
import numpy as np
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'work/research/analysis'))
sys.path.insert(0,str(ROOT/'work/research/models'))
import run_regional_2030_s0_s3 as regional
from energy_dispatch import energy_earliest_edf
from node_power_mapping import map_gpu_to_node


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--province',default='Jiangsu')
    ap.add_argument('--ai-share',type=float,default=.2)
    ap.add_argument('--workload',default='ft_llama_8b_dolly')
    ap.add_argument('--mapping',choices=['legacy','component'],default='component')
    ap.add_argument('--node-idle',type=float,default=.41)
    ap.add_argument('--gpu-idle',type=float,default=.1)
    ap.add_argument('--active-overhead',type=float,default=0.)
    a=ap.parse_args()
    name=f'{a.province}_ai{a.ai_share:g}_{a.workload}_{a.mapping}_I{a.node_idle:g}_g{a.gpu_idle:g}_d{a.active_overhead:g}'
    folder=ROOT/'outputs/research/revision/power_attribution/runs'/name
    if folder.exists():raise FileExistsError(folder)
    folder.mkdir(parents=True)
    source_paths=[Path(__file__).resolve(),ROOT/'work/research/models/energy_dispatch.py',ROOT/'work/research/models/node_power_mapping.py',
                  ROOT/'work/research/models/sequential_tasks.py',ROOT/'work/research/models/coupled_grid_compute.py',
                  ROOT/'work/research/models/response_cost.py',ROOT/'work/research/models/hydro_fleet.py',
                  ROOT/'work/research/analysis/run_regional_smoke_s0_s1_s2.py',ROOT/'work/research/analysis/run_regional_2030_s0_s3.py']
    input_names=json.loads((ROOT/'outputs/research/revision/hydro/paired_verification.json').read_text())['input_sha256']
    input_paths=[ROOT/p for p in input_names]+[ROOT/'outputs/research/revision/hydro/hydro_2030_by_technology.csv']
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    manifest=dict(parameters=vars(a),started_unix=time.time(),source_sha256={str(p.relative_to(ROOT)):sha(p) for p in source_paths},
                  input_sha256={str(p.relative_to(ROOT)):sha(p) for p in input_paths},
                  limitations=['Power component assumptions are not measured calibration.',
                               'Other original service, NOAI, representative-week and reservoir assumptions remain.',
                               'EDF baseline has full workload foresight; no grid price signal.',
                               'Four cells compare operational policies, not a causal claim of unchanged execution timing.'])
    # Archive the exact implementation as text for future audits after code evolves.
    (folder/'implementation_snapshot.json').write_text(json.dumps({str(p.relative_to(ROOT)):p.read_text() for p in source_paths},indent=2)+'\n')
    (folder/'run_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    original_modes=regional.base.dvfs_modes
    original_schedule=regional.schedule
    q,gpu,cfg=original_modes(a.workload)
    if a.mapping=='component':node,power_meta=map_gpu_to_node(gpu,a.node_idle,a.gpu_idle,a.active_overhead)
    else:node=gpu.copy();power_meta=dict(evidence='historical direct GPU-to-node ratio for comparison; physically uncalibrated')
    # The regional legacy minimum-mode filter must not silently alter this family.
    if a.mapping=='component' and np.any(node<=a.node_idle+.02):
        raise ValueError('This component setting reaches the legacy filter; requires explicit model extension')
    baseline_audits=[]
    def schedule_adapter(jobs,rates,powers,horizon,idle,**kwargs):
        if kwargs.get('service_cost_per_work') is not None:
            result=energy_earliest_edf(jobs,rates,powers,horizon,idle)
            if result['feasible']:baseline_audits.append(result['baseline_audit'])
            return result
        return original_schedule(jobs,rates,powers,horizon,idle,**kwargs)
    regional.schedule=schedule_adapter
    results={}
    try:
        for family in ['full_speed','all_modes']:
            rates=np.array([1.]) if family=='full_speed' else q
            powers=np.array([1.]) if family=='full_speed' else node
            regional.base.dvfs_modes=lambda config=a.workload:(rates.copy(),powers.copy(),cfg)
            results[family]=regional.run(a.province,a.ai_share,idle_frac=a.node_idle,export=False,
                hydro_treatment='split_pumped_storage',phs_duration_h=8.,phs_roundtrip_efficiency=.75,results_dir=folder/family)
    finally:
        regional.base.dvfs_modes=original_modes;regional.schedule=original_schedule
    full=results['full_speed']['results'];modes=results['all_modes']['results']
    if not all(v['feasible'] for family in results.values() for v in family['results'].values()):
        raise AssertionError('At least one scenario infeasible; retain output as failure')
    for case in ['NOAI','S0']:
        if not np.isclose(full[case]['total_cost'],modes[case]['total_cost'],atol=1e-5,rtol=1e-10):
            raise AssertionError(('factorial baseline mismatch',case))
    if not np.isclose(full['S0e']['total_cost'],full['S0']['total_cost'],atol=1.,rtol=1e-9):
        raise AssertionError('Full-speed lexicographic baseline differs from work-conserving EDF')
    base=full['NOAI']['total_cost']
    C00=full['S0']['total_cost']-base;C01=full['S2']['total_cost']-base
    C10=modes['S0e']['total_cost']-base;C11=modes['S2']['total_cost']-base
    interaction=C10+C01-C00-C11
    mode_first=C00-C10;mode_last=C01-C11;timing_first=C00-C01;timing_last=C10-C11
    total=C00-C11
    summary=dict(parameters=vars(a),power_mapping=power_meta,
                 mapped_modes=[dict(throughput=float(x),gpu_power_ratio=float(y),node_power_ratio=float(z)) for x,y,z in zip(q,gpu,node)],
                 cells=dict(C00=C00,C10=C10,C01=C01,C11=C11),
                 total_saving=total,total_reduction_pct=100*total/C00,
                 energy_policy_first_value=mode_first,mode_added_after_grid_value=mode_last,
                 grid_coordination_at_full_speed_value=timing_first,grid_coordination_after_energy_policy_value=timing_last,
                 interaction_saving=interaction,mode_shapley_value=(mode_first+mode_last)/2,
                 grid_shapley_value=(timing_first+timing_last)/2,
                 original_order_mode_share_pct=100*mode_first/total,
                 symmetric_mode_share_pct=100*(mode_first+mode_last)/2/total,
                 baseline_audits=baseline_audits,
                 conditional_interpretation='Shapley allocation over the specified policy matrix; not an invariant physical decomposition',
                 finished_unix=time.time())
    if abs(summary['mode_shapley_value']+summary['grid_shapley_value']-total)>1e-5:
        raise AssertionError('Decomposition does not conserve total saving')
    (folder/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    (folder/'complete.json').write_text(json.dumps(dict(all_scenarios_feasible=True,cases=14),indent=2)+'\n')
    print(json.dumps({k:v for k,v in summary.items() if k not in ['baseline_audits','mapped_modes']},indent=2))


if __name__=='__main__':main()
