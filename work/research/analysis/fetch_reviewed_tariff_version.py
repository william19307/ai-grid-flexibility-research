"""Explicitly fetch the single reviewed tariff version into its own filename."""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import json
import sys
import urllib.request
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'work/research/models'))
from reviewed_tariff_version import NEW_PATH,NEW_SHA,NEW_SCRIPT_SHA,REMAINDER_SHA,SOURCE_URL,digest,split_reviewed_script
ap=argparse.ArgumentParser();ap.add_argument('--fetch',action='store_true');a=ap.parse_args()
if not a.fetch:ap.error('Use --fetch to explicitly retrieve the reviewed version')
with urllib.request.urlopen(urllib.request.Request(SOURCE_URL,headers={'User-Agent':'research-reconstruction/1.0'}),timeout=45) as r:
    if r.status!=200:raise ValueError('Unexpected source response')
    body=r.read(21577)
if len(body)!=21576 or digest(body)!=NEW_SHA:raise ValueError('Source changed; new review required')
script,remainder=split_reviewed_script(body)
if digest(script)!=NEW_SCRIPT_SHA or digest(remainder)!=REMAINDER_SHA:raise ValueError('Reviewed structure differs')
p=ROOT/NEW_PATH;p.parent.mkdir(parents=True,exist_ok=True)
if p.exists():
    if p.read_bytes()!=body:raise ValueError('Existing different file preserved')
else:
    with p.open('xb') as output:output.write(body)
report=dict(retrieved_utc=datetime.now(timezone.utc).isoformat(),url=SOURCE_URL,path=NEW_PATH,
    bytes=len(body),sha256=digest(body),scope='Reviewed new version, not historical original-byte restoration')
out=ROOT/'work/tmp/reviewed_tariff_version/fetch_receipt.json';out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
