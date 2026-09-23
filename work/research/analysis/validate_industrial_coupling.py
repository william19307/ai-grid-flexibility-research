"""Synthetic physical/analytical tests. No site observation or provincial fit."""
from pathlib import Path
from dataclasses import replace, asdict
import copy
import json
import hashlib
import argparse
import sys
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'work/research/models'))
from coupled_grid_compute import Generator, Scenario, Line, solve
from industrial_captive import CaptiveUnit, IndustrialSite
from thermal_commitment import ThermalCommitment

parser = argparse.ArgumentParser()
parser.add_argument('--output-dir', type=Path, default=ROOT / 'outputs/research/revision/industrial_coupling')
OUT = parser.parse_args().output_dir
OUT.mkdir(parents=True, exist_ok=True)
checks, cases, residuals = [], {}, []


def close(a, b, label):
    error = float(np.max(np.abs(np.asarray(a) - np.asarray(b))))
    if error > 1e-7:
        raise AssertionError((label, a, b, error))
    residuals.append(error)


def site(production, units=None, **kwargs):
    T = len(production)
    data = dict(name='steel', node='plant', grid_node='grid',
        units=units or [CaptiveUnit('gas', 2., 0., 0., 0., 0., 0.)],
        fuel_calorific_basis='LHV', load_basis='gross_process_excluding_generator_auxiliaries',
        generator_cost_basis='non_fuel_operating_cost', gas_production_mw={'s': production},
        other_process_use_mw={'s': [0.] * T}, flare_limit_mw={'s': [100.] * T},
        import_limit_mw={'s': [100.] * T}, export_limit_mw={'s': [0.] * T},
        gas_storage_mwh=0., initial_gas_mwh=0., max_storage_charge_mw=0., max_storage_discharge_mw=0.,
        generation_fuel_cost_per_mwh=0., flare_cost_per_mwh=0.,
        combustion_t_per_mwh_fuel=.2, flaring_t_per_mwh_fuel=.3, process_use_t_per_mwh_fuel=.4)
    data.update(kwargs)
    return IndustrialSite(**data)


def fixture(load, production, **kwargs):
    T = len(load)
    return dict(nodes=['grid', 'plant'], scenarios=[Scenario('s', 1., {'grid': [0.] * T, 'plant': load})],
        generators=[Generator('public', 'grid', 100., 0., 0., 10., .5), Generator('gas', 'plant', 10., 0., 0., 0.)],
        industrial_sites=[site(production, **kwargs)])


