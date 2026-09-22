"""Isolated counterfactual check with archived source and actual coal constraints."""
from pathlib import Path
import sys,json,argparse,hashlib,time
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'work/research/analysis'));sys.path.insert(0,str(ROOT/'work/research/models'))
import run_regional_2030_s0_s3 as regional
from node_power_mapping import map_gpu_to_node
from energy_dispatch import energy_earliest_edf
from counterfactual_coal import coal_boundary


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--province',required=True);parser.add_argument('--ai-share',type=float,required=True)
    parser.add_argument('--policy',choices=['legacy','independent_reference','dispatch_relaxation'],required=True)
    args=parser.parse_args();name=f'{args.province}_ai{args.ai_share:g}_{args.policy}'
    out=ROOT/'outputs/research/revision/counterfactual/runs'/name
    if out.exists():raise FileExistsError(out)
    out.mkdir(parents=True)
    predecessor=ROOT/'outputs/research/revision/power_attribution/runs/Jiangsu_ai0.2_ft_llama_8b_dolly_component_I0.41_g0.1_d0/run_manifest.json'
    prior=json.loads(predecessor.read_text())
    sources=[p for p in prior['source_sha256'] if not p.endswith('run_power_attribution_revision.py')]
    sources += [str(Path(__file__).resolve().relative_to(ROOT)),'work/research/models/counterfactual_coal.py']
    digest=lambda p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
    manifest=dict(parameters=vars(args),started_unix=time.time(),source_sha256={p:digest(p) for p in sources},
                  input_sha256={p:digest(p) for p in prior['input_sha256']},
                  limitations=['Original job guards, uncalibrated node components and representative weeks retained.',
                               'Independent reference fixes only NOAI; AI cases retain rigid-AI commitment heuristic.',
                               'Dispatch relaxation has no unit startup, ramps, minimum times or forced outages.'])
    (out/'run_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (out/'implementation_snapshot.json').write_text(json.dumps({p:(ROOT/p).read_text() for p in sources},indent=2)+'\n')
    modes0=regional.base.dvfs_modes;schedule0=regional.schedule;solve0=regional.solve
    q,gpu,config=modes0('ft_llama_8b_dolly');node,power_meta=map_gpu_to_node(gpu,.41,.1,0.)
    regional.base.dvfs_modes=lambda config='ft_llama_8b_dolly':(q.copy(),node.copy(),'ft_llama_8b_dolly')
    baseline_audits=[];coal_audits=[]
    def schedule_adapter(jobs,rates,powers,horizon,idle,**kwargs):
        if kwargs.get('service_cost_per_work') is not None:
            result=energy_earliest_edf(jobs,rates,powers,horizon,idle)
            if result['feasible']:baseline_audits.append(result['baseline_audit'])
            return result
        return schedule0(jobs,rates,powers,horizon,idle,**kwargs)
    def solve_adapter(nodes,scenarios,generators,lines,storage,pools,**kwargs):
        revised,audit=coal_boundary(generators,scenarios,args.province,args.policy,bool(pools))
        coal_audits.append(audit)
        return solve0(nodes,scenarios,revised,lines,storage,pools,**kwargs)
    regional.schedule=schedule_adapter;regional.solve=solve_adapter
    try:
        result=regional.run(args.province,args.ai_share,export=False,hydro_treatment='split_pumped_storage',
                            phs_duration_h=8.,phs_roundtrip_efficiency=.75,results_dir=out)
    finally:
        regional.base.dvfs_modes=modes0;regional.schedule=schedule0;regional.solve=solve0
    # Regional metadata is historical; expose the actual constraints in a named field.
    result['meta']['historical_rigid_ai_coal_heuristic_mw']=result['meta'].pop('committed_coal_mw')
    result['meta']['actual_coal_boundaries']=dict(zip(result['results'],coal_audits))
    result['meta']['counterfactual_policy']=args.policy
    assert len(coal_audits)==len(result['results'])==7
    files=list(out.glob('regional_2030_*.json'));assert len(files)==1
    files[0].write_text(json.dumps(result,indent=2)+'\n')
    assert all(r['feasible'] for r in result['results'].values())
    checks=dict(power_mapping=power_meta,baseline_audits=baseline_audits,
                all_scenarios_feasible=True,cases=7,finished_unix=time.time())
    (out/'complete.json').write_text(json.dumps(checks,indent=2)+'\n')


if __name__=='__main__':main()
