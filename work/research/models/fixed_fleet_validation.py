"""Hold investment fixed for chronological hourly annual dispatch diagnostics.

This is perfect-foresight minimum-EUE dispatch, not probabilistic LOLE, online
control or independently calibrated provincial reliability. Each supplied year
is solved in full, with the underlying model's stated cyclic storage/water bounds.
"""
from dataclasses import asdict,dataclass,replace
import copy,hashlib,json
import numpy as np
import pandas as pd
from coupled_grid_compute import solve


def fingerprint(value):
    def default(x):
        if isinstance(x,np.ndarray):return x.tolist()
        if isinstance(x,np.generic):return x.item()
        raise TypeError(type(x).__name__)
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),default=default,allow_nan=False).encode()).hexdigest()


@dataclass(frozen=True)
class FixedFleet:
    generators:tuple
    lines:tuple
    storage:tuple
    manifest:dict


def freeze_investments(planning_result,generators,lines=(),storage=()):
    """Copy planned capacities into existing stock and set every expansion bound to zero.

    The caller must bind the planning result to its actual input manifest. These
    consistency checks cannot establish that an arbitrary result came from a model.
    """
    generators=list(generators);lines=list(lines);storage=list(storage)
    if planning_result.get('feasible') is not True or planning_result.get('solver_status')!=0:
        raise ValueError('Only an accepted optimal planning solution can be frozen')
    for key in ['max_equality_residual','max_inequality_violation']:
        value=planning_result.get(key)
        if value is None or not np.isfinite(value) or not 0<=value<=1e-6:raise ValueError('Planning residual missing or unacceptable')
    groups=[('new_generator_mw',generators,'max_new_mw'),('new_line_mw',lines,'max_new_mw'),
            ('new_storage_power_mw',storage,'max_new_power_mw'),('new_storage_energy_mwh',storage,'max_new_energy_mwh')]
    for key,assets,bound in groups:
        values=planning_result.get(key,{})
        if set(values)!={a.name for a in assets}:raise ValueError(f'Planning asset mismatch: {key}')
        if len({a.name for a in assets})!=len(assets):raise ValueError('Duplicate asset names')
        for a in assets:
            x=values[a.name]
            if isinstance(x,bool) or not np.isfinite(x) or x<0 or x>getattr(a,bound)+1e-6:
                raise ValueError(f'Invalid planned expansion: {a.name}')
    gs=tuple(replace(copy.deepcopy(g),existing_mw=g.existing_mw+planning_result['new_generator_mw'][g.name],
                     max_new_mw=0.,investment_cost=0.) for g in generators)
    ls=tuple(replace(copy.deepcopy(l),existing_mw=l.existing_mw+planning_result['new_line_mw'][l.name],
                     max_new_mw=0.,investment_cost=0.) for l in lines)
    bs=tuple(replace(copy.deepcopy(b),existing_power_mw=b.existing_power_mw+planning_result['new_storage_power_mw'][b.name],
                     existing_energy_mwh=b.existing_energy_mwh+planning_result['new_storage_energy_mwh'][b.name],
                     max_new_power_mw=0.,max_new_energy_mwh=0.,power_investment_cost=0.,energy_investment_cost=0.) for b in storage)
    payload=dict(generators=[asdict(x) for x in gs],lines=[asdict(x) for x in ls],storage=[asdict(x) for x in bs])
    manifest=dict(fixed_asset_sha256=fingerprint(payload),
        planning_investment_sha256=fingerprint({k:planning_result[k] for k,_,_ in groups}),
        original_input_assets_sha256=fingerprint(dict(generators=[asdict(x) for x in generators],lines=[asdict(x) for x in lines],storage=[asdict(x) for x in storage])),
        planning_investment_cost=planning_result['cost_components']['investment'],
        scope='Installed capacity only; input/output provenance and physical calibration require separate evidence.')
    return FixedFleet(gs,ls,bs,manifest)


def annual_clock(timestamps):
    clock=pd.DatetimeIndex(timestamps)
    if clock.tz is None or not len(clock):raise ValueError('An explicit timezone and complete calendar are required')
    year=clock[0].year
    expected=pd.date_range(f'{year}-01-01',f'{year+1}-01-01',freq='h',inclusive='left',tz=clock.tz)
    if not clock.equals(expected):raise ValueError('Expected one continuous complete hourly calendar year; no padding or resampling')
    return clock