def reconstruct(config, result):
    """Raw output arithmetic, independent of the extension's matrix builder."""
    dt = config.get('dt', 1.)
    ef, operating = 0., 0.
    controls = {c.generator: c for c in config.get('commitments', [])}
    for scenario in config['scenarios']:
        rr = result['scenarios'][scenario.name]
        balance = {n: -np.asarray(load, float) + np.asarray(rr['unserved'][n]) for n, load in scenario.load_mw.items()}
        scenario_cost, scenario_emissions = 0., 0.
        for gen in config['generators']:
            gross = np.asarray(rr['generation'][gen.name])
            balance[gen.node] += gross
            scenario_cost += dt * gross.sum() * gen.marginal_cost
            scenario_emissions += dt * gross.sum() * gen.emissions_t_per_mwh
            assert min(gross) >= -1e-8 and max(gross) <= gen.existing_mw + 1e-8
            if gen.name in controls:
                c = controls[gen.name]; u = rr['unit_commitment'][gen.name]
                scenario_cost += dt * sum(u['on']) * c.no_load_cost_per_hour + sum(u['startup']) * c.startup_cost + sum(u['shutdown']) * c.shutdown_cost
        for st in config['industrial_sites']:
            r = rr['industrial_sites'][st.name]
            net = np.asarray(r['net_grid_import_mw']); stock = np.asarray(r['gas_storage_mwh'])
            flare = np.asarray(r['flare_mw_fuel']); fuel = np.zeros(len(net))
            balance[st.node] += net; balance[st.grid_node] -= net
            close(rr['unserved'][st.node], np.zeros(len(net)), 'mandatory_industry')
            assert (net <= np.asarray(st.import_limit_mw[scenario.name]) + 1e-8).all()
            assert (net >= -np.asarray(st.export_limit_mw[scenario.name]) - 1e-8).all()
            assert (stock >= -1e-8).all() and (stock <= st.gas_storage_mwh + 1e-8).all()
            assert (np.diff(stock) <= dt * st.max_storage_charge_mw + 1e-8).all()
            assert (-np.diff(stock) <= dt * st.max_storage_discharge_mw + 1e-8).all()
            close(stock[[0, -1]], [st.initial_gas_mwh] * 2, 'gas_endpoints')
            assert (flare >= -1e-8).all() and (flare <= np.asarray(st.flare_limit_mw[scenario.name]) + 1e-8).all()
            for binding in st.units:
                g = binding.generator; gross = np.asarray(rr['generation'][g])
                state = rr['unit_commitment'].get(g, {'on': np.zeros(len(net)), 'startup': np.zeros(len(net))})
                on, start = np.asarray(state['on']), np.asarray(state['startup'])
                independent_fuel = gross * binding.fuel_mwh_per_mwh_gross + on * binding.no_load_fuel_mw + start * binding.startup_fuel_mwh / dt
                independent_aux = gross * binding.auxiliary_fraction + on * binding.online_auxiliary_mw + start * binding.startup_auxiliary_mwh / dt
                close(r['fuel_mw'][g], independent_fuel, 'fuel_relation')
                close(r['auxiliary_mw'][g], independent_aux, 'auxiliary_relation')
                close(r['net_generation_mw'][g], gross - independent_aux, 'net_generation')
                fuel += independent_fuel; balance[st.node] -= independent_aux
            production = np.asarray(st.gas_production_mw[scenario.name]); process = np.asarray(st.other_process_use_mw[scenario.name])
            close(np.diff(stock), dt * (production - process - fuel - flare), 'gas_conservation')
            emission = dt * (fuel.sum() * st.combustion_t_per_mwh_fuel + flare.sum() * st.flaring_t_per_mwh_fuel + process.sum() * st.process_use_t_per_mwh_fuel)
            close(emission, r['gas_boundary_emissions_t'], 'gas_emissions')
            scenario_emissions += emission
            scenario_cost += dt * (fuel.sum() * st.generation_fuel_cost_per_mwh + flare.sum() * st.flare_cost_per_mwh)
        for n, values in balance.items():
            close(values, np.zeros(len(values)), 'electric_balance:' + n)
        ef += scenario.probability * scenario_emissions
        operating += scenario.probability * scenario_cost
    close(ef, result['expected_emissions_t'], 'weighted_emissions')
    close(operating, result['cost_components']['operating'], 'weighted_operating_cost')
    close(operating, result['total_cost'], 'fixed_assets_total_cost')


def run(label, config, feasible=True):
    result = solve(**config)
    cases[label] = dict(inputs={k: [asdict(v) for v in value] if k in ('scenarios', 'generators', 'industrial_sites', 'commitments') else value
                               for k, value in config.items()}, result=result)
    assert result['feasible'] is feasible, (label, result)
    if feasible:
        reconstruct(config, result)
    else:
        assert result['proven_infeasible'] and result['solver_status'] == 2
    checks.append(label)
    return result


# Shared gas and other process use. Independently: 6-2 fuel permits 4 MW in
# the efficient unit, rather than unconstrained 9 MW from the cheaper old unit.
c = fixture([4.], [6.], units=[CaptiveUnit('old', 2., 0., 0., 0., 0., 0.), CaptiveUnit('new', 1., 0., 0., 0., 0., 0.)], other_process_use_mw={'s': [2.]})
c['scenarios'][0].load_mw['grid'] = [5.]
c['generators'] = [c['generators'][0], Generator('old', 'plant', 10., 0., 0., 0.), Generator('new', 'plant', 10., 0., 0., 1.)]
r = run('shared_fuel_priority', c)
close(r['scenarios']['s']['generation']['new'], [4.], 'efficient_unit')
close(r['scenarios']['s']['generation']['old'], [0.], 'old_unit')
close(r['total_cost'], 54., 'shared_cost_oracle')
legacy = solve(c['nodes'], c['scenarios'], c['generators'], lines=[Line('unrestricted', 'grid', 'plant', 100., flow_cost_per_mwh=0.)])
close(legacy['total_cost'], 0., 'unconstrained_cost_oracle')
close(legacy['scenarios']['s']['generation']['old'], [9.], 'unconstrained_generation')
cases['unconstrained_comparator'] = {'result': legacy, 'scope': 'Same demand and capacity, unlimited fuel and ordinary bidirectional line'}

