"""Paired correction diagnostic; never writes frozen publication tables."""
from pathlib import Path
import sys,argparse,json,hashlib,time
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'work/research/analysis'))
from run_regional_2030_s0_s3 import run

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--province',default='Jiangsu')
    ap.add_argument('--ai-share',type=float,default=.2)
    ap.add_argument('--treatment',choices=['legacy','split_pumped_storage','remove_pumped_storage'],required=True)
    ap.add_argument('--duration',type=float,default=8.)
    ap.add_argument('--efficiency',type=float,default=.75)
    ap.add_argument('--neighbours',action='store_true')
    a=ap.parse_args()
    label=f'{a.province}_ai{a.ai_share:g}_{a.treatment}_{a.duration:g}h_eta{a.efficiency:g}_{"neighbours" if a.neighbours else "islanded"}'
    folder=ROOT/'outputs/research/revision/hydro/runs'/label
    folder.mkdir(parents=True,exist_ok=True)
    if (folder/'complete.json').exists():raise FileExistsError(f'Already completed: {folder}')
    if list(folder.glob('regional_2030_*.json')):raise FileExistsError(f'Inspect incomplete output before retry: {folder}')
    sources=['work/research/analysis/run_regional_2030_s0_s3.py','work/research/models/coupled_grid_compute.py','work/research/models/hydro_fleet.py','outputs/research/revision/hydro/hydro_2030_by_technology.csv']
    manifest=dict(parameters=vars(a),started_unix=time.time(),evidence_tier='paired structural-correction diagnostic; other manuscript assumptions retained',sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in sources})
    (folder/'run_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    r=run(a.province,a.ai_share,export=a.neighbours,ext_mode='neighbours' if a.neighbours else 'price',hydro_treatment=a.treatment,phs_duration_h=a.duration,phs_roundtrip_efficiency=a.efficiency,results_dir=folder)
    status={k:v['feasible'] for k,v in r['results'].items()}
    (folder/'complete.json').write_text(json.dumps(dict(finished_unix=time.time(),scenario_feasibility=status,all_feasible=all(status.values())),indent=2)+'\n')

if __name__=='__main__':main()
