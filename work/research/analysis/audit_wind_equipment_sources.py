"""Cross-read published equipment fields; retain design/operating distinctions."""
from pathlib import Path
import hashlib
import json
import re
import subprocess
from pypdf import PdfReader

ROOT=Path(__file__).resolve().parents[3]
SRC=ROOT/'work/research/sources/wind_conversion_revision_20260923'
OUT=ROOT/'outputs/research/revision/wind_conversion_v1'


def main():
    checks=[]
    sources=[('rudong_msa.pdf',['55台H151-5.0MW','25台海装H171-5.0MW']),
             ('rudong_issuer_2018_065.pdf',['55台叶轮直径151','25台叶轮直径171','97米及105米'])]
    for name,terms in sources:
        path=SRC/name
        metadata=json.loads(path.with_suffix('.pdf.meta.json').read_text())
        sha=hashlib.sha256(path.read_bytes()).hexdigest()
        assert sha==metadata['sha256']
        reader=PdfReader(path)
        texts=[re.sub(r'\s+','',p.extract_text()) for p in reader.pages]
        other=re.sub(r'\s+','',subprocess.check_output(['pdftotext',str(path),'-']).decode())
        assert all(term in ''.join(texts) and term in other for term in terms)
        checks.append(dict(file=name,sha256=sha,pages=[i+1 for i,t in enumerate(texts) if any(s in t for s in terms)],
                           fields_crosschecked=len(terms),engines=['pypdf','pdftotext'],
                           scope='Text extraction agreement, not verification of installed configuration or generation'))
    result=dict(pdf_checks=checks,issuer_source=json.loads((SRC/'rudong_issuer_2018_065.pdf.meta.json').read_text()),
        operator_web_source=dict(url='https://eps.ctg.com.cn/cms/channel/1ywgg1/12587.htm',
            retrieved_via='web tool text, 2026-09-23',local_snapshot=False,
            local_acquisition_failures=['urllib SSL UNEXPECTED_EOF_WHILE_READING','curl TLS SSL_ERROR_SYSCALL'],
            fields=dict(manufacturer_model='Dongfang FD77C',count=134,unit_mw=1.5,tower_height_m=61.5,rotor_diameter_m=77),
            limit='Tower height is not substituted for hub height; published 2022 text says 2010 commissioning and nearly 9 years, an internal chronology inconsistency retained.'),
        missing=['No certified site power curve retrieved for FD77C/H151/H171',
                 'No site hub-height density/loss or metered-generation validation',
                 'Guazhou financing local PDF failed secure TLS retrieval, search result not admitted as verified turbine count',
                 'Guizhou Qingfeng exact operating turbine mix not verified'],
        script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    (OUT/'equipment_source_audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(dict(pdf_files=len(checks),extracted_fields=sum(c['fields_crosschecked'] for c in checks),
                          all_verified=True,scope='source extraction only')))


if __name__=='__main__':main()
