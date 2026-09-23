"""Local full-byte and independent parser review of the registered HTML pair."""
from pathlib import Path
from html.parser import HTMLParser
import argparse
import re
import json
import sys
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'work/research/models'))
from reviewed_tariff_version import *


class ScriptSpans(HTMLParser):
    def __init__(self, body):
        super().__init__(convert_charrefs=False)
        self.text=body.decode('latin1'); self.starts=[0]
        for match in re.finditer('\n', self.text):
            self.starts.append(match.end())
        self.opened=None; self.spans=[]
        self.feed(self.text)
    def byte_offset(self):
        line,column=self.getpos(); return self.starts[line-1]+column
    def handle_starttag(self, tag, attrs):
        if tag=='script': self.opened=self.byte_offset()
    def handle_endtag(self, tag):
        if tag=='script' and self.opened is not None:
            end=self.text.index('>',self.byte_offset())+1
            if 'P8CONFIG.RESOURCE=' in self.text[self.opened:end]:self.spans.append((self.opened,end))
            self.opened=None


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--new-file',type=Path,required=True);a=ap.parse_args()
    old=(ROOT/OLD_PATH).read_bytes();new=a.new_file.read_bytes();checks=[]
    assert digest(old)==OLD_SHA and digest(new)==NEW_SHA
    checks.append('exact_known_old_new_raw_hashes')
    parts=[]
    for label,body,expected in [('old',old,OLD_SCRIPT_SHA),('new',new,NEW_SCRIPT_SHA)]:
        script,remaining=split_reviewed_script(body)
        parser=ScriptSpans(body);assert len(parser.spans)==1
        start,end=parser.spans[0]
        assert body[start:end]==script and body[:start]+body[end:]==remaining
        assert digest(script)==expected and digest(remaining)==REMAINDER_SHA and len(remaining)==20364
        checks.append(label+'_regex_and_independent_parser_spans_identical');parts.append((script,remaining))
    assert parts[0][1]==parts[1][1]
    checks.append('all_20364_bytes_outside_one_script_unchanged')
    # Exact scripted changes, not an open-ended exemption for arbitrary scripts.
    oldscript,newscript=parts[0][0],parts[1][0]
    predicted=oldscript.replace(b'$this_router=P8CONFIG.URI[SYSTEM][MODULE].controller',b"$this_router='/index.php/cms/item'")
    predicted=predicted.replace(b";document.domain = 'gsei.com.cn';;document.base_domain = 'gsei.com.cn';",b'\r\n')
    assert predicted==newscript
    checks.append('only_reviewed_router_expression_and_document_domain_assignments_changed')
    text=new.decode('utf-8')
    for token in ['7:00-9:00','18:00-24:00','2:00-4:00','11:00-17:00','上浮50%','下浮50%','2021年1月1日']:
        assert token in text
    prices=json.loads((ROOT/'outputs/research/revision/policy/manifest.json').read_text())['prices']['Gansu']
    expected=[1.5 if 7<=h%24<9 or 18<=h%24<24 else .5 if 2<=h%24<4 or 11<=h%24<17 else 1. for h in range(192)]
    assert prices['hours']==expected and prices['source']['effective']=='2021-01-01'
    checks.append('all_192_frozen_tariff_values_match_reviewed_intervals_and_ratios')
    report=dict(old_sha256=OLD_SHA,new_sha256=NEW_SHA,identical_remainder_sha256=REMAINDER_SHA,
        old_bytes=len(old),new_bytes=len(new),unchanged_bytes=20364,old_script_sha256=OLD_SCRIPT_SHA,new_script_sha256=NEW_SCRIPT_SHA,
        source_url=SOURCE_URL,checks=checks,number_of_checks=len(checks),
        scope='One explicit source-version review; not original-byte restoration or authentication of all website content',
        remaining_limitations=['2021 effective tariff paired with 2020 workload is a scenario assumption',
            'Published catalogue ratios are not observed industrial market prices',
            'No new workload optimization, physical calibration or annual reliability evidence'])
    (ROOT/AUDIT_PATH).write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
