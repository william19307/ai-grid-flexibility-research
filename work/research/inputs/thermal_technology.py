"""Technology-preserving staging, with no empirical fleet or solver admission."""
from decimal import Decimal, InvalidOperation
import csv, hashlib, json, re
from pathlib import Path

ID = 'GEM unit/phase ID'
SCHEMA = 'thermal_technology_staging_v1'
UNITS = {'efficiency': 'per unit', 'VOM': 'EUR/MWh', 'investment': 'EUR/kW',
         'FOM': '%/year', 'lifetime': 'years', 'fuel': 'EUR/MWh_th',
         'CO2 intensity': 'tCO2/MWh_th', 'c_b': '50oC/100oC', 'c_v': '50oC/100oC'}
GAS_FUELS = {'fossil gas: natural gas', 'fossil gas: LNG'}
BFG_FUELS = {'industrial by-product: blast furnace gas',
            'industrial by-product: blast furnace gas, industrial by-product: coke oven gas'}


def decimal(value):
    if isinstance(value, bool):
        raise ValueError('Boolean is not a numeric parameter')
    try:
        result = Decimal(str(value))
    except (ValueError, InvalidOperation) as exc:
        raise ValueError('Invalid numeric parameter') from exc
    if not result.is_finite():
        raise ValueError('Nonfinite parameter')
    return result


def read_verified_csv(path, expected_sha256):
    path = Path(path)
    if hashlib.sha256(path.read_bytes()).hexdigest() != expected_sha256:
        raise ValueError('Source version not admitted: ' + path.name)
    with path.open(newline='') as f:
        return list(csv.DictReader(f))


def verify_cohort(records, reference):
    def indexed(rows):
        by_id = {}
        for row in rows:
            uid = row.get(ID)
            if not uid or uid in by_id:
                raise ValueError('Missing or duplicate unit identity')
            by_id[uid] = row
        return by_id
    a, b = indexed(records), indexed(reference)
    if not a or a != b:
        raise ValueError('Cohort fields/membership differ from the frozen audited source')


def archive_parameters(rows, discount_rate):
    rate = decimal(discount_rate)
    if not 0 <= rate <= 1:
        raise ValueError('Discount rate must be explicit and between zero and one')
    provenance = []
    def get(technology, parameter):
        matches = [r for r in rows if r.get('technology') == technology and r.get('parameter') == parameter]
        if len(matches) != 1:
            raise ValueError('Absent/duplicate archive parameter: ' + technology + ':' + parameter)
        r = matches[0]
        if decimal(r['year']) != 2030 or r['unit'] != UNITS[parameter] or not r['source'].strip():
            raise ValueError('Wrong year/unit or absent parameter source')
        v = decimal(r['value'])
        if v < 0:
            raise ValueError('Negative parameter')
        provenance.append(dict(r))
        return v
    fuel, co2 = get('gas', 'fuel'), get('gas', 'CO2 intensity')
    parameters = {}
    for technology in ['OCGT', 'CCGT']:
        eta, vom, investment, fom, lifetime = [get(technology, p) for p in ['efficiency', 'VOM', 'investment', 'FOM', 'lifetime']]
        if not 0 < eta <= 1 or lifetime <= 0 or lifetime != lifetime.to_integral_value():
            raise ValueError('Invalid efficiency/lifetime')
        recovery = Decimal(1) / lifetime if rate == 0 else rate / (1 - (1 + rate) ** (-int(lifetime)))
        values = dict(efficiency=eta, fuel_cost_per_mwh_th=fuel, fuel_co2_t_per_mwh_th=co2,
                      vom_eur_per_mwh=vom, investment_eur_per_kw=investment, fom_percent_per_year=fom,
                      lifetime_years=lifetime, discount_rate=rate,
                      marginal_cost_eur_per_mwh=fuel/eta + vom, emissions_t_per_mwh=co2/eta,
                      annualized_capital_eur_per_mw=investment*1000*recovery,
                      fixed_om_eur_per_mw_year=investment*1000*fom/100,
                      annualized_capital_plus_fixed_om_eur_per_mw=investment*1000*(recovery+fom/100))
        if technology == 'CCGT':
            values.update(c_b=get('CCGT','c_b'), c_v=get('CCGT','c_v'))
        parameters[technology] = dict(values={k:str(v) for k,v in values.items()},
            scope='ARCHIVE_CONDITIONAL_REFERENCE_NOT_UNIT_CALIBRATION',
            heat_coefficients_applied=False, electrical_meter_basis='NOT_ESTABLISHED_FOR_SOURCE_UNITS',
            efficiency_time_basis='annual_average_from_archive_description')
    return parameters, provenance


