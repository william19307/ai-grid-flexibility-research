"""Recompute paired metrics and audit stored dispatch diagnostics independently.

The source inputs inventory is collected after these runs, explicitly labelled;
the individual run manifests separately hold pre-run implementation hashes.
"""
from pathlib import Path
import csv,json,hashlib,math
ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'outputs/research/revision/hydro'


def main():
    rows=[];checks=[];max_old_difference=0.;max_storage_error=0.
    for folder in sorted((OUT/'runs').iterdir()):
        if not folder.is_dir():continue
        complete=json.loads((folder/'complete.json').read_text())
        assert complete['all_feasible'],folder
        manifest=json.loads((folder/'run_manifest.json').read_text())
        for name,digest in manifest['sha256'].items():
            assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest,(folder,name,'source changed since run')
        files=list(folder.glob('regional_2030_*.json'));assert len(files)==1
        doc=json.loads(files[0].read_text());m=doc['meta'];r=doc['results']
        base=r['NOAI']['total_cost'];inc=lambda case:r[case]['total_cost']-base
        total_gain=inc('S0')-inc('S2');mode_gain=inc('S0')-inc('S0e');timing_gain=inc('S0e')-inc('S2')
        assert abs(total_gain-mode_gain-timing_gain)<1e-6
        for case,v in r.items():
            assert v['unserved_mwh']<1e-6,(folder,case)
            for name,p in v['pumped_storage_audit'].items():
                eta=m['hydro_revision']['roundtrip_efficiency']
                err=abs(p['discharge_mwh']-eta*p['charge_mwh'])
                assert err<1e-5,(folder,case,name,err)
                max_storage_error=max(max_storage_error,err,p['max_transition_error_mwh'],p['max_cyclic_error_mwh'])
        if m['hydro_revision']['treatment']=='legacy':
            frozen=ROOT/'outputs/research/tables'/files[0].name
            old=json.loads(frozen.read_text())['results']
            for case in r:
                for key in ['total_cost','emissions_t','ai_mwh','new_batt_mw']:
                    difference=abs(r[case][key]-old[case][key]);max_old_difference=max(max_old_difference,difference)
                    assert math.isclose(r[case][key],old[case][key],rel_tol=1e-9,abs_tol=1e-5),(folder,case,key)
        row=dict(run=folder.name,province=m['province'],ai_share=m['assumptions']['ai_share_of_peak'],
                 exchange=m['exchange'],treatment=m['hydro_revision']['treatment'],
                 assumed_duration_h=m['hydro_revision']['ac_deliverable_duration_h'],
                 assumed_roundtrip_efficiency=m['hydro_revision']['roundtrip_efficiency'],
                 incremental_cost_S0_eur_per_week=inc('S0'),incremental_cost_S0e_eur_per_week=inc('S0e'),incremental_cost_S2_eur_per_week=inc('S2'),
                 cost_reduction_pct=100*total_gain/inc('S0'),conditional_mode_share_pct=100*mode_gain/total_gain,
                 residual_cost_gap_pct=100*timing_gain/inc('S2'),
                 new_gas_S0_MW=r['S0']['new_mw']['ocgt'],new_gas_S0e_MW=r['S0e']['new_mw']['ocgt'],new_gas_S2_MW=r['S2']['new_mw']['ocgt'],
                 max_simultaneous_storage_slots=max([p['simultaneous_slots'] for v in r.values() for p in v['pumped_storage_audit'].values()] or [0]))
        rows.append(row);checks.append(folder.name)
    with (OUT/'paired_results.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
    # Verify full national selected-vintage hydro totals, including all neighbours.
    from hydro_fleet import split_hydro
    national=[];unresolved=[]
    with (OUT/'hydro_2030_by_technology.csv').open() as f:
        classified=list(csv.DictReader(f))
    with (ROOT/'outputs/research/tables/gem_fleet_all_provinces_2020_2030.csv').open() as f:
        for r in csv.DictReader(f):
            if r['type']=='hydropower':
                total=sum(float(x['capacity_mw']) for x in classified if x['province']==r['province'].replace(' ',''))
                assert math.isclose(total,float(r['mw_2030']),abs_tol=1e-6),(r,total)
                national.append(r['province'])
                try:split_hydro(r['province'],float(r['mw_2030']))
                except ValueError as error:unresolved.append(str(error))
    inputs=['work/research/prepared/load_2020_annual_anchored_hourly_shape_UNVALIDATED.npz',
            'work/research/prepared/archive_2020_source_inputs_NOT_calibrated.npz',
            'work/research/prepared/helios_completed_gpu_jobs_sample.csv.gz',
            'work/research/prepared/HVDC_source_list_rebuilt_UNVERIFIED_GW.csv',
            'work/research/prepared/HVAC_source_list_rebuilt_UNVERIFIED_GW.csv',
            'outputs/research/tables/dvfs_measured_and_derived.csv',
            'outputs/research/tables/gem_fleet_three_provinces_2020_2030.csv',
            'outputs/research/tables/gem_fleet_all_provinces_2020_2030.csv',
            'work/research/sources/zenodo_13987282/selected/data/load/Province_Load_2020_2060.csv',
            'work/research/sources/zenodo_13987282/selected/data/costs/costs_2030.csv',
            'work/research/sources/zenodo_13987282/selected/data/existing_infrastructure/China_current_capacity.csv',
            'work/research/sources/zenodo_13987282/selected/data/hydro/dams_large.csv']
    report=dict(completed_configurations=len(rows),completed_scenario_solves=len(rows)*7,
                configurations=checks,national_capacity_reconciled_provinces=national,
                unresolved_national_technology_splits=unresolved,
                max_legacy_numeric_difference=max_old_difference,max_storage_conservation_error_mwh=max_storage_error,
                input_hash_collection='post-run inventory; do not represent as a pre-run snapshot',
                input_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in inputs},
                limitations=['Paired diagnostic retains original power mapping, deadlines, NOAI commitment and representative weeks.',
                             'Non-pumped reservoir hydrology remains uncalibrated.',
                             'Duration and efficiency are assumptions; no empirical capacity claim.',
                             'Scenario EUE=0 is not annual reliability validation.'])
    (OUT/'paired_verification.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ['input_sha256','configurations']},indent=2))


if __name__=='__main__':
    import sys
    sys.path.insert(0,str(ROOT/'work/research/models'))
    main()
