"""Audit disclosed annual scope; never infer unit dispatch from corporate ratios."""
from pathlib import Path
from decimal import Decimal
import argparse,csv,hashlib,json,re
from html.parser import HTMLParser
import pypdf,pdfplumber
ROOT=Path(__file__).resolve().parents[3]
parser=argparse.ArgumentParser();parser.add_argument('--output-dir',type=Path,default=ROOT/'outputs/research/revision/captive_operating');args=parser.parse_args()
OUT=args.output_dir;OUT.mkdir(parents=True,exist_ok=True)
SOURCE=ROOT/'work/research/sources/nangang_operating_20260923'
expected={'sustainability_2025.pdf':'21b440dae39a31b438b22ca01fe85e7f8b624b7283ec39aace6a78b00c2dd951','csm_grid_202608.html':'b6392e2e074e924732fad5896661bd06b0a8f8d001f48c5720b3cc347bdda39a'}
expected['issuer_sustainability_2025.pdf']='0e2d069526583bc28fb5974791f2a37a1c60384a61cebff3c4208698780f434e'
checks=[]
def check(condition,label):
    if not condition:raise AssertionError(label)
    checks.append(label)
def compact(s):return re.sub(r'\s+','',s)
for name,digest in expected.items():check(hashlib.sha256((SOURCE/name).read_bytes()).hexdigest()==digest,'source_hash:'+name)
r=pypdf.PdfReader(SOURCE/'sustainability_2025.pdf')
issuer=pypdf.PdfReader(SOURCE/'issuer_sustainability_2025.pdf')
check(len(r.pages)==75 and len(issuer.pages)==73,'pdf_version_page_counts')
page_pairs=[{'issuer_page':i+1,'exchange_page':i+2,'normalized_text_equal':compact(page.extract_text())==compact(r.pages[i+1].extract_text())} for i,page in enumerate(issuer.pages)]
check(all(p['normalized_text_equal'] for p in page_pairs),'issuer_exchange_all_73_text_pages_aligned')
image_checks=[]
for page_number in [4,33,66,72,73]:
    hashes=lambda p:[hashlib.sha256(im.data).hexdigest() for im in p.images]
    image_checks.append(dict(exchange_page=page_number,issuer_page=page_number-1,image_payload_hashes_equal=hashes(r.pages[page_number-1])==hashes(issuer.pages[page_number-2])))
check(all(p['image_payload_hashes_equal'] for p in image_checks),'issuer_exchange_reviewed_page_images')
(OUT/'source_version_comparison.json').write_text(json.dumps(dict(exchange_pages=75,issuer_pages=73,page_pairs=page_pairs,reviewed_page_images=image_checks,scope='Whitespace-normalized text and selected embedded image payloads; not whole-document byte or pixel equality'),indent=2)+'\n')
text=r.pages[65].extract_text()
with pdfplumber.open(SOURCE/'sustainability_2025.pdf') as p:
    page=p.pages[65];second=page.crop((page.width/2,0,page.width,page.height)).extract_text()
    scope_second=p.pages[3].extract_text();ratio_second=p.pages[32].extract_text()
metrics=[
 ('photovoltaic_capacity','－光伏','兆瓦',['55','55','55']),
 ('renewable_consumption','可再生能源消耗量','兆瓦时',['627,590','643,782','64,761']),
 ('self_generated_green_consumption','－自发绿电','兆瓦时',['27,590','43,782','40,421']),
 ('purchased_green_consumption','－外购绿电','兆瓦时',['600,000','600,000','24,340']),
 ('direct_energy_consumption','直接能源消耗总量','吨标准煤',['5,601,280','5,745,641.75','5,859,721.58']),
 ('indirect_energy_consumption','间接能源消耗总量','吨标准煤',['281,438.05','282,121.98','235,020.61']),
 ('electricity_consumption','电力消耗总量','兆瓦时',['5,027,023.85','4,849,493.38','4,984,250.57']),
 ('total_energy_consumption','能源消耗总量','吨标准煤',['5,882,717.78','6,027,763.73','6,094,742.19']),
]
rows=[];values={}
for key,label,unit,numbers in metrics:
    expected_line=compact(label+unit+''.join(numbers))
    for engine,t in [('pypdf',text),('pdfplumber',second)]:
        check(expected_line in compact(t),engine+':'+key)
    values[key]=[Decimal(n.replace(',','')) for n in numbers]
    for year,value,reported in zip([2023,2024,2025],values[key],numbers):
        rows.append(dict(metric=key,reported_label=label,year=year,value=str(value),reported_value=reported,
                         unit=unit,scope='steel_business',source='sustainability_2025.pdf',pdf_page=66,printed_page=126,
                         evidence='issuer_annual_disclosure_not_meter_trace',dispatch_admitted=False))