def stage(records, parameters):
    verify_cohort(records, records)
    stock = []
    for row in records:
        cap = decimal(row['capacity_numeric_MW'])
        if cap <= 0:
            raise ValueError('Unit capacity must be positive')
        technology, fuel = row['Technology'], row['Fuel']
        if technology == 'combined cycle' and fuel in GAS_FUELS:
            category, reference = 'CCGT_fossil_gas', 'CCGT'
        elif technology == 'steam turbine' and fuel in BFG_FUELS:
            category, reference = 'industrial_byproduct_steam', None
        else:
            category, reference = 'unclassified_requires_review', None
        chp = {'yes':'reported_yes','no':'reported_no'}.get(row['CHP'], 'unknown')
        captive_fields = [row[k] for k in ['Captive Industry Type','Captive Industry Use','Captive Non Industry Use']]
        captive = 'reported_use' if any(v.strip() and v.strip().lower() != 'not found' for v in captive_fields) else 'unknown'
        requirements = ['scenario_vintage_and_retirement', 'gross_net_meter_and_load_scope',
                        'unit_availability_and_outage', 'unit_start_ramp_minimum_output',
                        'site_grid_interface_or_public_generator_evidence', 'unit_fuel_and_cost_boundary']
        if chp == 'reported_yes':requirements.append('heat_service_and_feasible_power_heat_region')
        elif chp == 'unknown':requirements.append('resolve_heat_service_presence_and_obligations')
        if captive == 'unknown':requirements.append('resolve_captive_or_public_supply_role')
        if category == 'industrial_byproduct_steam':requirements.append('industrial_site_shared_gas_and_auxiliaries')
        if category == 'unclassified_requires_review':requirements.append('resolve_technology_and_fuel')
        if reference:requirements.append('validate_or_explicitly_bound_archive_parameter_transfer')
        label_issue=bool(re.fullmatch(r'\d{4}-\d{2}-\d{2} 00:00:00',row['Unit / Phase name']))
        if label_issue:requirements.append('resolve_date_formatted_unit_name_from_primary_documents')
        stock.append(dict(unit_id=row[ID], province=row['province_source_label'], role='existing_candidate_stock',
            capacity_mw=str(cap), new_build_capacity_mw='0', candidate_technology=category, fuel=fuel,
            chp_evidence=chp, captive_evidence=captive, date_formatted_unit_label=label_issue, conditional_parameter_reference=reference,
            unresolved_requirements=requirements, dispatch_ready=False, source_record=dict(row),
            source_record_sha256=hashlib.sha256(json.dumps(row,sort_keys=True,ensure_ascii=False).encode()).hexdigest()))
    # This preserves the legacy prospective technology without inferring policy permission/cap.
    investment = [dict(option_id=p+':new_OCGT',province=p,technology='OCGT',role='prospective_investment_option',
                      existing_capacity_mw='0',max_new_capacity_mw=None,permission='UNRESOLVED_POLICY',
                      conditional_parameter_reference='OCGT',dispatch_ready=False)
                  for p in sorted({r['province_source_label'] for r in records} | {'Guizhou'})]
    return dict(schema=SCHEMA, scope='STAGING_ONLY_NOT_A_SOLVER_INPUT', vintage='legacy_conditional_2030_membership_not_observed_2030',
                stock=stock, investment_options=investment, conditional_parameters=parameters,
                qualified_operational_parameter_sets=0)


def require_dispatch_ready(manifest):
    """Never turn a candidate staging ledger into a fleet by dropping blocked rows."""
    if manifest.get('schema') != SCHEMA or not manifest.get('stock'):
        raise ValueError('Not a complete staging manifest')
    blocked = {r['unit_id']:r['unresolved_requirements'] for r in manifest['stock'] if r['unresolved_requirements']}
    if blocked:
        raise ValueError(f'{len(blocked)} units have unresolved operating evidence; no partial fleet emitted')
    # No unsupported ad-hoc edits can make this version an approval/compilation mechanism.
    raise ValueError('This schema is staging only; a separately reviewed operational input compiler is required')
