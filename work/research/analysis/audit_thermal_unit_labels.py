"""Read OOXML cell values/styles to distinguish date labels from known unit IDs."""
from pathlib import Path
from datetime import datetime,timedelta
from decimal import Decimal
import argparse,csv,hashlib,json,posixpath,re,zipfile,xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[3]
parser=argparse.ArgumentParser();parser.add_argument('--output-dir',type=Path,default=ROOT/'outputs/research/revision/thermal_technology');args=parser.parse_args()
OUT=args.output_dir;OUT.mkdir(parents=True,exist_ok=True)
raw_rel='work/research/sources/zenodo_16810831/Global-integrated-Plant-Tracker-July-2025_china.xlsx'
expected=json.loads((ROOT/'outputs/research/revision/input_consistency/source_hashes.json').read_text())[raw_rel]
raw=ROOT/raw_rel
if hashlib.sha256(raw.read_bytes()).hexdigest()!=expected:raise ValueError('Unreviewed workbook version')
with (ROOT/'outputs/research/revision/input_consistency/selected_oil_gas_unit_audit.csv').open(newline='') as f:rows=list(csv.DictReader(f))
wanted={r['GEM unit/phase ID']:r for r in rows if re.fullmatch(r'\d{4}-\d{2}-\d{2} 00:00:00',r['Unit / Phase name'])}
ns={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'};records=[]
with zipfile.ZipFile(raw) as z:
    workbook=ET.fromstring(z.read('xl/workbook.xml'));props=workbook.find('s:workbookPr',ns)
    if props is not None and props.attrib.get('date1904','0') not in ['0','false']:raise ValueError('Unsupported workbook date system')
    sheet=next(s for s in workbook.find('s:sheets',ns) if s.attrib['name']=='Power facilities')
    rid=sheet.attrib['{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id']
    target=next(x.attrib['Target'] for x in ET.fromstring(z.read('xl/_rels/workbook.xml.rels')) if x.attrib['Id']==rid)
    target=target.lstrip('/') if target.startswith('/') else posixpath.normpath('xl/'+target)
    strings=[''.join(n.itertext()) for n in ET.fromstring(z.read('xl/sharedStrings.xml'))] if 'xl/sharedStrings.xml' in z.namelist() else []
    styles=ET.fromstring(z.read('xl/styles.xml'));xfs=styles.find('s:cellXfs',ns)
    fmts={int(n.attrib['numFmtId']):n.attrib['formatCode'] for n in styles.findall('s:numFmts/s:numFmt',ns)}
    headers={}
    with z.open(target) as stream:
        for _,element in ET.iterparse(stream,events=['end']):
            if element.tag!='{'+ns['s']+'}row':continue
            cells={}
            for c in element:
                col=re.sub('[0-9]','',c.attrib['r']);v=c.find('s:v',ns);value='' if v is None else (v.text or '')
                typ=c.attrib.get('t','n');text=strings[int(value)] if typ=='s' else ''.join(n.text or '' for n in c.findall('.//s:t',ns)) if typ=='inlineStr' else value
                cells[col]=(text,c.attrib,value)
            if 'GEM unit/phase ID' in [v[0] for v in cells.values()]:headers={v[0]:k for k,v in cells.items()}
            elif headers:
                uid=cells.get(headers['GEM unit/phase ID'],('',{},''))[0]
                if uid in wanted:
                    value,attrs,raw_value=cells[headers['Unit / Phase name']];style_id=int(attrs.get('s','0'));format_id=int(xfs[style_id].attrib['numFmtId']);fmt=fmts.get(format_id,{16:'d-mmm'}.get(format_id)) # OOXML built-in 16, cross-checked against openpyxl 3.1.5
                    if attrs.get('t','n')!='n' or fmt is None or not all(x in fmt.lower() for x in ['m','d']):raise ValueError(('Expected explicit numeric date-formatted cell',attrs,format_id,fmt))
                    converted=(datetime(1899,12,30)+timedelta(days=float(raw_value))).strftime('%Y-%m-%d %H:%M:%S')
                    if converted!=wanted[uid]['Unit / Phase name']:raise ValueError('Date conversion mismatch')
                    records.append(dict(unit_id=uid,cell=attrs['r'],raw_numeric_value=raw_value,style_index=style_id,num_format_id=format_id,num_format_code=fmt,prepared_label=converted,capacity_mw=wanted[uid]['capacity_numeric_MW'],action='KEEP_GEM_ID_AND_ORIGINAL_VALUE; DO_NOT_INFER_INTENDED_UNIT_NAME'))
            element.clear()
if {r['unit_id'] for r in records}!=set(wanted) or len(records)!=len(wanted):raise ValueError('Incomplete date-label mapping')
result=dict(workbook_sha256=expected,affected_units=len(records),affected_capacity_mw=str(sum(Decimal(r['capacity_mw']) for r in records)),records=records,
            interpretation='Numeric date-format cells verified; original intended unit identifiers are not recoverable from this alone. This is not a start-year correction.',
            auditor_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
(OUT/'date_formatted_unit_labels.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='records'},indent=2))
