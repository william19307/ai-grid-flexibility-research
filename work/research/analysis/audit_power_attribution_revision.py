"""Independent arithmetic, provenance and conservation audit of factorial outputs.

Does not import the run script, component mapping or decomposition functions.
It verifies stored implementations even if current source subsequently changes.
"""
from pathlib import Path
import csv, hashlib, json, math

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'outputs/research/revision/power_attribution'


def near(a,b):
    assert math.isfinite(a) and math.isfinite(b)
    assert math.isclose(a,b,abs_tol=1e-5,rel_tol=1e-10),(a,b)


def main():
    rows=[];failures=[];changes=set();max_storage=0.;max_nonidle=0.;max_energy_gap=0.
    process=json.loads((OUT/'sweep_process_results.json').read_text())
    assert len({row['name'] for row in process})==len(process)
    for process_row in process:
        folder=OUT/'runs'/process_row['name']
        if process_row['exit_code'] or not (folder/'complete.json').exists():
            failures.append(process_row);continue
        manifest=json.loads((folder/'run_manifest.json').read_text())
        snapshot=json.loads((folder/'implementation_snapshot.json').read_text())
        summary=json.loads((folder/'summary.json').read_text())
        assert manifest['parameters']==summary['parameters']
        for path,digest in manifest['source_sha256'].items():
            assert hashlib.sha256(snapshot[path].encode()).hexdigest()==digest,(folder,path)
            if hashlib.sha256((ROOT/path).read_bytes()).hexdigest()!=digest:changes.add(path)
        for path,digest in manifest['input_sha256'].items():
            assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==digest,(folder,path)
        docs={}
        for family in ['full_speed','all_modes']:
            files=list((folder/family).glob('regional_2030_*.json'));assert len(files)==1
            docs[family]=json.loads(files[0].read_text())
        f=docs['full_speed']['results'];m=docs['all_modes']['results'];meta=docs['all_modes']['meta']
        for doc in docs.values():
            assert doc['meta']['hydro_revision']['treatment']=='split_pumped_storage'
            near(doc['meta']['hydro_revision']['ac_deliverable_duration_h'],8.)
            assert len(doc['results'])==7
            for case,value in doc['results'].items():
                assert value['feasible'] and value['unserved_mwh']<1e-6,(folder,case)
                near(value['total_cost'],sum(value[k] for k in ['cost_investment','cost_operating','cost_service_delay','cost_unserved_penalty']))
                for audit in value['pumped_storage_audit'].values():
                    error=abs(audit['discharge_mwh']-.75*audit['charge_mwh'])
                    max_storage=max(max_storage,error,audit['max_transition_error_mwh'],audit['max_cyclic_error_mwh'])
                    assert error<1e-5
                    assert audit['max_transition_error_mwh']<1e-5 and audit['max_cyclic_error_mwh']<1e-5
        for case in ['NOAI','S0']:
            near(f[case]['total_cost'],m[case]['total_cost'])
        # Both families must use identical work and any historical deadline guards.
        assert docs['full_speed']['meta']['ai_work_pool_hours']==meta['ai_work_pool_hours']
        for season,jobs in meta['job_meta'].items():
            for key in ['extended','dropped_share','n','realised_utilisation','guard_iterations']:
                near(jobs[key],docs['full_speed']['meta']['job_meta'][season][key])
        C00=f['S0']['total_cost']-f['NOAI']['total_cost']
        C01=f['S2']['total_cost']-f['NOAI']['total_cost']
        C10=m['S0e']['total_cost']-m['NOAI']['total_cost']
        C11=m['S2']['total_cost']-m['NOAI']['total_cost']
        for key,value in zip(['C00','C10','C01','C11'],[C00,C10,C01,C11]):near(summary['cells'][key],value)
        total=C00-C11;mode=.5*((C00-C10)+(C01-C11));grid=.5*((C00-C01)+(C10-C11))
        near(total,mode+grid);near(summary['total_saving'],total)
        near(summary['mode_shapley_value'],mode);near(summary['grid_shapley_value'],grid)
        near(summary['interaction_saving'],C10+C01-C00-C11)
        near(summary['total_reduction_pct'],100*total/C00)
        near(summary['symmetric_mode_share_pct'],100*mode/total)
        near(summary['original_order_mode_share_pct'],100*(C00-C10)/total)
        p=summary['parameters']
        if p['mapping']=='component':
            I,g,d=p['node_idle'],p['gpu_idle'],p['active_overhead']
            alpha=(1-I-d)/(1-g);active=1-alpha;idle=active-d
            assert 0<alpha<=1 and idle>=-1e-12
            near(alpha*g+idle,I);near(alpha+active,1.)
            for curve in summary['mapped_modes']:
                near(curve['node_power_ratio'],alpha*curve['gpu_power_ratio']+active)
            assert meta['assumptions']['modes_kept']==len(summary['mapped_modes'])
        assert len(summary['baseline_audits'])==8
        for baseline in summary['baseline_audits']:
            max_nonidle=max(max_nonidle,baseline['max_idle_fraction_with_released_unfinished_work'])
            max_energy_gap=max(max_energy_gap,baseline['energy_excess_normalized'])
            assert baseline['max_overdue_work']<1e-5 and baseline['max_remaining_work']<1e-5
            assert baseline['max_pool_fraction']<1+1e-6 and baseline['energy_excess_normalized']<2e-7
        row=dict(run=folder.name,**p,C00=C00,C10=C10,C01=C01,C11=C11,
                 total_reduction_pct=100*total/C00,mode_first_share_pct=100*(C00-C10)/total,
                 symmetric_mode_share_pct=100*mode/total,interaction_eur_per_week=C10+C01-C00-C11,
                 grid_first_share_pct=100*(C00-C01)/total,
                 new_gas_S0_MW=m['S0']['new_mw']['ocgt'],new_gas_S0e_MW=m['S0e']['new_mw']['ocgt'],new_gas_S2_MW=m['S2']['new_mw']['ocgt'],
                 ai_mwh_S0=m['S0']['ai_mwh'],ai_mwh_S0e=m['S0e']['ai_mwh'],ai_mwh_S2=m['S2']['ai_mwh'],
                 modes_kept=meta['assumptions']['modes_kept'])
        rows.append(row)
    assert max_nonidle<1e-5
    # At fixed province and idle power, C00/C01 cannot depend on the DVFS curve.
    reference={}
    for row in rows:
        key=(row['province'],row['ai_share'],row['node_idle'])
        if key in reference:
            for cell in ['C00','C01']:near(reference[key][cell],row[cell])
        else:reference[key]=row
    with (OUT/'factorial_results.csv').open('w') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');writer.writeheader();writer.writerows(rows)
    report=dict(planned_configurations=len(process),completed_configurations=len(rows),failed_configurations=failures,
                completed_scenario_solves=len(rows)*14,archived_implementations_verified=True,
                current_source_changed_since_runs=sorted(changes),current_inputs_match=True,
                max_storage_conservation_error_mwh=max_storage,max_idle_fraction_with_unfinished_work=max_nonidle,
                max_lexicographic_energy_gap_normalized=max_energy_gap,
                evidence='conditional policy diagnostics, not whole-node measured calibration or annual reliability validation')
    (OUT/'factorial_verification.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
    if failures:raise SystemExit(1)


if __name__=='__main__':main()
