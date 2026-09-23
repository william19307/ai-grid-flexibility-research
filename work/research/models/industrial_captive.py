"""Explicit single-basis process-gas and captive electric boundary.

Coefficients are inputs, not fitted or inferred observations. The affine fuel
curve, proportional/online/start auxiliaries and lossless site interface omit
gas quality, pressure, heat service and upstream/process-chemical emissions.
"""
from dataclasses import dataclass
from typing import Mapping, Sequence
import numpy as np


@dataclass(frozen=True)
class CaptiveUnit:
    generator: str
    fuel_mwh_per_mwh_gross: float
    no_load_fuel_mw: float
    startup_fuel_mwh: float
    auxiliary_fraction: float
    online_auxiliary_mw: float
    startup_auxiliary_mwh: float


@dataclass(frozen=True)
class IndustrialSite:
    name: str
    node: str
    grid_node: str
    units: Sequence[CaptiveUnit]
    fuel_calorific_basis: str
    load_basis: str
    generator_cost_basis: str
    gas_production_mw: Mapping[str, Sequence[float]]
    other_process_use_mw: Mapping[str, Sequence[float]]
    flare_limit_mw: Mapping[str, Sequence[float]]
    import_limit_mw: Mapping[str, Sequence[float]]
    export_limit_mw: Mapping[str, Sequence[float]]
    gas_storage_mwh: float
    initial_gas_mwh: float
    max_storage_charge_mw: float
    max_storage_discharge_mw: float
    generation_fuel_cost_per_mwh: float
    flare_cost_per_mwh: float
    combustion_t_per_mwh_fuel: float
    flaring_t_per_mwh_fuel: float
    process_use_t_per_mwh_fuel: float


def _nonnegative(values):
    try:
        return all(not isinstance(x, (bool, np.bool_)) and np.isscalar(x)
                   and np.isfinite(x) and x >= 0 for x in values)
    except (TypeError, ValueError):
        return False


def validate(sites, nodes, generators, lines, controls, scenario_names, horizon):
    if len({s.name for s in sites}) != len(sites) or any(not s.name for s in sites):
        raise ValueError('Industrial site names must be nonempty and unique')
    site_nodes = {s.node for s in sites}
    if len(site_nodes) != len(sites):
        raise ValueError('Industrial sites cannot share a private node')
    gen = {g.name: g for g in generators}
    owned = set()
    for site in sites:
        if site.node not in nodes or site.grid_node not in nodes or site.grid_node in site_nodes:
            raise ValueError('Industrial interface must connect a private node to a public node')
        if any(site.node in (line.source, line.target) for line in lines):
            raise ValueError('Ordinary lines would bypass the explicit industrial interface')
        if site.fuel_calorific_basis not in ('LHV', 'HHV'):
            raise ValueError('Declare a common fuel calorific basis')
        if site.load_basis != 'gross_process_excluding_generator_auxiliaries':
            raise ValueError('Industrial demand must declare the gross process meter boundary')
        if site.generator_cost_basis != 'non_fuel_operating_cost':
            raise ValueError('Declare generator cost separately from explicit fuel use')
        names = [u.generator for u in site.units]
        if not names or len(set(names)) != len(names) or set(names) & owned:
            raise ValueError('Captive units require unique single-gas-system ownership')
        if set(names) != {g.name for g in generators if g.node == site.node}:
            raise ValueError('Every generator at a private site must have a fuel binding')
        owned.update(names)
        for unit in site.units:
            g = gen[unit.generator]
            if g.max_new_mw != 0 or g.emissions_t_per_mwh != 0:
                raise ValueError('Captive capacity must be fixed; emissions are counted from fuel')
            values = [unit.fuel_mwh_per_mwh_gross, unit.no_load_fuel_mw, unit.startup_fuel_mwh,
                      unit.auxiliary_fraction, unit.online_auxiliary_mw, unit.startup_auxiliary_mwh]
            if not _nonnegative(values) or unit.fuel_mwh_per_mwh_gross < 1 or unit.auxiliary_fraction >= 1:
                raise ValueError('Invalid captive heat-rate or auxiliary coefficient')
            if unit.generator not in controls and any(values[i] != 0 for i in (1, 2, 4, 5)):
                raise ValueError('Online/start fuel and auxiliaries require commitment states')
        values = [site.gas_storage_mwh, site.initial_gas_mwh, site.max_storage_charge_mw,
                  site.max_storage_discharge_mw, site.generation_fuel_cost_per_mwh,
                  site.flare_cost_per_mwh, site.combustion_t_per_mwh_fuel,
                  site.flaring_t_per_mwh_fuel, site.process_use_t_per_mwh_fuel]
        if not _nonnegative(values) or site.initial_gas_mwh > site.gas_storage_mwh:
            raise ValueError('Invalid industrial storage, cost or emissions input')
        for mapping in (site.gas_production_mw, site.other_process_use_mw, site.flare_limit_mw,
                        site.import_limit_mw, site.export_limit_mw):
            if not isinstance(mapping, Mapping) or set(mapping) != scenario_names:
                raise ValueError('Industrial series must cover exactly all scenarios')
            for values in mapping.values():
                try:
                    raw = np.asarray(values)
                    if raw.dtype.kind not in 'iuf':
                        raise ValueError('Industrial series must contain real numbers')
                    a = raw.astype(float)
                except (TypeError, ValueError) as exc:
                    raise ValueError('Invalid industrial series') from exc
                if a.shape != (horizon,) or not np.isfinite(a).all() or (a < 0).any():
                    raise ValueError('Industrial series must be finite, nonnegative and aligned')
    return site_nodes