c = fixture([10.], [20.], units=[CaptiveUnit('gas', 2., 0., 0., .1, 0., 0.)])
c['scenarios'][0].load_mw['grid'] = [2.]
r = run('gross_net_auxiliary', c)
close(r['scenarios']['s']['industrial_sites']['steel']['net_grid_import_mw'], [1.], 'net_aux_import')
close(r['total_cost'], 30., 'aux_cost_oracle')
plain = copy.deepcopy(c); plain['industrial_sites'][0] = replace(plain['industrial_sites'][0], units=[CaptiveUnit('gas', 2., 0., 0., 0., 0., 0.)])
close(run('zero_auxiliary_comparator', plain)['total_cost'], 20., 'no_aux_cost')

for export, expected_import, expected_cost in [(0., 0., 50.), (2., -2., 30.)]:
    c = fixture([4.], [20.], export_limit_mw={'s': [export]})
    c['scenarios'][0].load_mw['grid'] = [5.]
    r = run('export_limit_' + str(export), c)
    close(r['scenarios']['s']['industrial_sites']['steel']['net_grid_import_mw'], [expected_import], 'export_oracle')
    close(r['total_cost'], expected_cost, 'export_cost')

for rate, expected_cost, expected_stock in [(4., 0., [0., 4., 0.]), (2., 10., [0., 2., 0.])]:
    c = fixture([0., 2.], [4., 0.], gas_storage_mwh=4., max_storage_charge_mw=rate, max_storage_discharge_mw=rate)
    r = run('gas_storage_rate_' + str(rate), c)
    close(r['scenarios']['s']['industrial_sites']['steel']['gas_storage_mwh'], expected_stock, 'storage_oracle')
    close(r['total_cost'], expected_cost, 'storage_cost')
c = fixture([2.], [0.], gas_storage_mwh=4., initial_gas_mwh=4., max_storage_charge_mw=4., max_storage_discharge_mw=4.)
close(run('no_free_initial_gas', c)['total_cost'], 20., 'terminal_restoration')
run('insufficient_process_fuel', fixture([0.], [1.], other_process_use_mw={'s': [2.]}), False)
run('surplus_without_flare_or_export', fixture([0.], [4.], flare_limit_mw={'s': [0.]}), False)
c = fixture([2.], [0.], import_limit_mw={'s': [0.]}); c['expected_unserved_limit_mwh'] = 100.
run('industrial_demand_cannot_be_shed', c, False)

for dt, expected_fuel, expected_cost, expected_emissions in [(1., 21.5, 113., 6.7), (.5, 22., 60.5, 3.4)]:
    c = fixture([9. - .5 - .1 / dt], [expected_fuel + 7.],
        units=[CaptiveUnit('gas', 2., 1., .5, .1, .5, .1)], import_limit_mw={'s': [0.]},
        other_process_use_mw={'s': [3.]}, generation_fuel_cost_per_mwh=2., flare_cost_per_mwh=3.)
    c['dt'] = dt; c['generators'][1].marginal_cost = 5.; c['generators'][1].min_output_fraction = .5
    c['commitments'] = [ThermalCommitment('gas', startup_cost=7., no_load_cost_per_hour=1.)]
    r = run('startup_energy_dt_' + str(dt), c)
    close(r['total_cost'], expected_cost, 'startup_cost_oracle')
    close(r['expected_emissions_t'], expected_emissions, 'startup_emission_oracle')
    close(r['scenarios']['s']['generation']['gas'], [10.], 'startup_gross')
    binding = copy.deepcopy(c); binding['emissions_limit_t'] = expected_emissions
    run('binding_emissions_dt_' + str(dt), binding)
    binding['emissions_limit_t'] -= .01
    run('infeasible_emissions_dt_' + str(dt), binding, False)

c = fixture([2.], [1.]); base = c['industrial_sites'][0]
c['scenarios'] = [Scenario('low', .75, {'grid': [0.], 'plant': [2.]}), Scenario('high', .25, {'grid': [0.], 'plant': [2.]})]
c['industrial_sites'] = [replace(base, gas_production_mw={'low': [1.], 'high': [5.]}, other_process_use_mw={'low': [1.], 'high': [1.]},
    flare_limit_mw={'low': [100.], 'high': [100.]}, import_limit_mw={'low': [100.], 'high': [100.]}, export_limit_mw={'low': [0.], 'high': [0.]}, process_use_t_per_mwh_fuel=.3)]
