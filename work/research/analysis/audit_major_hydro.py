"""Audit archived dam, reservoir and historical inflow inputs without imputation."""
from pathlib import Path
import sys,json,hashlib,ast
import numpy as np,pandas as pd
from read_legacy_hydro_pickle import load,State
ROOT=Path(__file__).resolve().parents[3]
SRC=ROOT/'work/research/sources/zenodo_13987282/selected'
OUT=ROOT/'outputs/research/tables';PREP=ROOT/'work/research/prepared'

def values(index):
    if isinstance(index,np.ndarray):return index
    d=index.state
    if 'data' in d:return values(d['data'])
    return np.arange(d['start'],d['stop'],d['step'])

def simple_series(path):
    obj=load(path);manager=obj.state['_data'].state
    assert len(manager[0])==1 and len(manager[1])==1
    a=np.asarray(manager[1][0]);ix=values(manager[0][0]);assert len(a)==len(ix)
    return pd.Series(a,index=ix)

def simple_frame(path):
    obj=load(path);manager=obj.state['_data'].state
    assert len(manager[0])==2 and len(manager[1])==1
    cols=values(manager[0][0]);idx=values(manager[0][1]);a=np.asarray(manager[1][0])
    assert a.shape==(len(cols),len(idx)) and a.dtype.kind=='f'
    return pd.DataFrame(a.T,index=pd.DatetimeIndex(idx),columns=cols)

d=pd.read_csv(SRC/'data/hydro/dams_large.csv').set_index('Dam_names')
for name in ['total','initial','effective']:
    s=simple_series(SRC/f'data/hydro/reservoir_{name}_capacity.pickle')
    assert s.index.equals(pd.RangeIndex(len(d)))
    d[name+'_m3']=s.to_numpy()
d['capacity_MW']=d.installed_capacity_10MW*10
d['specific_water_m3_per_MWh']=d.Water_consumption_factor_avg*1000
d['initial_exceeds_effective']=d.initial_m3>d.effective_m3
d['dead_storage_subtraction_candidate_m3']=d.initial_m3-(d.total_m3-d.effective_m3)
d['dead_storage_subtraction_negative']=d.dead_storage_subtraction_candidate_m3<0
d['status']='source audit only; vintage, initial storage reference and site mapping need verification'
assert len(d)==43 and not d.index.duplicated().any()
assert np.isfinite(d[['capacity_MW','specific_water_m3_per_MWh','total_m3','initial_m3','effective_m3']]).all().all()
assert (d.capacity_MW>0).all() and (d.specific_water_m3_per_MWh>0).all()
d.to_csv(OUT/'major_hydro_dam_parameter_audit.csv')

flow=simple_frame(SRC/'data/hydro/daily_hydro_inflow_per_dam_1979_2016_m3.pickle')
energy=simple_frame(SRC/'data/hydro/daily_hydro_inflow_per_dam_1979_2016_GWh.pickle')
assert flow.columns.equals(d.index) and flow.columns.equals(energy.columns) and flow.index.equals(energy.index)
assert flow.index.equals(pd.date_range('1979-01-01','2016-12-31',freq='D'))
assert np.isfinite(flow.to_numpy()).all() and (flow.to_numpy()>=0).all()
assert np.isfinite(energy.to_numpy()).all() and (energy.to_numpy()>=0).all()
ratio=flow/energy.where(energy>0)/1e6  # implied m3/kWh; undefined at zero energy
rr=pd.DataFrame({'implied_m3_per_kWh_min':ratio.min(),'implied_m3_per_kWh_max':ratio.max(),
                 'average_factor_in_dam_csv':d.Water_consumption_factor_avg,
                 'days_exactly_100000_m3':flow.eq(100000).sum(),
                 'zero_energy_days':energy.eq(0).sum(),
                 'zero_energy_and_100000_m3_days':(energy.eq(0)&flow.eq(100000)).sum()})
rr['relative_factor_difference_vs_dam_average']=ratio.median()/d.Water_consumption_factor_avg-1
rr.to_csv(OUT/'major_hydro_volume_energy_conversion_audit.csv')
annual=flow.groupby(flow.index.year).sum();annual.index.name='hydrology_year'
annual.to_csv(OUT/'major_hydro_annual_source_volume_m3.csv')
np.savez_compressed(PREP/'major_hydro_daily_source_1979_2016_NOT_calibrated.npz',
    date_ns=flow.index.as_unit('ns').asi8,dam_names=np.asarray(flow.columns,dtype='U32'),
    volume_m3_per_day=flow.to_numpy(),source_energy_GWh_per_day=energy.to_numpy())

# Recover named cascade edges from the actual archived code rather than from an
# undocumented new map. These edges remain source-model assumptions.
script=SRC/'scripts/prepare_base_network_2020.py';tree=ast.parse(script.read_text())
lists={}
for node in ast.walk(tree):
    if isinstance(node,ast.Assign):
        for target in node.targets:
            if isinstance(target,ast.Name) and target.id in {'bus0s','bus1s'}:lists[target.id]=ast.literal_eval(node.value)
