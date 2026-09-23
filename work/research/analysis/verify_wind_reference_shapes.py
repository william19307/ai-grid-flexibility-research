"""Scalar Decimal reconstruction from raw wind, independent of numpy interpolation."""
from pathlib import Path
from bisect import bisect_right
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import csv
import gzip
import hashlib
import json
import re

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'outputs/research/revision/wind_conversion_v1'
SRC=ROOT/'work/research/sources/wind_conversion_revision_20260923'
RAW=ROOT/'work/research/sources/weather_fleet_revision_v2/pilot'
D=Decimal


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def curve_rows(path):
    text=path.read_text()
    return [[D(x.strip()) for x in re.search(r'^'+k+r': \[([^\]]+)\]',text,re.M)[1].split(',')]
            for k in ['V','POW']]


def scalar(v,curve):
    if curve is None:
        if v<3 or v>=25:return D(0)
        return D('.85')*((v-3)/9)**3 if v<12 else D('.85')
    speeds,powers=curve
    j=bisect_right(speeds,v)-1
    if j<0 or j>=len(speeds)-1:return D(0)
    power=powers[j]+(powers[j+1]-powers[j])*(v-speeds[j])/(speeds[j+1]-speeds[j])
    return D('.85')*power/max(powers)


def main():
    audit=json.loads((OUT/'comparison_audit.json').read_text())
    assert sha(OUT/'conversion_plan.json')==audit['plan_sha256']=='0e63f094829af82f8545a4954880bd75e9bc7ec73b3ddaa6b10e35097ef083e0'
    assert sha(ROOT/'work/research/analysis/compare_wind_reference_shapes.py')==audit['builder_sha256']
    assert sha(OUT/'source_manifest.json')==audit['source_manifest_sha256']
    assert sha(ROOT/audit['output_path'])==audit['output_sha256']
    assert sha(OUT/'shape_comparison.csv')==audit['summary_sha256']
    manifest=json.loads((OUT/'source_manifest.json').read_text())
    curves={'legacy_generic':None}
    for name in ['Vestas_V112_3MW.yaml','NREL_ReferenceTurbine_5MW_offshore.yaml']:
        assert sha(SRC/name)==manifest[name]['sha256']
        curves[name.removesuffix('.yaml')]=curve_rows(SRC/name)
    with gzip.open(ROOT/audit['output_path'],'rt') as f:output=list(csv.DictReader(f))
    assert len(output)==8784
    start=datetime(2020,1,1,tzinfo=timezone(timedelta(hours=8)))
    assert all(datetime.fromisoformat(r['interval_start_local'])==start+timedelta(hours=i)
               for i,r in enumerate(output))
    checks=0;maximum=D(0);summary_checks=0
    expected_columns=set()
    for source in audit['weather_sources']:
        raw=RAW/(source['request_id']+'.json')
        assert sha(raw)==source['raw_sha256'] and sha(raw.with_suffix('.meta.json'))==source['meta_sha256']
        data=json.loads(raw.read_text(),parse_float=D,parse_int=D)
        wind=data['hourly']['wind_speed_100m'][:8785]
        for name,curve in curves.items():
            col=source['group']+'|'+name;expected_columns.add(col)
            endpoints=[scalar(v,curve) for v in wind]
            expected=[(a+b)/2 for a,b in zip(endpoints[:-1],endpoints[1:])]
            for r,value in zip(output,expected):
                error=abs(D(r[col])-value);maximum=max(maximum,error);checks+=1
                assert error<D('1e-12')
            matches=[r for r in audit['results'] if r['group']==source['group'] and r['curve']==name]
            assert len(matches)==1
            assert abs(D(str(matches[0]['equivalent_hours']))-sum(expected))<D('1e-8')
            summary_checks+=1
    assert set(output[0])-{'interval_start_local'}==expected_columns and len(expected_columns)==12
    # Check production handling of duplicate cut-in/cut-out knots against the
    # independent right-continuous scalar function at/around every curve knot.
    from compare_wind_reference_shapes import convert,read_curve
    boundary_checks=0
    for name,curve in curves.items():
        production_curve=read_curve(SRC/(name+'.yaml')) if curve else None
        knots=curve[0] if curve else [D(0),D(3),D(12),D(25)]
        for knot in sorted(set(knots)):
            for delta in [D('-.000001'),D(0),D('.000001')]:
                speed=knot+delta
                if speed<0:continue
                actual=float(convert([float(speed)],production_curve)[0])
                assert abs(D(str(actual))-scalar(speed,curve))<D('1e-12')
                boundary_checks+=1
    result=dict(status='PASS',independent_hourly_values=checks,max_absolute_error=str(maximum),
                independent_energy_sums=summary_checks,synthetic_knot_checks=boundary_checks,
                analysis_sha256=sha(OUT/'comparison_audit.json'),verifier_sha256=sha(Path(__file__)),
                scope='Verifies conversion arithmetic and temporal indexing, not physical accuracy or observed generation.')
    (OUT/'independent_verification.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