def add_constraints(matrix, sites, scenario, dt, indices, balances):
    """Return incremental operating IDs, emissions coefficients and fixed CO2."""
    op_ids, co2, fixed_co2, records = [], {}, 0., {}
    name, probability = scenario.name, scenario.probability
    for site in sites:
        T = len(scenario.load_mw[site.node])
        net, flare, stock, fuel, auxiliaries = [], [], [], {}, {}
        for t in range(T + 1):
            stock.append(matrix.var(('industrial_gas_stock', name, site.name, t), upper=site.gas_storage_mwh))
        matrix.equal({stock[0]: 1}, site.initial_gas_mwh, ('initial_process_gas', name, site.name))
        matrix.equal({stock[-1]: 1}, site.initial_gas_mwh, ('terminal_process_gas', name, site.name))
        for unit in site.units:
            fuel[unit.generator], auxiliaries[unit.generator] = [], []
            commitment = indices['commitment'].get(unit.generator)
            for t, gross in enumerate(indices['generation'][unit.generator]):
                f = matrix.var(('captive_fuel', name, unit.generator, t),
                               probability * dt * site.generation_fuel_cost_per_mwh)
                fuel[unit.generator].append(f); op_ids.append(f)
                row = {f: 1, gross: -unit.fuel_mwh_per_mwh_gross}
                aux = {gross: unit.auxiliary_fraction}
                if commitment:
                    on, start = commitment['on'][t], commitment['startup'][t]
                    row[on], row[start] = -unit.no_load_fuel_mw, -unit.startup_fuel_mwh / dt
                    aux[on], aux[start] = unit.online_auxiliary_mw, unit.startup_auxiliary_mwh / dt
                matrix.equal(row, 0, ('captive_fuel_relation', name, unit.generator, t))
                for variable, coefficient in aux.items():
                    balances[site.node, t][variable] = balances[site.node, t].get(variable, 0) - coefficient
                auxiliaries[unit.generator].append(aux)
                co2[f] = probability * dt * site.combustion_t_per_mwh_fuel
        for t in range(T):
            v = matrix.var(('industrial_net_import', name, site.name, t),
                           lower=-float(site.export_limit_mw[name][t]), upper=float(site.import_limit_mw[name][t]))
            net.append(v); balances[site.node, t][v] = 1; balances[site.grid_node, t][v] = -1
            f = matrix.var(('industrial_flare', name, site.name, t), probability * dt * site.flare_cost_per_mwh,
                           upper=float(site.flare_limit_mw[name][t]))
            flare.append(f); op_ids.append(f); co2[f] = probability * dt * site.flaring_t_per_mwh_fuel
            row = {stock[t+1]: 1, stock[t]: -1, f: dt}
            row.update({fuel[u.generator][t]: dt for u in site.units})
            matrix.equal(row, dt * float(site.gas_production_mw[name][t] - site.other_process_use_mw[name][t]),
                         ('industrial_gas_balance', name, site.name, t))
            matrix.upper({stock[t+1]: 1, stock[t]: -1}, dt * site.max_storage_charge_mw)
            matrix.upper({stock[t+1]: -1, stock[t]: 1}, dt * site.max_storage_discharge_mw)
        fixed_co2 += probability * dt * sum(site.other_process_use_mw[name]) * site.process_use_t_per_mwh_fuel
        records[site.name] = dict(net_grid_import_mw=net, flare_mw_fuel=flare, gas_storage_mwh=stock,
                                  fuel_mw=fuel, auxiliary_rows=auxiliaries)
    indices['industrial_sites'] = records
    return op_ids, co2, fixed_co2


def extract(sites, scenario, indices, x, dt):
    output = {}
    for site in sites:
        ix = indices['industrial_sites'][site.name]
        r = {key: x[ix[key]].tolist() for key in ('net_grid_import_mw', 'flare_mw_fuel', 'gas_storage_mwh')}
        r['fuel_mw'] = {g: x[ids].tolist() for g, ids in ix['fuel_mw'].items()}
        r['auxiliary_mw'] = {g: [float(sum(c*x[v] for v, c in row.items())) for row in rows]
                             for g, rows in ix['auxiliary_rows'].items()}
        r['net_generation_mw'] = {u.generator: (x[indices['generation'][u.generator]] - r['auxiliary_mw'][u.generator]).tolist() for u in site.units}
        r['gas_production_mw_fuel'] = list(map(float, site.gas_production_mw[scenario.name]))
        r['other_process_use_mw_fuel'] = list(map(float, site.other_process_use_mw[scenario.name]))
        r['gas_boundary_emissions_t'] = float(dt * (sum(map(sum, r['fuel_mw'].values())) * site.combustion_t_per_mwh_fuel
            + sum(r['flare_mw_fuel']) * site.flaring_t_per_mwh_fuel
            + sum(r['other_process_use_mw_fuel']) * site.process_use_t_per_mwh_fuel))
        output[site.name] = r
    return output
