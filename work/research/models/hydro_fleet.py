"""Technology-aware hydro split; no claim of calibrated reservoir hydrology."""
from pathlib import Path
import csv
import math
from coupled_grid_compute import Storage

ROOT = Path(__file__).resolve().parents[3]
INVENTORY = ROOT / 'outputs/research/revision/hydro/hydro_2030_by_technology.csv'
NON_PUMPED = {'conventional storage', 'run-of-river', 'conventional and run-of-river'}


def split_hydro(province, expected_total_mw, inventory=INVENTORY):
    with Path(inventory).open() as f:
        rows = [r for r in csv.DictReader(f) if r['province'] == province.replace(' ', '')]
    total = sum(float(r['capacity_mw']) for r in rows)
    if not math.isclose(total, expected_total_mw, abs_tol=1e-6):
        raise ValueError(f'{province}: classified {total} MW != original inventory {expected_total_mw} MW')
    unknown = [r for r in rows if r['technology'] not in NON_PUMPED | {'pumped storage'}]
    if unknown:
        raise ValueError(f'{province}: unresolved hydro technology {unknown}')
    pumped = sum(float(r['capacity_mw']) for r in rows if r['technology'] == 'pumped storage')
    return dict(total_mw=total, pumped_mw=pumped, non_pumped_mw=total-pumped,
                by_technology={r['technology']:float(r['capacity_mw']) for r in rows})


def pumped_storage(name, node, power_mw, duration_h, roundtrip_efficiency):
    """Duration is AC-deliverable hours at rated power, not reservoir-side hours.

    Equal pump/turbine power and symmetric efficiencies are explicit scenarios.
    Cyclic terminal state prevents initial energy from becoming free net supply.
    """
    if not all(math.isfinite(v) for v in [power_mw, duration_h, roundtrip_efficiency]):
        raise ValueError('Nonfinite pumped-storage parameter')
    if power_mw < 0 or duration_h <= 0 or not 0 < roundtrip_efficiency <= 1:
        raise ValueError('Invalid pumped-storage parameter')
    efficiency = math.sqrt(roundtrip_efficiency)
    return Storage(name, node, existing_power_mw=power_mw,
                   existing_energy_mwh=power_mw*duration_h/efficiency,
                   charge_efficiency=efficiency, discharge_efficiency=efficiency,
                   initial_soc_fraction=0.5)
