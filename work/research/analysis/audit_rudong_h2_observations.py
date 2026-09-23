"""Preserve annual reported offshore observations and their reporting boundaries."""
from pathlib import Path
from decimal import Decimal
from pypdf import PdfReader
import csv,hashlib,json,re,subprocess

ROOT=Path(__file__).resolve().parents[3]
SRC=ROOT/'work/research/sources/rudong_h2_observations_20260923'
OUT=ROOT/'outputs/research/revision/rudong_h2_validation'
# Manual transcription after reading the source pages; automatically compared
# against two independent PDF extractors, not asserted to be raw meter records.
TRANSCRIPT=[(2022,11,31,'8.55','8.31','2443','94.38'),
            (2023,10,27,'8.58','8.32','2452','96.47'),
            (2024,10,28,'10.29','9.80','2940','98.22')]


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def flat(t):return re.sub(r'\s+','',t).replace(',','')


def main():
    OUT.mkdir(exist_ok=True,parents=True)
    rows=[];checks=[];manifest={}
    for year,ep,hp,generation,export,util,availability in TRANSCRIPT:
        path=SRC/f'annual{year}.pdf';m=json.loads(path.with_suffix('.pdf.meta.json').read_text())
        assert sha(path)==m['sha256'];manifest[path.name]=m
        reader=PdfReader(path)
        pages=subprocess.check_output(['pdftotext','-layout',str(path),'-']).decode().split('\f')
        for engine,texts in [('pypdf',[reader.pages[n-1].extract_text() for n in [ep,hp]]),
                             ('pdftotext',[pages[n-1] for n in [ep,hp]])]:
            energy,height=[flat(t) for t in texts]
            if engine=='pypdf':
                offshore=texts[0].split('（海上）',1)[1].split('光伏',1)[0]
            else:
                offshore=texts[0].split('（海上）',1)[0].rstrip().splitlines()[-1]
            nums=re.findall(r'\d+\.\d+',offshore)
            assert nums[0]==generation and export in nums[:4],(year,engine,nums)
            assert '海上风电发电平均利用小时'+util+'小时' in height
            assert '海上风机可利用率'+availability+'%' in height
            checks.append(dict(year=year,engine=engine,pages=[ep,hp],numeric_fields=4))
        # All report definitions say availability is a time fraction, not an
        # energy-weighted loss fraction; do not apply it as an hourly multiplier.
        definition=flat(reader.pages[4].extract_text())
        assert '统计期内机组处于可用状态的时间占总时间的比例' in definition
        g=Decimal(generation)*100000;n=Decimal(export)*100000
        capacity=Decimal(350);precision=Decimal(500)
        implied=(g-precision)/capacity,(g+precision)/capacity
        reported=Decimal(util)-Decimal('.5'),Decimal(util)+Decimal('.5')
        assert max(implied[0],reported[0])<=min(implied[1],reported[1])
        rows.append(dict(year=year,source_file=path.name,energy_page=ep,utilization_page=hp,
            source_scope='Company controlled offshore wind; H2 mapping supported by 2022 full-commissioning note and unchanged wind fleet, distinct from equity-accounted Binhai',
            proposed_gem_unit_id='G100000903072',matched_capacity_mw='350',
            gross_generation_mwh=str(g),grid_export_mwh=str(n),
            reported_generation_utilization_hours=util,time_availability_pct=availability,
            energy_reporting_rounding_halfwidth_mwh='500',
            gross_minus_export_mwh=str(g-n),export_to_generation_ratio=str(n/g),
            rounding_consistency_with_350mw=True,
            admission='Annual aggregate validation candidate; not hourly metering or provincial validation'))
    # Capacity boundary and full-commissioning source; distinct from 2021 partial year.
    commissioning=flat(PdfReader(SRC/'annual2022.pdf').pages[10].extract_text())
    assert '如东H2#海上风电35万千瓦项目全容量并网' in commissioning
    assert '2021年12月' in commissioning
    with (OUT/'annual_observations.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
    result=dict(source_manifest=manifest,checks=checks,numeric_values=12,
        extracted_values_across_two_engines=24,definition_checks=3,
        capacity_rounding_consistency_checks=3,
        script_sha256=sha(Path(__file__)),output_sha256=sha(OUT/'annual_observations.csv'),
        source_scope_limit='Controlled offshore totals; mapping is documentary inference, not a directly labelled plant meter series.',
        boundaries=['Gross generation and grid export are separate observations.',
                    'Gross-minus-export cannot identify electrical losses versus other accounting components.',
                    'Time availability is not energy availability; no flat correction is inferred.',
                    'Annual/quarterly totals cannot validate hourly ramping, tails or reliability.',
                    'All three annual observations have been examined; temporal tests will not be described as blind holdout.'])
    (OUT/'observation_audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(dict(years=3,numeric_values=12,engine_checks=24,rounding_checks=3),indent=2))


if __name__=='__main__':main()
