"""Independent Decimal re-extraction without importing the stage-38 extractor."""
import csv,json,re
from decimal import Decimal
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'outputs/research/revision/mlperf_power_corrected'
SRC=ROOT/'work/tmp/mlperf-inference-v40/closed/NVIDIA/results/DGX-H100_H100-SXM-80GBx8_TRT_MaxQ'
rows=list(csv.DictReader((OUT/'matched_results.csv').open()))
assert len(rows)==24 and len({(r['benchmark'],r['scenario']) for r in rows})==24
checks=[]
for r in rows:
    p=SRC/r['benchmark']/r['scenario']/'performance/run_1'
    # Source dates are all in one month/year. Reorder their fixed-width fields
    # to ISO strings for a separate, non-datetime window implementation.
    def ordered(s):
        return s[6:10]+'-'+s[:2]+'-'+s[3:5]+'T'+s[11:]
    log=(p/'mlperf_log_detail.txt').read_text()
    begin=re.search(r'"key": "power_begin", "value": "([^"]+)"',log).group(1)
    end=re.search(r'"key": "power_end", "value": "([^"]+)"',log).group(1)
    vals=[Decimal(x.split(',')[3]) for x in (p/'spl.txt').read_text().splitlines()
          if x.strip() and ordered(begin)<=ordered(x.split(',')[1])<=ordered(end)]
    mean=sum(vals)/len(vals)
    assert abs(mean-Decimal(r['window_ac_sample_mean_w'])) < Decimal('0.000000001')
    assert len(vals)==int(r['window_samples'])
    if r['benchmark'] in ('dlrm-v2-99.9','llama2-70b-99.9'):
        assert int(r['gpu_power_limit_w_each'])==450
    assert r['standard_ac_power_status']=='not_submitted'
    assert r['whole_node_energy_saving_computable']=='False'
    checks.append(r['benchmark']+'/'+r['scenario'])
result=dict(status='pass',independently_recomputed_rows=len(checks),checks=checks,
    tolerance_w=1e-9, scope='Window sample arithmetic and four corrected cap values; not hardware or accuracy certification')
(OUT/'independent_verification.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
