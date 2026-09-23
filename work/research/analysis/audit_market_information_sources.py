"""Audit acquired primary rules; do not invent historical forecast observations."""
from pathlib import Path
import re,json,hashlib,csv
from pypdf import PdfReader
ROOT=Path(__file__).resolve().parents[3]
SRC=ROOT/'work/research/sources/market_information_20260923'
OUT=ROOT/'outputs/research/revision/market_information';OUT.mkdir(parents=True,exist_ok=True)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def compact(t):return re.sub(r'\s+','',t)
raw=SRC/'national_disclosure_nea.doc';mirror=SRC/'national_disclosure.doc'
expected='6aaf7a70f9a2c3b2f9b9f1f9f5c7babcfa5689ed9aa447c990f46720e3c87d82'
assert sha(raw)==sha(mirror)==expected
assert raw.read_bytes()[:8]==bytes.fromhex('d0cf11e0a1b11ae1')
text=(SRC/'national_disclosure.txt').read_text()
pdf=SRC/'render/cjk/national_disclosure_nea.pdf';pages=PdfReader(pdf).pages
pdftext='\n'.join(p.extract_text() for p in pages)
phrases=['披露的信息保留或可供查询的时间不少于2年','预测类信息在交易申报开始前披露','运行类信息在运行日次日披露','公众信息：是指向社会公众披露的信息','公开信息：是指向有关市场成员披露的信息','特定信息：是指根据电力市场运营需要向特定市场成员披露的信息']
checks=[]
for phrase in phrases:
    assert compact(phrase) in compact(text) and compact(phrase) in compact(pdftext),phrase
    checks.append('cross_engine_principle_'+str(len(checks)+1))
fields=[
('6.36','系统负荷预测','月','省内'),('6.37','系统负荷预测','周、日','省内'),
('6.38','电力电量供需平衡预测','月','省内'),('6.39','电力电量供需平衡预测','日','省内'),
('6.40','各电网电力平衡预测','月','省间'),('6.41','省间联络线输电曲线预测','日前、日内','省内'),
('6.42','发电总出力预测','日','省间、省内'),('6.43','非市场机组总出力预测','日','省间、省内'),
('6.44','新能源总出力预测','周、日','省内'),('6.45','水电（含抽蓄）总出力预测','周、日','省间、省内')]
rows=[]
for code,label,period,market in fields:
    after='6.'+str(int(code.split('.')[1])+1)
    chunks=[doc.split(code,1)[1].split(after,1)[0] for doc in [text,pdftext]]
    for chunk in chunks:
        c=compact(chunk)
        assert period in c and '公开' in c and market in c and '电力调度机构' in c,(code,c)
        if code not in ['6.37','6.39']:assert compact(label) in c,(code,c)
    rows.append(dict(rule_item=code,series_label=label,disclosure_period=period,access_scope='公开（有关市场成员）',market=market,
        merged_label_from_previous_row=code in ['6.37','6.39'],is_observed_forecast=False))
    checks.append('cross_engine_table_'+code)
with (OUT/'required_forecast_fields.csv').open('w') as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
html=(SRC/'jiangsu_disclosure_202606.html').read_text()
for phrase in ['96点潮流信息','日清分数据变化情况信息','调整后及时披露','修改计划机组出力','2026年6月30日']:
    assert phrase in compact(re.sub('<[^>]+>','',html)),phrase
    checks.append('jiangsu_notice_'+phrase)
manifest=[]
for filename in ['download_manifest.json','download_supplement.json']:
    manifest.extend(json.loads((SRC/filename).read_text()))
manifest.append(json.loads((SRC/'national_disclosure_nea.source.json').read_text()))
report=dict(date='2026-09-23',status='PRIMARY_RULES_VERIFIED_NO_EMPIRICAL_FORECASTS',checks=checks,number_of_checks=len(checks),
    national_rule='国能发监管〔2024〕9号',official_notice='https://zfxxgk.nea.gov.cn/2024-01/31/c_1310763726.htm',
    original_word_urls=['https://zfxxgk.nea.gov.cn/1310763726_17072197518981n.doc','https://www.gov.cn/zhengce/zhengceku/202402/P020240207399607172280.doc'],
    original_copies_byte_identical=True,raw_word_sha256=expected,
    rendered_pages_visually_checked=[2,3,27,28],rendered_page_numbers_are_conversion_specific=True,
    extraction=['macOS textutil from original DOC','pypdf from locally rendered original DOC with explicit system CJK font configuration'],
    rendering_failure_and_fix='Initial default font configuration lost Chinese glyphs; rejected. Original DOC unchanged; explicit font configuration produced readable checked pages.',
    empirical_forecast_curves_acquired=0,empirical_forecast_curves_admitted=0,
    source_files_sha256={str(p.relative_to(ROOT)):sha(p) for p in [raw,mirror,SRC/'national_disclosure.txt',pdf,SRC/'render/fonts.conf',SRC/'jiangsu_disclosure_202606.html',Path(__file__)]},
    limitations=['Disclosure obligation is not evidence of actual publication time or availability of every historical version','Source access or network failures do not prove data do not exist','These rules do not establish provincial rule-version applicability for each historical delivery day','No observed forecast accuracy or operational mechanism gain is computed'])
(OUT/'source_audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
(OUT/'source_attempts.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:report[k] for k in ['status','number_of_checks','empirical_forecast_curves_acquired','empirical_forecast_curves_admitted']},ensure_ascii=False,indent=2))