edges=[]
for a,b in zip(lists['bus0s'],lists['bus1s']):
    up=d.iloc[a];down=d.iloc[b];factor=up.specific_water_m3_per_MWh/down.specific_water_m3_per_MWh
    edges.append({'upstream':d.index[a],'downstream':d.index[b],
        'upstream_m3_per_MWh':up.specific_water_m3_per_MWh,'downstream_m3_per_MWh':down.specific_water_m3_per_MWh,
        'energy_equivalent_transfer_factor_for_equal_water':factor,'archived_efficiency2':1.,
        'status':'constant specific-water dimensional check, not a generation-bias estimate'})
e=pd.DataFrame(edges);assert len(e)==20;e.to_csv(OUT/'major_hydro_cascade_conversion_audit.csv',index=False)
# Pulse vs uniform interpolation preserves daily volume at hourly resolution;
# downsampling a pulse without volume aggregation does not preserve it generally.
day=np.arange(24,24*8,24,dtype=float);uniform=np.repeat(day/24,24)
pulse=np.zeros(24*len(day));pulse[::24]=day
assert np.isclose(uniform.sum(),day.sum()) and np.isclose(pulse.sum(),day.sum())
assert np.isclose(uniform.reshape(-1,24).sum(axis=1),day).all()
diagnostic={str(step):{'uniform_aggregate_volume':float(uniform.reshape(-1,step).sum()),
                     'pulse_decimation_times_step_volume':float(pulse[::step].sum()*step)} for step in [1,3,4,6]}

summary={'status':'source_hydro_inputs_audited_NOT_ready_as_2020_hydrology',
 'dams':len(d),'total_nameplate_MW':float(d.capacity_MW.sum()),'historical_daily_rows':len(flow),
 'hydrology_years':list(map(int,annual.index)),'time_zone_in_source':None,
 'missing_or_negative_daily_flow_values':int((~np.isfinite(flow.to_numpy())|(flow.to_numpy()<0)).sum()),
 'source_flow_values_equal_100000_m3':int(flow.eq(100000).sum().sum()),
 'source_energy_zero_values':int(energy.eq(0).sum().sum()),
 'source_energy_zero_with_positive_volume_values':int((energy.eq(0)&flow.gt(0)).sum().sum()),
 'initial_greater_than_effective_count':int(d.initial_exceeds_effective.sum()),
 'initial_greater_than_total_count':int((d.initial_m3>d.total_m3).sum()),
 'negative_after_naive_dead_storage_subtraction_count':int(d.dead_storage_subtraction_negative.sum()),
 'cascade_edges':len(e),'cascade_energy_transfer_factors_different_from_one':int((~np.isclose(e.energy_equivalent_transfer_factor_for_equal_water,1)).sum()),
 'factor_min':float(e.energy_equivalent_transfer_factor_for_equal_water.min()),'factor_max':float(e.energy_equivalent_transfer_factor_for_equal_water.max()),
 'archived_default_resolution_hours':1,'time_resolution_diagnostic_arbitrary_m3':diagnostic,
 'source_year_selected_in_archive_code':2016,'calendar_template_year_in_archive_code':2025,
 'calendar_days_selected':365,'calendar_days_in_2016':366,
 'excluded_feb29_source_volume_m3_all_dams':float(flow.loc['2016-02-29'].sum()),
 'no_2020_inflow_observations_in_this_file':True,
 'limits':['daily volumes require an explicit within-day timing assumption; midnight pulses and uniform flow have identical daily total but different feasible hourly dispatch',
 'direct decimation example is a dimensional warning; archive default is 1 hour, so no multi-hour inflation is asserted for its default run',
 'initial reservoir values cannot be used directly as active storage; subtraction of total minus effective also fails for 11 dams',
 'archive sets cyclic storage; PyPSA documentation says e_initial is ignored when e_cyclic is true, so above-range initial values do not establish archive-run infeasibility',
 'source energy-valued cascade variables require dam-specific conversion to preserve water volume; this audit does not quantify full-system output bias',
 'downstream flow could be total catchment inflow rather than incremental inflow; do not add it to routed upstream flow without source clarification',
 'Baihetan and Wudongde capacity vintages require commissioning reconciliation before 2020 modeling',
 'historical hydrology and future plant list may be a scenario reconstruction; not 43 observed operational plants throughout 1979-2016',
 'pumped storage is separate; fixed six-hour duration in source configuration is an assumption'],
 'source':'https://doi.org/10.5281/zenodo.13987282',
 'pypsa_cyclic_documentation':'https://docs.pypsa.org/stable/api/components/types/stores/',
 'full_archive_checksum_verified':False,'selected_members_verified_total':len(json.loads((SRC.parent/'selected_members_manifest.json').read_text())),
 'script_sha256':hashlib.sha256(script.read_bytes()).hexdigest()}
(OUT/'major_hydro_source_audit.json').write_text(json.dumps(summary,indent=2))
print(json.dumps({k:v for k,v in summary.items() if k not in ['limits','time_resolution_diagnostic_arbitrary_m3','hydrology_years']},indent=2))