r = run('scenario_probability_accounting', c)
close(r['total_cost'], 15., 'scenario_cost_oracle'); close(r['expected_emissions_t'], 1.25, 'scenario_emission_oracle')

# Reject distinct ways of obtaining a seemingly feasible but mis-specified case.
base = fixture([1.], [2.])
invalid_sites = {
    'net_meter': dict(load_basis='net_grid_purchase'),
    'fuel_cost_double_count': dict(generator_cost_basis='fuel_included'),
    'fuel_basis_missing': dict(fuel_calorific_basis=''),
    'public_node_is_private': dict(grid_node='plant'),
    'unknown_public_node': dict(grid_node='absent'),
    'unknown_unit': dict(units=[CaptiveUnit('absent', 2., 0., 0., 0., 0., 0.)]),
    'duplicate_unit': dict(units=[base['industrial_sites'][0].units[0]] * 2),
    'online_without_commitment': dict(units=[CaptiveUnit('gas', 2., 1., 0., 0., 0., 0.)]),
    'start_aux_without_commitment': dict(units=[CaptiveUnit('gas', 2., 0., 0., 0., 0., .1)]),
    'invalid_aux': dict(units=[CaptiveUnit('gas', 2., 0., 0., 1., 0., 0.)]),
    'invalid_heat_rate': dict(units=[CaptiveUnit('gas', .5, 0., 0., 0., 0., 0.)]),
    'negative_storage': dict(gas_storage_mwh=-1.),
    'initial_exceeds_storage': dict(initial_gas_mwh=1.),
    'nonfinite_flare_price': dict(flare_cost_per_mwh=float('inf')),
    'negative_emission_coefficient': dict(process_use_t_per_mwh_fuel=-1.),
    'missing_scenario': dict(gas_production_mw={}),
    'missing_mapping': dict(gas_production_mw=None),
    'wrong_horizon': dict(gas_production_mw={'s': [1., 2.]}),
    'negative_gas': dict(gas_production_mw={'s': [-1.]}),
    'nonfinite_gas': dict(gas_production_mw={'s': [float('nan')]}),
    'string_gas': dict(gas_production_mw={'s': ['2']}),
    'boolean_gas': dict(gas_production_mw={'s': [True]}),
    'infinite_interface': dict(import_limit_mw={'s': [float('inf')]}),
}
for label, changes in invalid_sites.items():
    c = copy.deepcopy(base); c['industrial_sites'][0] = replace(c['industrial_sites'][0], **changes)
    try: solve(**c)
    except ValueError: checks.append('reject_' + label)
    else: raise AssertionError('Accepted: ' + label)
for label in ['line_bypass', 'duplicate_site', 'duplicate_private_node', 'capacity_expansion', 'emission_double_count', 'unbound_generator']:
    c = copy.deepcopy(base)
    if label == 'line_bypass': c['lines'] = [Line('bypass', 'grid', 'plant', 1.)]
    if label == 'duplicate_site': c['industrial_sites'] *= 2
    if label == 'duplicate_private_node': c['industrial_sites'].append(replace(c['industrial_sites'][0], name='other'))
    if label == 'capacity_expansion': c['generators'][1].max_new_mw = 1.
    if label == 'emission_double_count': c['generators'][1].emissions_t_per_mwh = .2
    if label == 'unbound_generator': c['generators'].append(Generator('unbound', 'plant', 10., 0., 0., 0.))
    try: solve(**c)
    except ValueError: checks.append('reject_' + label)
    else: raise AssertionError('Accepted: ' + label)

report = dict(check_count=len(checks), checks=checks, solve_cases=len(cases),
    maximum_independent_residual=max(residuals), scope='Synthetic mathematical validation only; no qualified industrial measurements',
    prespecified_design='DESIGN.md, commit 1d58d6e', empirical_parameter_sets=0)
(OUT / 'validation.json').write_text(json.dumps(report, indent=2) + '\n')
(OUT / 'analytic_cases.json').write_text(json.dumps(cases, indent=2) + '\n')
paths = [Path(__file__), ROOT / 'work/research/models/coupled_grid_compute.py', ROOT / 'work/research/models/industrial_captive.py', ROOT / 'work/research/models/thermal_commitment.py', ROOT / 'outputs/research/revision/industrial_coupling/DESIGN.md']
(OUT / 'implementation_manifest.json').write_text(json.dumps({str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}, indent=2) + '\n')
print(json.dumps({k: v for k, v in report.items() if k != 'checks'}, indent=2))
