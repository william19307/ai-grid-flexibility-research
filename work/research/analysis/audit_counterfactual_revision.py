"""Check reference invariance across AI scales and paired AI-side equality."""
from pathlib import Path
import csv,json,hashlib,math
ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'outputs/research/revision/counterfactual'
def near(a,b):
    assert math.isfinite(a) and math.isfinite(b)
    assert math.isclose(a,b,rel_tol=1e-10,abs_tol=1e-5),(a,b)
def main():
    processes=json.loads((OUT/'sweep_process_results.json').read_text())
    assert len(processes)==27 and not any(p['exit_code'] for p in processes)
    docs={};rows=[];max_storage=0.
    for p in processes:
        folder=OUT/'runs'/p['name'];manifest=json.loads((folder/'run_manifest.json').read_text())
        snapshot=json.loads((folder/'implementation_snapshot.json').read_text())
        assert json.loads((folder/'complete.json').read_text())['all_scenarios_feasible']
        for path,digest in manifest['source_sha256'].items():
            assert hashlib.sha256(snapshot[path].encode()).hexdigest()==digest
        for path,digest in manifest['input_sha256'].items():assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==digest
        files=list(folder.glob('regional_2030_*.json'));assert len(files)==1
        d=json.loads(files[0].read_text());r=d['results'];m=d['meta'];a=manifest['parameters']
        key=(a['province'],a['ai_share'],a['policy']);docs[key]=d
        assert m['counterfactual_policy']==a['policy'] and len(r)==7
        for case,v in r.items():
            assert v['feasible'] and v['unserved_mwh']<1e-6
            boundary=m['actual_coal_boundaries'][case]
            assert boundary['has_compute']==(case!='NOAI')
            if a['policy']=='legacy' or (a['policy']=='independent_reference' and case!='NOAI'):
                assert boundary['coal_upper_mw']==m['historical_rigid_ai_coal_heuristic_mw']
                near(boundary['minimum_output_fraction'],.4)
            elif a['policy']=='dispatch_relaxation':
                assert all(x==m['fleet_2030_gem']['coal'] for x in boundary['coal_upper_mw'].values())
                near(boundary['minimum_output_fraction'],0.)
            for storage in v['pumped_storage_audit'].values():
                error=abs(storage['discharge_mwh']-.75*storage['charge_mwh']);assert error<1e-5
                max_storage=max(max_storage,error,storage['max_transition_error_mwh'],storage['max_cyclic_error_mwh'])
        base=r['NOAI']['total_cost'];rigid=r['S0']['total_cost']-base;flex=r['S2']['total_cost']-base
        rows.append(dict(run=p['name'],province=a['province'],ai_share=a['ai_share'],policy=a['policy'],
                         noai_cost_eur_per_week=base,rigid_incremental_eur_per_week=rigid,flex_incremental_eur_per_week=flex,
                         total_saving_eur_per_week=rigid-flex,cost_reduction_pct=100*(rigid-flex)/rigid,
                         mode_first_share_pct=100*(r['S0']['total_cost']-r['S0e']['total_cost'])/(rigid-flex),
                         new_gas_S0_MW=r['S0']['new_mw']['ocgt'],new_gas_S2_MW=r['S2']['new_mw']['ocgt']))
    corrected_drift={};legacy_drift={}
    for province in ['Gansu','Guizhou','Jiangsu']:
        legacy_drift[province]=max(docs[(province,s,'legacy')]['results']['NOAI']['total_cost'] for s in [.01,.1,.2])-min(docs[(province,s,'legacy')]['results']['NOAI']['total_cost'] for s in [.01,.1,.2])
        for policy in ['independent_reference','dispatch_relaxation']:
            reference=docs[(province,.01,policy)]
            costs=[]
            for share in [.01,.1,.2]:
                d=docs[(province,share,policy)];costs.append(d['results']['NOAI']['total_cost'])
                assert d['meta']['actual_coal_boundaries']['NOAI']['coal_upper_mw']==reference['meta']['actual_coal_boundaries']['NOAI']['coal_upper_mw']
                for key in ['total_cost','emissions_t','new_batt_mw','new_batt_mwh','ai_mwh']:
                    near(d['results']['NOAI'][key],reference['results']['NOAI'][key])
                if policy=='independent_reference':
                    old=docs[(province,share,'legacy')]
                    for case in ['S0','S0e','S1','S2','S1rt','S3']:
                        for key in ['total_cost','emissions_t','new_batt_mw','new_batt_mwh','ai_mwh']:near(d['results'][case][key],old['results'][case][key])
            corrected_drift[f'{province}/{policy}']=max(costs)-min(costs)
        share=.2 if province=='Jiangsu' else .1
        prior_folder=ROOT/'outputs/research/revision/power_attribution/runs'/f'{province}_ai{share:g}_ft_llama_8b_dolly_component_I0.41_g0.1_d0/all_modes'
        prior=json.loads(next(prior_folder.glob('regional_2030_*.json')).read_text())
        for case in prior['results']:
            for key in ['total_cost','emissions_t','ai_mwh']:near(prior['results'][case][key],docs[(province,share,'legacy')]['results'][case][key])
    with (OUT/'counterfactual_results.csv').open('w') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');writer.writeheader();writer.writerows(rows)
    report=dict(completed_configurations=len(rows),completed_scenario_solves=len(rows)*7,failed_configurations=[],
                legacy_noai_cost_drift_eur_per_week=legacy_drift,corrected_noai_cost_drift_eur_per_week=corrected_drift,
                ai_scenarios_unchanged_by_reference_only_correction=True,paired_predecessor_reproduced=True,
                archived_sources_and_input_hashes_verified=True,max_storage_conservation_error_mwh=max_storage,
                limitations=['Independent reference corrects NOAI dependence only; endogenous thermal commitment remains unresolved.',
                             'Dispatch relaxation is a bounding sensitivity, not calibrated thermal operation.'])
    (OUT/'counterfactual_verification.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
if __name__=='__main__':main()
