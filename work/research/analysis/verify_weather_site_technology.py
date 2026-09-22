"""Verify recovered site fields directly from OOXML, without openpyxl."""
from pathlib import Path
import zipfile, xml.etree.ElementTree as E, csv, json, hashlib, posixpath

ROOT=Path(__file__).resolve().parents[3]
SOURCE=ROOT/'work/research/sources/zenodo_16810831/Global-integrated-Plant-Tracker-July-2025_china.xlsx'
OUT=ROOT/'outputs/research/revision/weather_site_technology'


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    ns={'m':'http://schemas.openxmlformats.org/spreadsheetml/2006/main',
        'r':'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}
    table=OUT/'archived_sites_with_technology_and_vintage.csv'
    rows=list(csv.DictReader(table.open()));want={int(r['source_excel_row']):r for r in rows};checked=0
    if len(want)!=120:raise ValueError('Missing or duplicate recovered source rows')
    with zipfile.ZipFile(SOURCE) as z:
        sheet=next(s for s in E.fromstring(z.read('xl/workbook.xml')).findall('m:sheets/m:sheet',ns)
                   if s.attrib['name']=='Power facilities')
        rels=E.fromstring(z.read('xl/_rels/workbook.xml.rels'))
        target=next(r.attrib['Target'] for r in rels if r.attrib['Id']==sheet.attrib['{'+ns['r']+'}id'])
        path=target.lstrip('/') if target.startswith('/') else posixpath.normpath('xl/'+target)
        strings=[''.join(t.itertext()) for t in E.fromstring(z.read('xl/sharedStrings.xml'))] if 'xl/sharedStrings.xml' in z.namelist() else []
        # Column references checked against the source header independently of
        # the openpyxl column-name mapping used in the recovery implementation.
        mapping={'AP':'unit_id','M':'technology','K':'start_year','I':'mw','AH':'lat','AI':'lon'}
        for r in E.fromstring(z.read(path)).findall('m:sheetData/m:row',ns):
            n=int(r.attrib['r'])
            if n not in want:continue
            values={}
            for c in r:
                col=''.join(x for x in c.attrib['r'] if x.isalpha());v=c.find('m:v',ns)
                text=v.text if v is not None else ''
                if c.attrib.get('t')=='s':text=strings[int(text)]
                if c.attrib.get('t')=='inlineStr':text=''.join(c.find('m:is',ns).itertext())
                values[col]=text
            for col,key in mapping.items():
                a=values.get(col,'');b=want[n][key]
                if key in ['mw','lat','lon']:assert abs(float(a)-float(b))<1e-9,(n,key,a,b)
                elif key=='start_year':
                    try:a=str(int(float(a)))
                    except ValueError:a=''
                    assert a==b,(n,key,a,b)
                else:assert a==b,(n,key,a,b)
                checked+=1
    assert checked==720
    result=dict(method='Independent OOXML cell extraction without openpyxl; recovered IDs, technology, year, capacity and coordinates',
        source_rows=120,cell_checks=checked,passed=True,source_sha256=sha(SOURCE),
        table_sha256=sha(table),verifier_sha256=sha(Path(__file__)))
    (OUT/'independent_cell_verification.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
