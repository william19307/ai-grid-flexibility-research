"""Read-only source qualification and audit of the historical peak sensitivity."""
from pathlib import Path
from html.parser import HTMLParser
from decimal import Decimal
import hashlib
import html
import json
import re
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / 'work/research/sources/load_scope_20260923'
OUT = ROOT / 'outputs/research/revision/load_scope'
OUT.mkdir(parents=True, exist_ok=True)
checks = []
source_hashes = {}
def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()
class Text(HTMLParser):
    def __init__(self):
        super().__init__(); self.parts = []
    def handle_data(self, value):
        self.parts.append(value)
def compact(s):
    return re.sub(r'\s+', '', s)
def source(filename, fragments):
    path = SRC / filename; raw = path.read_text()
    parser = Text(); parser.feed(raw)
    one = compact(''.join(parser.parts))
    two = compact(html.unescape(re.sub(r'<[^>]*>', '', raw)))
    for text in fragments:
        assert compact(text) in one and compact(text) in two, (filename, text)
        checks.append(filename + ':' + text)
    source_hashes[str(path.relative_to(ROOT))] = sha(path)

source('js_2020_nov.html', ['2020-12-10', '本年度全省统调最高用电负荷11512.49万千瓦', '1-11月累计全社会用电量5730.26亿千瓦时'])
source('js_peak_aug_nea.html', ['2020-08-21', '8月17日13点25分', '统调最高用电负荷11512万千瓦'])
source('gs_peak_2022_nea.html', ['2022-09-05', '最高达1953万千瓦（7月9日）', '同比增长2.93%'])
source('gz_peak_2026_nea.html', ['2026-01-21', '1月4日达到历史最高值2955.3万千瓦'])
source('js_2025_dec.html', ['2026-01-16', '年累计全社会用电量8895.41亿千瓦时', '本年调度用电最高负荷14405.50万千瓦'])
observations = [
    dict(province='Jiangsu', period='2020-01/2020-11', value_MW=115124.9, measure='reported_dispatch_peak',
         source='js_2020_nov.html', scope='统调；year-to-date, not independently established full-year value', admitted_as_hourly_shape_target=False),
    dict(province='Jiangsu', period='2020-08-17 13:25 local', value_MW=115120., measure='reported_dispatch_peak_event',
         source='js_peak_aug_nea.html', scope='time-stamped event; not established hourly average', admitted_as_hourly_shape_target=False),
    dict(province='Gansu', period='2022-07-09', value_MW=19530., measure='reported_provincial_peak',
         source='gs_peak_2022_nea.html', scope='2022 summer; not a 2020 annual observation', admitted_as_hourly_shape_target=False),
    dict(province='Guizhou', period='2026-01-04', value_MW=29553., measure='reported_dispatch_peak',
         source='gz_peak_2026_nea.html', scope='2026 dispatch boundary; not 2020 all-society hourly load', admitted_as_hourly_shape_target=False),
    dict(province='Jiangsu', period='2025 annual', value_MW=144055., measure='reported_dispatch_peak',
         source='js_2025_dec.html', scope='2025 dispatch peak; different year and time resolution from legacy hourly shape', admitted_as_hourly_shape_target=False),
]
pd.DataFrame(observations).to_csv(OUT / 'qualified_peak_observations.csv', index=False, lineterminator='\n')
array_path = ROOT / 'work/research/prepared/load_2020_annual_anchored_hourly_shape_UNVALIDATED.npz'
growth_path = ROOT / 'work/research/sources/zenodo_13987282/selected/data/load/Province_Load_2020_2060.csv'
a = np.load(array_path, allow_pickle=False)
clock = pd.to_datetime(a['timestamps_UTC_ns'], utc=True).tz_convert('Asia/Shanghai')
assert clock.equals(pd.date_range('2020-01-01', periods=8784, freq='h', tz='Asia/Shanghai', unit='ns'))
growth = pd.read_csv(growth_path, index_col=0)
descriptive = []
for p in ['Jiangsu', 'Gansu', 'Guizhou']:
    i = list(a['provinces']).index(p); v = a['load_MW'][:, i]
    year20 = float(v.sum()/1e6); ratio = float(growth.loc[p, '2030']/growth.loc[p, '2020'])
    reference = Decimal(str(a['annual_targets_TWh'][i])) * Decimal(str(growth.loc[p, '2030'])) / Decimal(str(growth.loc[p, '2020']))
    assert abs(float(reference) - year20*ratio) < 1e-9
    descriptive.append(dict(province=p, year2020_annual_TWh=year20, reconstructed_hourly_peak_MW=float(v.max()),
        legacy_2030_background_TWh=year20*ratio, legacy_2030_hourly_peak_MW=float(v.max()*ratio),
        admission='CONDITIONAL_SCENARIO_NOT_VALIDATED_CURRENT_OUTLOOK'))
