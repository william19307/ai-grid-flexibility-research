"""Audit quarterly official wind aggregates against uncalibrated weather curves.

Comparisons are deliberately not calibration errors: fleet geography, vintage,
offshore mix and average operating capacity differ. No fitted factors are emitted.
"""
from pathlib import Path
from html.parser import HTMLParser
import csv, hashlib, json
import pandas as pd

ROOT=Path(__file__).resolve().parents[3]
SRC=ROOT/'work/research/sources/renewable_observations_20260923'
OUT=ROOT/'outputs/research/revision/weather_site_technology'


class TableRows(HTMLParser):
    def __init__(self):
        super().__init__(); self.rows=[]; self.row=None; self.cell=None
    def handle_starttag(self, tag, attrs):
        if tag=='tr': self.row=[]
        if tag in ['td','th'] and self.row is not None:self.cell=[]
    def handle_data(self,data):
        if self.cell is not None:self.cell.append(data)
    def handle_endtag(self,tag):
        if tag in ['td','th'] and self.cell is not None:
            self.row.append(''.join(''.join(self.cell).split()));self.cell=None
        if tag=='tr' and self.row is not None:self.rows.append(self.row);self.row=None


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    # Independent manual transcription of visible official table rows, not a
    # generated expected result from the HTML parser.
    transcribed={'q1':{'江苏':(1044,64.3,617),'贵州':(458,27.6,622),'甘肃':(1297,54.1,419)},
                 'h1_nea':{'江苏':(1110,126.7,1188),'贵州':(471,51.0,1130),'甘肃':(1312,130.1,1007)}}
    names={'江苏':'Jiangsu','贵州':'Guizhou','甘肃':'Gansu'}
    profile=ROOT/'outputs/research/revision/era5_rebuild/profiles_2020_generic_INTERVAL_ALIGNED_UNCALIBRATED.csv.gz'
    d=pd.read_csv(profile,index_col=0,parse_dates=True);rows=[];sources=[]
    for period in ['q1','h1_nea']:
        f=SRC/f'wind_2020_{period}.html';meta=json.loads(f.with_suffix('.html.meta.json').read_text())
        assert sha(f)==meta['sha256'];sources.append(meta)
        p=TableRows();p.feed(f.read_text(encoding='utf-8'))
        extracted={r[0]:tuple(float(x) for x in r[1:]) for r in p.rows if r and r[0] in names}
        assert extracted==transcribed[period],(period,extracted)
        end='2020-04-01' if period=='q1' else '2020-07-01'
        sub=d[d.index<pd.Timestamp(end,tz='Asia/Shanghai')]
        assert len(sub)==(2184 if period=='q1' else 4368)
        for cn,(cap,energy,hours) in extracted.items():
            rows.append(dict(province=names[cn],period='2020Q1' if period=='q1' else '2020H1',
                official_period_end_capacity_mw=cap*10,official_generation_mwh=energy*100000,
                official_utilization_hours=hours,period_hours=len(sub),
                generation_divided_by_end_capacity_hours=energy*100000/(cap*10),
                generic_fixed_site_equivalent_hours=float(sub[names[cn]+'|wind'].sum()),
                comparable_calibration_pair=False,source_url=meta['url']))
    OUT.mkdir(exist_ok=True,parents=True)
    with (OUT/'official_2020_wind_period_diagnostics.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
    result=dict(sources=sources,profile_sha256=sha(profile),code_sha256=sha(Path(__file__)),
        checks=dict(official_table_cells_against_manual_transcription=18,calendar_hours=[2184,4368]),
        observations=rows,scope='Independent published aggregate observations; not matched-fleet validation or a fitted generation calibration',
        limitations=['Official wind combines technologies, including Jiangsu offshore and onshore.',
            'Published utilization hours do not generally equal generation divided by period-end capacity.',
            'Fixed 2025 sample sites are not the historical operating fleet; no fitted scale is justified by these pairs.',
            'Q1 is contained in H1: these are correlated aggregates, not independent replications.',
            'Observed generation reflects curtailment/outages; modeled weather availability is a different quantity.'])
    (OUT/'official_2020_wind_audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
