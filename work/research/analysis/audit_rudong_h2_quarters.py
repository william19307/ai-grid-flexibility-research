"""Audit six issuer reports and derive quarterly totals without inventing precision."""
from pathlib import Path
from decimal import Decimal as D
from pypdf import PdfReader
import csv,hashlib,json,re,subprocess
ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'outputs/research/revision/rudong_h2_quarterly'
SRC=ROOT/'work/research/sources/rudong_h2_quarterly_20260923'
ANNUAL=ROOT/'outputs/research/revision/rudong_h2_validation'
PLAN_SHA='ce972c86eb621db2a3fd7afcef71dc003ba154e7ddf8b3720586a75aaa02467f'
# Six fields per row: gross current/prior/change, export current/prior/change.
TRANSCRIPT=[('2023q1.pdf',2023,1,5,4,'海上风电',['2.07','2.19','-5.48','2.01','2.14','-5.92']),
 ('2023h1.pdf',2023,2,13,12,'风力发电（海上）',['4.24','4.55','-6.81','4.12','4.44','-7.16']),
 ('2023q3.pdf',2023,3,4,4,'海上风电',['6.01','6.58','-8.73','5.82','6.41','-9.11']),
 ('2024q1.pdf',2024,1,4,4,'海上风电',['3.34','2.07','61.35','3.18','2.01','58.21']),
 ('2024h1.pdf',2024,2,13,13,'风力发电（海上）',['5.20','4.24','22.64','4.93','4.12','19.66']),
 ('2024q3.pdf',2024,3,5,5,'海上风电',['7.50','6.01','24.79','7.13','5.82','22.51'])]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def flat(s):return re.sub(r'\s+','',s)
def writecsv(name,rows):
 with (OUT/name).open('w') as f:
  w=csv.DictWriter(f,fieldnames=rows[0],lineterminator='\n');w.writeheader();w.writerows(rows)
def main():
 assert sha(OUT/'analysis_plan.json')==PLAN_SHA
 manifest=json.loads((OUT/'source_manifest.json').read_text());records=[];checks=[]
 for name,year,q,page,header,label,values in TRANSCRIPT:
  p=SRC/name;assert sha(p)==manifest[name]['sha256']
  reader=PdfReader(p)
  assert '江苏省新能源开发股份有限公司' in flat(reader.pages[0].extract_text())
  assert str(year) in reader.pages[0].extract_text()
  layout=subprocess.check_output(['pdftotext','-layout',str(p),'-']).decode().split('\f')
  for engine,text,h in [('pypdf',reader.pages[page-1].extract_text(),reader.pages[header-1].extract_text()),('pdftotext',layout[page-1],layout[header-1])]:
   pattern=re.escape(label)+''.join(re.escape(v)+r'%?' for v in values)
   if name=='2024h1.pdf' and engine=='pdftotext':
    pattern='风力发电'+''.join(re.escape(v)+r'%?' for v in values)+'（海上）'
   assert re.search(pattern,flat(text)),(name,engine,'row mismatch')
   assert '发电量' in h and '上网电量' in h and '亿千瓦' in flat(h),(name,engine,'header')
   if q!=2:
    # Layout extraction interleaves header columns; years and periods occur
    # on separate lines. Keep both years and all four period labels explicit.
    assert f'{year}年' in flat(h) and f'{year-1}年' in flat(h)
    assert flat(h).count(f'1-{q*3}')>=4
   else:assert '本报告期' in flat(h) and '上年同期' in flat(h)
   checks.append({'file':name,'page':page,'header_page':header,'engine':engine,'energy_values':4,'percent_values':2})
  for y,offset in [(year,0),(year-1,1)]:
   records.append(dict(year=y,cumulative_quarter=q,gross_mwh=str(D(values[offset])*100000),export_mwh=str(D(values[3+offset])*100000),rounding_halfwidth_mwh=500,source_file=name,source_page=page,source_header_page=header,disclosure_year=year))
 writecsv('cumulative_disclosures.csv',records)
 unique={};duplicates=[]
 for r in records:
  key=(r['year'],r['cumulative_quarter'])
  if key in unique:
   old=unique[key]
   assert (r['gross_mwh'],r['export_mwh'])==(old['gross_mwh'],old['export_mwh']),(key,'disclosure revision; stop')
   duplicates.append({'year':key[0],'quarter':key[1],'first_source':old['source_file'],'second_source':r['source_file'],'gross_and_export_equal_at_display_precision':True})
  else:unique[key]=r
 annual_audit=json.loads((ANNUAL/'observation_audit.json').read_text())
 assert sha(ANNUAL/'annual_observations.csv')==annual_audit['output_sha256']
 with (ANNUAL/'annual_observations.csv').open() as f:
  for r in csv.DictReader(f):
   unique[(int(r['year']),4)]=dict(gross_mwh=r['gross_generation_mwh'],export_mwh=r['grid_export_mwh'],source_file=r['source_file'],source_page=r['energy_page'])
 quarters=[]
 for year in [2022,2023,2024]:
  prev={'gross_mwh':'0','export_mwh':'0','source_file':'calendar start','source_page':''}
  for q in [1,2,3,4]:
   row=unique[(year,q)]
   gross=D(row['gross_mwh'])-D(prev['gross_mwh']);export=D(row['export_mwh'])-D(prev['export_mwh'])
   assert gross>0 and 0<export<=gross
   quarters.append(dict(year=year,quarter=q,gross_mwh=str(gross),export_mwh=str(export),rounding_halfwidth_mwh=500 if q==1 else 1000,current_cumulative_source=row['source_file'],current_page=row['source_page'],previous_cumulative_source=prev['source_file'],previous_page=prev['source_page'],measurement_scope='Controlled offshore aggregate; H2 mapping remains documentary inference'))
   prev=row
  assert sum(D(r['gross_mwh']) for r in quarters if r['year']==year)==D(unique[(year,4)]['gross_mwh'])
 writecsv('quarterly_observations.csv',quarters)
 result=dict(status='PASS',plan_sha256=PLAN_SHA,source_manifest_sha256=sha(OUT/'source_manifest.json'),script_sha256=sha(Path(__file__)),checks=checks,energy_field_extractions=48,percentage_field_extractions=24,duplicate_disclosure_checks=duplicates,unique_cumulative_energy_values=18,derived_quarters=12,cumulative_sha256=sha(OUT/'cumulative_disclosures.csv'),quarterly_sha256=sha(OUT/'quarterly_observations.csv'),annual_observations_sha256=sha(ANNUAL/'annual_observations.csv'),scope='Displayed company totals and difference arithmetic, not independent meter validation. Differences share endpoints and rounding errors; no statistical confidence intervals.')
 (OUT/'observation_audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({k:result[k] for k in ['status','energy_field_extractions','percentage_field_extractions','derived_quarters','duplicate_disclosure_checks']},indent=2))
if __name__=='__main__':main()