checks.append('three_province_annual_growth_independent_decimal_reconstruction')
pd.DataFrame(descriptive).to_csv(OUT / 'legacy_load_descriptive.csv', index=False, lineterminator='\n')
js = next(x for x in descriptive if x['province']=='Jiangsu')
actual2025 = float(Decimal('8895.41')/10)
outlook = dict(province='Jiangsu', official2025_all_society_TWh=actual2025,
    legacy2030_background_TWh=js['legacy_2030_background_TWh'],
    background_below_observed2025_percent=100*(1-js['legacy_2030_background_TWh']/actual2025),
    gap_TWh=actual2025-js['legacy_2030_background_TWh'],
    comparison='Model background only, before separately added AI. Same all-society anchor concept, unresolved treated-cohort boundary.',
    inference='Old 2030 background is below already observed 2025 use; justify scenario and cohort or revise outlook. Not an error estimate for total model demand.')
(OUT / 'jiangsu_2030_outlook_check.json').write_text(json.dumps(outlook, ensure_ascii=False, indent=2)+'\n')

# Pair immutable historical outputs. Do not import/run the old solver wrapper.
rows = []
for adjusted_path in sorted((ROOT / 'outputs/research/tables').glob('regional_2030_*_pk.json')):
    base_path = adjusted_path.with_name(adjusted_path.name.replace('_pk.json', '.json'))
    assert base_path.exists()
    adjusted = json.loads(adjusted_path.read_text()); base = json.loads(base_path.read_text())
    m, b = adjusted['meta'], base['meta']; ma, ba = m['assumptions'], b['assumptions']
    assert m['province'] == b['province'] and ma['ai_share_of_peak'] == ba['ai_share_of_peak']
    assert ma['peak_target_2020'] is not None and ba['peak_target_2020'] is None
    ratio = m['peak_2030_mw']/b['peak_2030_mw']
    ai_ratio = ma['ai_nameplate_mw']/ba['ai_nameplate_mw']
    energy_ratio = adjusted['results']['S0']['ai_mwh']/base['results']['S0']['ai_mwh']
    assert abs(ratio-ai_ratio)<1e-10 and abs(ratio-energy_ratio)<1e-10
    assert m['ai_work_pool_hours'] == b['ai_work_pool_hours']
    rows.append(dict(province=m['province'], ext_mode=ma['ext_mode'], export=ma['export'], ai_share=ma['ai_share_of_peak'],
        adjusted_file=str(adjusted_path.relative_to(ROOT)), base_file=str(base_path.relative_to(ROOT)),
        target2020_MW=ma['peak_target_2020'], base_peak2030_MW=b['peak_2030_mw'], adjusted_peak2030_MW=m['peak_2030_mw'],
        base_AI_nameplate_MW=ba['ai_nameplate_mw'], adjusted_AI_nameplate_MW=ma['ai_nameplate_mw'],
        AI_nameplate_change_percent=100*(ai_ratio-1), rigid_AI_energy_change_percent=100*(energy_ratio-1),
        normalized_work_equal=True, interpretation='LOAD_SHAPE_AND_AI_ELECTRICAL_SCALE_CHANGE_TOGETHER_NOT_ISOLATED_SHAPE_EFFECT'))
    for path in [adjusted_path, base_path]:source_hashes[str(path.relative_to(ROOT))]=sha(path)
assert len(rows)==8
checks.append('eight_frozen_peak_pairs_show_proportional_AI_nameplate_and_rigid_energy_change')
pd.DataFrame(rows).to_csv(OUT/'peak_sensitivity_scale_audit.csv', index=False, lineterminator='\n')
for path in [array_path, growth_path, ROOT/'outputs/research/tables/provincial_peak_load_plausibility_check.csv',
             ROOT/'work/research/analysis/run_regional_2030_s0_s3.py',
             ROOT/'outputs/research/manuscript/core_paper_en_v1.4.md', ROOT/'outputs/research/manuscript/supplementary_information_v1.4.md']:
    source_hashes[str(path.relative_to(ROOT))]=sha(path)
report=dict(date='2026-09-23',checks=checks,number_of_checks=len(checks),source_pages=5,peak_observations=5,
    admissible_same_scope_hourly_peak_targets=0,paired_legacy_sensitivity_cases=8,
    actual_new_dispatch_runs=0,limitation='Source and input audit only. No new calibrated load or provincial outcome.')
(OUT/'audit_summary.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
(OUT/'source_hashes.json').write_text(json.dumps(source_hashes,ensure_ascii=False,indent=2)+'\n')
logs=[]
for name in ['download_log.json','download_supplement.json']:logs.extend(json.loads((SRC/name).read_text()))
(OUT/'source_access_log.json').write_text(json.dumps(logs,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(dict(report=report,outlook=outlook,scale_changes=[(r['province'],r['ai_share'],r['AI_nameplate_change_percent']) for r in rows]),ensure_ascii=False,indent=2))