for engine,t in [('pypdf',text),('pdfplumber',second)]:check('环境数据的统计范畴为钢铁业务' in compact(t),engine+':steel_business_footnote')
for engine,t in [('pypdf',r.pages[3].extract_text()),('pdfplumber',scope_second)]:
    check('南京钢铁股份有限公司及其附属公司' in compact(t),engine+':general_report_scope')
for engine,t in [('pypdf',r.pages[32].extract_text()),('pdfplumber',ratio_second)]:
    check('实际自发电比例达60.9%' in compact(t) and '目标为56.4%' in compact(t),engine+':target_actual_distinction')
arithmetic=[]
def half_last_digit(value):return Decimal(1).scaleb(value.as_tuple().exponent)/2
for i,year in enumerate([2023,2024,2025]):
    green=values['self_generated_green_consumption'][i]+values['purchased_green_consumption'][i]-values['renewable_consumption'][i]
    check(green==0,'green_subtotal:'+str(year))
    a,b,c=(values[k][i] for k in ['direct_energy_consumption','indirect_energy_consumption','total_energy_consumption'])
    residual=a+b-c;limit=sum(map(half_last_digit,[a,b,c]))
    check(abs(residual)<=limit,'energy_rounding_interval:'+str(year))
    arithmetic.append(dict(year=year,green_subtotal_residual_mwh=str(green),direct_plus_indirect_minus_total_tce=str(residual),
                           maximum_rounding_discrepancy_tce=str(limit),rounding_rule='nearest last reported digit; deterministic interval, not confidence interval'))
class Extract(HTMLParser):
    def __init__(self):super().__init__();self.parts=[]
    def handle_data(self,s):self.parts.append(s)
h=Extract();h.feed((SOURCE/'csm_grid_202608.html').read_text());htmltext=compact(' '.join(h.parts))
for label,phrase in [('source_attribution','信息来源：南京钢铁股份有限公司'),('pv_unit_as_reported','55MWh'),('annual_shift_as_reported','8000千瓦时'),('storage_nameplate','61MW/123MWh')]:
    check(phrase in htmltext,'csm:'+label)
with (OUT/'annual_energy_disclosures.csv').open('w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
(OUT/'arithmetic_checks.json').write_text(json.dumps(arithmetic,indent=2,ensure_ascii=False)+'\n')
report=dict(check_count=len(checks),checks=checks,annual_numeric_cells=len(rows),qualified_hourly_site_records=0,
            qualified_captive_parameter_sets=0,scope='Source reading, declared boundary and arithmetic only',
            versions={'pypdf':pypdf.__version__,'pdfplumber':pdfplumber.__version__})
(OUT/'validation.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
(OUT/'evidence_manifest.json').write_text(json.dumps({'sources':expected,'auditor_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    'visual_review_pdf_pages':[4,33,66,72,73],'assurance_review':'Human full-page visual reading; assurance body is an image, not double-engine text',
    'boundary':'Annual steel-business metrics; no gross/net unit meter or hourly interface identified'},indent=2,ensure_ascii=False)+'\n')
print(json.dumps(report,indent=2,ensure_ascii=False))
