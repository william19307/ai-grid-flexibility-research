"""Independent unit accounting and exact grid rounding for candidate inventory."""
from pathlib import Path
from decimal import Decimal
from fractions import Fraction
from collections import Counter,defaultdict
import csv,hashlib,json

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'outputs/research/revision/weather_fleet_v2'
INPUT=ROOT/'work/research/prepared/technology_separated_operating_2025_candidate_inventory.csv'


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def quarter(value):
    f=Fraction(value)*4
    return Fraction((f.numerator*2+f.denominator)//(f.denominator*2),4)


def main():
    source_rows=list(csv.DictReader(INPUT.open()))
    source={r['unit_id']:r for r in source_rows}
    assert len(source)==len(source_rows)==2902, 'Duplicate or missing source unit'
    assert sha(INPUT)=='dce044cf7c2cd0d0a81774fc9b10e85ed566fd8e79378949e72459f36432c25a'
    grids=list(csv.DictReader((OUT/'fixed2025_grid_weights_CANDIDATE.csv').open()))
    held_rows=list(csv.DictReader((OUT/'held_units.csv').open()))
    held={r['unit_id']:r for r in held_rows}
    assert len(held)==len(held_rows), 'Duplicate held unit'
    for unit,r in held.items():
        for field in ['province','technology','start_year']:
            assert r[field]==source[unit][field], ('Changed held source field',unit,field)
        for field in ['mw','lat','lon']:
            assert Decimal(r[field])==Decimal(source[unit][field]), ('Changed held numeric field',unit,field)
    seen=[];counts=Counter();totals=defaultdict(Decimal);cell_checks=0
    for g in grids:
        ids=g['unit_ids'].split(';');assert len(ids)==int(g['unit_count'])
        total=Decimal(0)
        for unit in ids:
            r=source[unit];assert unit not in held
            assert r['province']==g['province']
            expected={'Onshore':'wind_onshore','Offshore hard mount':'wind_offshore','PV':'solar_pv','Assumed PV':'solar_pv'}[r['technology']]
            assert expected==g['technology_group']
            assert quarter(r['lat'])==Fraction(g['grid_lat']) and quarter(r['lon'])==Fraction(g['grid_lon'])
            total+=Decimal(r['mw']);seen.append(unit);counts[expected]+=1;cell_checks+=2
        assert abs(total-Decimal(g['capacity_mw']))<Decimal('1e-8')
        totals[(g['province'],g['technology_group'])]+=total
    assert len(seen)==len(set(seen))
    assert set(seen)|set(held)==set(source) and not set(seen)&set(held)
    expected_solar_thermal={u for u,r in source.items() if r['technology']=='Solar Thermal'}
    actual_solar_thermal={u for u,r in held.items() if r['technology']=='Solar Thermal'}
    assert expected_solar_thermal==actual_solar_thermal and len(actual_solar_thermal)==5
    gross={u for u,r in held.items() if r['coordinate_screen']=='far_outside_hold'}
    assert len(gross)==6
    for u in gross:assert float(held[u]['approximate_distance_outside_province_km'])>50
    source_mw=sum((Decimal(r['mw']) for r in source.values()),Decimal(0))
    included_mw=sum(totals.values(),Decimal(0));held_mw=sum((Decimal(r['mw']) for r in held.values()),Decimal(0))
    assert source_mw==included_mw+held_mw
    plan=json.loads((OUT/'pilot_plan.json').read_text());pairs=defaultdict(list)
    for r in plan['pilot_requests']:pairs[r['unit_id']].append(r)
    assert len(pairs)==4
    for unit,pair in pairs.items():
        assert len(pair)==2 and unit in seen
        a,b=[dict(x['parameters']) for x in pair]
        selections={a.pop('cell_selection'),b.pop('cell_selection')}
        assert selections=={'nearest','sea' if source[unit]['technology']=='Offshore hard mount' else 'land'}
        assert a==b and a['models']=='era5' and a['elevation']=='nan'
    result=dict(source_units=len(source),candidate_units=len(seen),held_units=len(held),
        unique_candidate_grid_points=len({(g['grid_lat'],g['grid_lon']) for g in grids}),
        independent_coordinate_rounding_checks=cell_checks,pilot_pair_checks=len(pairs),
        source_mw=str(source_mw),candidate_mw=str(included_mw),held_mw=str(held_mw),capacity_conservation_exact=True,
        input_sha256=sha(INPUT),grid_sha256=sha(OUT/'fixed2025_grid_weights_CANDIDATE.csv'),
        held_sha256=sha(OUT/'held_units.csv'),plan_sha256=sha(OUT/'pilot_plan.json'),verifier_sha256=sha(Path(__file__)),
        scope='Exact bookkeeping, technology separation and arithmetic grid mapping; no geographic truth or generation calibration claim')
    (OUT/'independent_inventory_verification.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
