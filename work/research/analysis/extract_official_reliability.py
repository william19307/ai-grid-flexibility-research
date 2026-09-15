"""Extract selected clearly labelled aggregate tables, not event telemetry."""
from pathlib import Path
import re,json,hashlib
import pandas as pd
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'outputs/research/tables'
pdf=ROOT/'work/research/sources/papers/nea_2020_power_statistics.pdf'
text=pdf.with_suffix('.txt').read_text()
url='https://prpq.nea.gov.cn/uploads/file1/20211009/616107fe94a8e.pdf'
section=text.split('表 2-5  2016-2020 年 600 兆瓦等级燃煤机组主要可靠性指标')[1].split('PAGE 21')[0]
rows=[]
for line in section.splitlines():
    a=line.split()
    if len(a)==6 and a[0] in ['2016','2017','2018','2019','2020']:
        rows.append(dict(year=int(a[0]),unit_count=int(a[1]),operating_factor_pct=float(a[2]),
           equivalent_availability_factor_pct=float(a[3]),equivalent_forced_outage_rate_pct=float(a[4]),
           unplanned_events_per_unit_year=float(a[5]),source_raw_row=line,
           source_pdf_page_1based=20,source_printed_page=14,source_table='2-5',source_url=url))
assert len(rows)==5 and rows[-1]['unit_count']==548
pd.DataFrame(rows).to_csv(OUT/'nea_600MW_coal_reliability_2016_2020.csv',index=False)
section=text.split('表 2-29  2020 年各地区 100 兆瓦及以上容量燃煤机组运行可靠性指标')[1].split('图 2-25')[0]
regions=[]
for line in section.splitlines():
    a=line.split()
    if len(a)==7 and a[0] in ['华北','东北','华东','华中','西北','南方','全部']:
        regions.append(dict(region=a[0],unit_count=int(a[1]),mean_unit_capacity_MW=float(a[2]),
           annual_generation_MWh_per_kW=float(a[3]),operating_factor_pct=float(a[4]),
           equivalent_availability_factor_pct=float(a[5]),unplanned_events_per_unit_year=float(a[6]),
           source_raw_row=line,source_pdf_page_1based=39,source_printed_page=33,source_table='2-29',source_url=url))
assert len(regions)==7 and sum(x['unit_count'] for x in regions[:-1])==regions[-1]['unit_count']==1865
pd.DataFrame(regions).to_csv(OUT/'nea_regional_coal_reliability_2020.csv',index=False)
section=text.split('表 2-28  2020 年非计划停运事件按持续时间划分表')[1].split('备注：')[0]
durations=[]
for line in section.splitlines():
    a=line.split()
    if len(a)==3 and a[0] in ['<10','10-100','100-500','500-1000','1000']:
        durations.append(dict(source_duration_bin=a[0],unplanned_event_count=int(a[1]),percentage=float(a[2]),
           source_raw_row=line,source_pdf_page_1based=38,source_printed_page=32,source_table='2-28',source_url=url))
assert len(durations)==5 and sum(x['unplanned_event_count'] for x in durations)==906
assert abs(sum(x['percentage'] for x in durations)-100)<.02
pd.DataFrame(durations).to_csv(OUT/'nea_unplanned_outage_duration_bins_2020.csv',index=False)
summary={'status':'official_aggregate_targets_extracted_not_hourly_failure_process',
    'source_title':'2020 年全国电力可靠性年度报告','publisher':'国家能源局、中国电力企业联合会','publication':'2021-08',
    'source_url':url,'sha256':hashlib.sha256(pdf.read_bytes()).hexdigest(),
    'tables':{'2-5':len(rows),'2-29':len(regions),'2-28':len(durations)},
    'manual_visual_review':{'date':'2026-09-14','pdf_pages_1based':[20,38,39],'result':'table values and headings checked against rendered source pages'},
    'checks':['600MW five yearly rows','six regional counts sum to 1865','unplanned duration counts sum to 906','duration percentages sum to 100'],
    'interpretation_limits':['operating factor, equivalent availability and equivalent forced outage rate are distinct measures',
       'unplanned outage distribution includes more than forced outages; cannot use as forced-only duration distribution',
       'aggregate rates do not identify serial correlation, weather dependence or a unique Markov process',
       'source unit-year exposure definitions and subset coverage need reconciliation before rate fitting',
       'regional table covers six grid regions, not province-level outage telemetry',
       'last duration bin visually prints 1000; narrative says above 1000; exact endpoint convention retained as unresolved'],
    'next_reliability_work':'use as calibration targets; derive and stress-test explicitly assumed transition model only after exposure definitions are verified'}
(OUT/'official_reliability_source_audit.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2))
print(json.dumps(summary,ensure_ascii=False,indent=2))
