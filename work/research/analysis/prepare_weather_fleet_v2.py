"""Technology-separated fixed-2025 candidate geography and frozen grid pilot.

This is not a historical fleet reconstruction or a generation calibration.
Suspect coordinates and solar thermal capacity remain in explicit accounting.
"""
from pathlib import Path
from decimal import Decimal, ROUND_HALF_UP
from collections import defaultdict
import csv, hashlib, json, math, platform
import shapely
from shapely.geometry import shape, Point
from shapely.ops import nearest_points

ROOT=Path(__file__).resolve().parents[3]
PREP=ROOT/'work/research/prepared'
SRC=ROOT/'work/research/sources/weather_fleet_revision_v2'
OUT=ROOT/'outputs/research/revision/weather_fleet_v2'
INPUT=PREP/'technology_separated_operating_2025_candidate_inventory.csv'
BOUNDARY=SRC/'province_boundaries.geojson'
BASE='https://archive-api.open-meteo.com/v1/archive'


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':')).encode()
def snap(x):return float((Decimal(str(x))*4).quantize(Decimal('1'),rounding=ROUND_HALF_UP)/4)
def write_csv(p,rows):
    with p.open('w') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
def save(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')


def approximate_km(p,q):
    a,b=map(math.radians,[p.y,q.y]);dl=math.radians(q.x-p.x)
    return 6371*2*math.asin(min(1,math.sqrt(math.sin((a-b)/2)**2+math.cos(a)*math.cos(b)*math.sin(dl/2)**2)))


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    source_audit=json.loads((ROOT/'outputs/research/revision/weather_site_technology/audit.json').read_text())
    assert sha(INPUT)==source_audit['candidate_sha256']
    assert sha(BOUNDARY)=='3a00467a0db9b4136facb5f2f3d0edbfd96adb15651cfdf63991da9281030e85'
    features=json.loads(BOUNDARY.read_text())['features']
    polygons={f['properties']['shapeName']:shape(f['geometry']) for f in features}
    rows=[];cells=defaultdict(list)
    for s in csv.DictReader(INPUT.open()):
        r=dict(s);r['mw']=float(s['mw']);r['lat']=float(s['lat']);r['lon']=float(s['lon'])
        tech={'Onshore':'wind_onshore','Offshore hard mount':'wind_offshore','PV':'solar_pv',
              'Assumed PV':'solar_pv','Solar Thermal':'solar_thermal'}.get(s['technology'],'unknown')
        r['technology_group']=tech
        r['pv_classification_assumed_in_source']=s['technology']=='Assumed PV'
        r['historical_2020_scope']=('surviving_2025_unit_started_before_2020' if s['start_year'] and int(s['start_year'])<2020 else
             'within_2020_commissioning_month_unknown' if s['start_year']=='2020' else
             'post2020_unit' if s['start_year'] else 'start_year_unknown')
        p=Point(r['lon'],r['lat']);poly=polygons[r['province']+' Province']
        r['approximate_distance_outside_province_km']=0.
        if tech=='wind_offshore':
            r['coordinate_screen']='offshore_not_tested_against_land_province_polygon'
        elif poly.covers(p):r['coordinate_screen']='inside_coarse_province_polygon'
        else:
            distance=approximate_km(p,nearest_points(poly,p)[0])
            r['approximate_distance_outside_province_km']=distance
            r['coordinate_screen']='far_outside_hold' if distance>50 else 'near_boundary_review_retained'
        r['weather_candidate']=tech in ['solar_pv','wind_onshore','wind_offshore'] and r['coordinate_screen']!='far_outside_hold'
        r['grid_lat']=snap(r['lat']);r['grid_lon']=snap(r['lon'])
        rows.append(r)
        if r['weather_candidate']:cells[(r['province'],tech,r['grid_lat'],r['grid_lon'])].append(r)
    assert len({r['unit_id'] for r in rows})==len(rows)==2902
    enriched=PREP/'weather_fleet_v2_units_CANDIDATE.csv';write_csv(enriched,rows)
    weights=[]
    for (province,tech,lat,lon),g in sorted(cells.items()):
        weights.append(dict(province=province,technology_group=tech,grid_lat=lat,grid_lon=lon,
            capacity_mw=math.fsum(r['mw'] for r in g),unit_count=len(g),
            near_boundary_review_mw=math.fsum(r['mw'] for r in g if r['coordinate_screen']=='near_boundary_review_retained'),
            assumed_pv_mw=math.fsum(r['mw'] for r in g if r['pv_classification_assumed_in_source']),
            known_pre2020_survivor_mw=math.fsum(r['mw'] for r in g if r['historical_2020_scope']=='surviving_2025_unit_started_before_2020'),
            unit_ids=';'.join(sorted(r['unit_id'] for r in g))))
    weights_path=OUT/'fixed2025_grid_weights_CANDIDATE.csv';write_csv(weights_path,weights)
    problems=[r for r in rows if not r['weather_candidate']]
    write_csv(OUT/'held_units.csv',problems)
    summary=[]
    for province,tech in sorted({(r['province'],r['technology_group']) for r in rows}):
        g=[r for r in rows if r['province']==province and r['technology_group']==tech]
        total=math.fsum(r['mw'] for r in g);admitted=math.fsum(r['mw'] for r in g if r['weather_candidate'])
        held=math.fsum(r['mw'] for r in g if not r['weather_candidate'])
        assert abs(total-admitted-held)<1e-8
        summary.append(dict(province=province,technology_group=tech,source_mw=total,candidate_mw=admitted,
            held_mw=held,rows=len(g),candidate_units=sum(r['weather_candidate'] for r in g),
            candidate_grid_cells=sum(w['province']==province and w['technology_group']==tech for w in weights)))
    # Freeze a small methodological pilot before any new weather is fetched.
    # Selection uses capacity/ID only and excludes land-boundary-review sites.
    pilots=[]
    for province,tech in [('Gansu','wind_onshore'),('Guizhou','wind_onshore'),('Jiangsu','wind_onshore'),('Jiangsu','wind_offshore')]:
        pool=[r for r in rows if r['province']==province and r['technology_group']==tech and r['weather_candidate']
              and r['coordinate_screen']!='near_boundary_review_retained']
        chosen=sorted(pool,key=lambda r:(-r['mw'],r['unit_id']))[0]
        for cell in ['nearest','sea' if tech=='wind_offshore' else 'land']:
            params=dict(latitude=f'{chosen["lat"]:.6f}',longitude=f'{chosen["lon"]:.6f}',start_date='2020-01-01',end_date='2021-01-01',
                hourly='wind_speed_100m,wind_speed_10m,shortwave_radiation,direct_radiation,diffuse_radiation,temperature_2m,surface_pressure',
                timezone='Asia/Shanghai',models='era5',wind_speed_unit='ms',cell_selection=cell,elevation='nan')
            pilots.append(dict(id=hashlib.sha256(canonical(params)).hexdigest()[:24],province=province,technology_group=tech,
                unit_id=chosen['unit_id'],name=chosen['name'],mw=chosen['mw'],parameters=params,expected_hours=8808,
                conservative_call_equivalents=27,purpose='Paired grid-selection diagnostic; not empirical generation validation'))
    plan=dict(schema_version=2,source_inventory_sha256=sha(INPUT),boundary_sha256=sha(BOUNDARY),
        fixed_candidate_scope='July-2025 operating inventory; stable geography under 2015-2024 weather, not reconstructed historical generation',
        weather_years=list(range(2015,2025)),grid_method='Nearest 0.25 degree center, half ties upward; candidate only, actual returned grid coordinates must be checked',
        proposed_grid_parameters=dict(models='era5',cell_selection='nearest',elevation='nan',timezone='Asia/Shanghai',wind_speed_unit='ms'),
        unique_candidate_grid_points=len({(w['grid_lat'],w['grid_lon']) for w in weights}),
        full_grid_acquisition_authorized_by_this_plan=False,
        full_grid_gate='First verify pilot cell mapping, source coordinates and technology-specific conversion; then freeze a distinct full request list',
        pilot_selection_rule='Largest-capacity unflagged unit per four wind groups; unit ID ascending breaks ties; two cell selection settings; fixed before acquisition',
        pilot_requests=pilots)
    target=OUT/'pilot_plan.json'
    if target.exists():assert json.loads(target.read_text())==plan,'Frozen pilot plan changed'
    else:save(target,plan)
    save(OUT/'inventory_audit.json',dict(input_sha256=sha(INPUT),boundary_sha256=sha(BOUNDARY),
        boundary_metadata_sha256=sha(SRC/'geoboundaries_metadata.json'),enriched_candidate_sha256=sha(enriched),
        grid_weights_sha256=sha(weights_path),builder_sha256=sha(Path(__file__)),python=platform.python_version(),shapely=shapely.__version__,
        source_unit_count=len(rows),held_count=len(problems),summary=summary,
        limits=['Coarse 2019 administrative polygons screen gross anomalies only; 50 km is an analyst review threshold, not location accuracy.',
               'Near-boundary and offshore sites still require geographic checking; no coordinates are repaired by inference.',
               'Solar thermal is explicitly held out of PV conversion; no energy profile is imputed.',
               '2025 operating status and start-year labels do not prove a full historical or 2030 fleet.',
               'Gridding preserves candidate inventory weights, not observed regional generation or turbine physics.']))
    print(json.dumps(dict(summary=summary,held_count=len(problems),candidate_grid_points=plan['unique_candidate_grid_points'],pilot_requests=len(pilots)),indent=2))


if __name__=='__main__':main()