def evaluate_year(fleet,nodes,scenario,timestamps,availability_by_generator,*,external_fixed_load=None,
                  reservoirs=(),commitments=(),emissions_limit_t=None,eue_tolerance_mwh=1e-6,milp_time_limit_s=120.):
    """Lexicographic minimum EUE then economic dispatch at frozen capacity.

    All generator availabilities must be explicitly supplied for the test year.
    Ordinary load can be shed; independently certified external AI load cannot.
    Returned shortage hours describe the chosen dispatch, not a LOLE estimate.
    """
    clock=annual_clock(timestamps);T=len(clock)
    if scenario.probability!=1 or set(scenario.load_mw)!=set(nodes):raise ValueError('Evaluate each explicit year with probability one')
    if any(len(x)!=T for x in scenario.load_mw.values()):raise ValueError('Load length differs from actual year')
    if not np.isfinite(eue_tolerance_mwh) or not 0<=eue_tolerance_mwh<=1e-4:raise ValueError('Invalid EUE tolerance')
    if emissions_limit_t is not None and (not np.isfinite(emissions_limit_t) or emissions_limit_t<0):raise ValueError('Invalid annual emissions limit')
    payload=dict(generators=[asdict(x) for x in fleet.generators],lines=[asdict(x) for x in fleet.lines],storage=[asdict(x) for x in fleet.storage])
    if fingerprint(payload)!=fleet.manifest['fixed_asset_sha256']:raise ValueError('Frozen assets were changed')
    if set(availability_by_generator)!={g.name for g in fleet.generators}:raise ValueError('Explicit availability required for every fixed generator')
    gs=[]
    for g in fleet.generators:
        a=np.asarray(availability_by_generator[g.name],float)
        if a.shape!=(T,) or not np.isfinite(a).all() or (a<0).any() or (a>1).any():raise ValueError('Invalid full-year availability')
        gs.append(replace(g,availability={scenario.name:a}))
    # Phase 1 removes all economic preferences while retaining physical constraints.
    minimum_g=[replace(g,marginal_cost=0.) for g in gs]
    minimum_l=[replace(l,flow_cost_per_mwh=0.) for l in fleet.lines]
    minimum_b=[replace(b,throughput_cost=0.) for b in fleet.storage]
    minimum_h=[replace(h,marginal_cost=0.,spillage_cost_per_hm3=0.) for h in reservoirs]
    minimum_c=[replace(c,startup_cost=0.,shutdown_cost=0.,no_load_cost_per_hour=0.) for c in commitments]
    maximum_eue=float(sum(np.sum(x) for x in scenario.load_mw.values()))
    first=solve(nodes,[scenario],minimum_g,minimum_l,minimum_b,expected_unserved_limit_mwh=maximum_eue,
        unserved_cost=1.,reservoirs=minimum_h,commitments=minimum_c,emissions_limit_t=emissions_limit_t,
        external_fixed_load=external_fixed_load,milp_time_limit_s=milp_time_limit_s)
    receipt=dict(year=int(clock[0].year),hours=T,clock_sha256=fingerprint([x.isoformat() for x in clock]),
        dispatch_inputs_sha256=fingerprint(dict(nodes=list(nodes),scenario=asdict(scenario),
            availability=availability_by_generator,external_fixed_load=external_fixed_load,
            reservoirs=[asdict(x) for x in reservoirs],commitments=[asdict(x) for x in commitments],
            emissions_limit_t=emissions_limit_t,eue_tolerance_mwh=eue_tolerance_mwh,milp_time_limit_s=milp_time_limit_s)),
        fleet_manifest=fleet.manifest,perfect_foresight=True,
        annual_boundary='Underlying model uses cyclic storage/reservoir constraints; initial fractions/volumes explicit. Thermal end obligations are reported.',
        scope='Deterministic fixed-fleet annual diagnostic; not stochastic LOLE or empirical reliability certification')
    if first.get('feasible') is not True:
        return dict(receipt=receipt,phase='minimum_eue',accepted=False,solver_result=first)
    minimum=float(first['expected_unserved_mwh'])
    second=solve(nodes,[scenario],gs,fleet.lines,fleet.storage,expected_unserved_limit_mwh=minimum+eue_tolerance_mwh,
        unserved_cost=0.,reservoirs=reservoirs,commitments=commitments,emissions_limit_t=emissions_limit_t,
        external_fixed_load=external_fixed_load,milp_time_limit_s=milp_time_limit_s)
    if second.get('feasible') is not True:
        return dict(receipt=receipt,phase='economic_dispatch',accepted=False,minimum_eue_mwh=minimum,solver_result=second)
    for key in ['new_generator_mw','new_line_mw','new_storage_power_mw','new_storage_energy_mwh']:
        if any(abs(v)>1e-8 for v in second[key].values()):raise RuntimeError('Capacity changed during fixed-fleet evaluation')
    assert second['cost_components']['investment']==0
    reported=second['scenarios'][scenario.name]
    deficit=np.sum([np.asarray(v) for v in reported['unserved'].values()],axis=0)
    if deficit.sum()>minimum+eue_tolerance_mwh+1e-6:raise RuntimeError('Economic phase violated EUE optimum')
    return dict(receipt=receipt,accepted=True,minimum_eue_mwh=minimum,reported_eue_mwh=float(deficit.sum()),
        eue_tolerance_mwh=eue_tolerance_mwh,
        shortage_hours_in_reported_dispatch=int(np.sum(deficit>1e-6)),
        maximum_shortage_mw=float(max(deficit)),capacity_reoptimized=False,
        minimum_eue_solver=dict(type=first['solver_type'],status=first['solver_status'],gap=first['mip_gap']),
        dispatch_result=second)
